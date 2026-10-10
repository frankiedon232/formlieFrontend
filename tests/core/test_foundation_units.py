"""Units: ids, cache tiers, logging (masking, files per level), soft-delete guard, list paging, codes."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.cache.tiers import L1Cache, RedisCache, cache_key
from app.core.db.base import HardDeleteRefused, SoftDeleteMixin, UuidPkMixin
from app.core.errors import FrmError
from app.core.ids import uuid7
from app.core.logging.setup import JsonFormatter, mask
from app.core.logging.sinks import DailyLevelFileHandler
from app.core.responses import PageParams


def test_uuid7_is_time_ordered_and_version_7() -> None:
    ids = [uuid7() for _ in range(50)]
    assert all(i.version == 7 for i in ids)
    assert ids == sorted(ids)


def test_unknown_error_codes_are_refused() -> None:
    with pytest.raises(ValueError):
        FrmError("FRM-NOPE-1234")


@pytest.mark.parametrize(("page", "size", "expected"), [
    (None, None, (1, 20)), ("3", "50", (3, 50)), ("0", "500", (1, 100)), ("x", "-1", (1, 1)),
])
def test_page_params_like_the_mock(page, size, expected) -> None:  # noqa: ANN001
    params = PageParams.from_query(page, size)
    assert (params.page, params.page_size) == expected


def test_list_meta() -> None:
    meta = PageParams(page=2, page_size=20).meta(41)
    assert meta.model_dump(exclude_none=True) == {"page": 2, "page_size": 20, "total": 41, "total_pages": 3}


# ── Cache ──────────────────────────────────────────────────────────────────────

def test_l1_cache_expires_and_evicts(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [100.0]
    monkeypatch.setattr("app.core.cache.tiers.time.monotonic", lambda: now[0])
    cache: L1Cache[str, int] = L1Cache(ttl_seconds=5, max_items=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None and cache.get("c") == 3
    now[0] += 6
    assert cache.get("c") is None


async def test_redis_cache_aside_with_tenant_versioned_keys(redis) -> None:
    cache = RedisCache(redis)
    calls = []

    async def loader() -> dict[str, int]:
        calls.append(1)
        return {"value": len(calls)}

    tenant = uuid.UUID("01900000-0000-7000-8000-00000000000a")
    assert await cache.get_or_set(tenant, "forms", "f1", loader) == {"value": 1}
    assert await cache.get_or_set(tenant, "forms", "f1", loader) == {"value": 1}
    assert await redis.get(cache_key(tenant, "forms", "f1", 0)) is not None
    assert cache_key(tenant, "forms", "f1", 0) == f"fm:v1:t:{tenant}:forms:f1:0"
    await cache.invalidate(tenant, "forms")
    assert await cache.get_or_set(tenant, "forms", "f1", loader) == {"value": 2}
    other = uuid.UUID("01900000-0000-7000-8000-00000000000b")  # another tenant never sees it
    assert await cache.get_or_set(other, "forms", "f1", loader) == {"value": 3}


# ── Logging ────────────────────────────────────────────────────────────────────

def test_mask_hides_secrets_at_any_depth() -> None:
    masked = mask({"email": "a@example.com", "password": "x", "nested": [{"refresh_token": "y", "company": "Acme"}]})
    assert masked == {"email": "a@example.com", "password": "***", "nested": [{"refresh_token": "***", "company": "Acme"}]}


def test_json_lines_go_to_one_file_per_level_and_day(tmp_path: Path, settings) -> None:
    handler = DailyLevelFileHandler(tmp_path)
    handler.setFormatter(JsonFormatter(settings))
    logger = logging.getLogger("formalie.test.files")
    logger.addHandler(handler)
    logger.propagate = False
    try:
        logger.warning("careful", extra={"authorization": "Bearer abc", "count": 2})
        logger.error("broken")
    finally:
        logger.removeHandler(handler)
        handler.close()
    warning_files = list((tmp_path / "warning").glob("*.log"))
    assert len(warning_files) == 1 and len(list((tmp_path / "error").glob("*.log"))) == 1
    entry = json.loads(warning_files[0].read_text(encoding="utf-8").strip())
    assert entry["level"] == "WARNING" and entry["message"] == "careful" and entry["count"] == 2
    assert entry["authorization"] == "***"
    assert "Bearer abc" not in warning_files[0].read_text(encoding="utf-8")


# ── Soft delete only ───────────────────────────────────────────────────────────

class _Base(DeclarativeBase):
    pass


class _Thing(UuidPkMixin, SoftDeleteMixin, _Base):
    __tablename__ = "things"
    name: Mapped[str] = mapped_column(String(20))


def test_hard_deletes_are_refused_and_soft_delete_works() -> None:
    engine = create_engine("sqlite://")
    _Base.metadata.create_all(engine)
    with Session(engine) as session:
        thing = _Thing(name="a")
        session.add(thing)
        session.commit()
        session.delete(thing)
        with pytest.raises(HardDeleteRefused):
            session.flush()
        session.rollback()
        actor = uuid7()
        thing.soft_delete(actor)
        session.commit()
        assert thing.deleted_at is not None and thing.deleted_by == actor


def test_route_template_keeps_the_prefix() -> None:
    from types import SimpleNamespace

    from app.core.middleware.request_log import route_template

    route = SimpleNamespace(path_format="/forms/{id}")
    scope = {"route": route, "path": "/api/v1/forms/abc", "path_params": {"id": "abc"}}
    assert route_template(scope) == "/api/v1/forms/{id}"
    assert route_template({"path": "/x"}) is None
