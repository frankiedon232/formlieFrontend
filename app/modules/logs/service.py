"""Request-log writing: enrich (location, device), then insert in batches; JSON-lines file as the fallback.

The middleware hands finished records to `RequestLogShipper.submit()` (never blocks the request). The shipper
batches them and, per REQUEST_LOG_SINK, writes them to the database itself, hands them to the `logs` Celery
queue, or appends them to `logs/requests/{date}.jsonl`. Whatever cannot be written goes to that file, and
`scripts/replay_request_logs.py` loads it later. Inserts are idempotent (same id and time: skipped).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from user_agents import parse as parse_user_agent

from app.core.config import get_settings
from app.core.logging.geo import get_geo
from app.modules.logs.models import COLUMNS, RequestLog

log = logging.getLogger("formalie.requestlog")

_UUID_COLUMNS = ("id", "tenant_id", "organisation_id", "user_id", "session_id")


# ── Enrichment ────────────────────────────────────────────────────────────────

def device_fields(user_agent: str | None) -> dict[str, Any]:
    if not user_agent:
        return {}
    ua = parse_user_agent(user_agent)
    kind = ("bot" if ua.is_bot else "mobile" if ua.is_mobile else "tablet" if ua.is_tablet
            else "desktop" if ua.is_pc else "other")
    return {
        "device_type": kind,
        "device_brand": ua.device.brand,
        "device_model": ua.device.model,
        "os": ua.os.family,
        "os_version": ua.os.version_string or None,
        "browser": ua.browser.family,
        "browser_version": ua.browser.version_string or None,
        "is_bot": ua.is_bot,
    }


def enrich(record: dict[str, Any]) -> dict[str, Any]:
    """Adds location and device. Safe to call twice (a replayed record keeps what it has)."""
    if "geo_source" not in record:
        record.update(get_geo().lookup(record.get("client_ip"), record.get("request_headers"),
                                       trusted_proxy=bool(record.get("proxy_trusted"))))
    if "device_type" not in record:
        try:
            record.update(device_fields(record.get("user_agent")))
        except Exception as exc:  # noqa: BLE001
            log.debug("user agent not parsed", extra={"error": str(exc)})
    return record


def to_row(record: dict[str, Any]) -> dict[str, Any]:
    row = {k: v for k, v in record.items() if k in COLUMNS}
    for key in _UUID_COLUMNS:
        if isinstance(row.get(key), str):
            row[key] = uuid.UUID(row[key])
    if isinstance(row.get("occurred_at"), str):
        row["occurred_at"] = datetime.fromisoformat(row["occurred_at"])
    for key in ("country", "continent"):
        if row.get(key):
            row[key] = str(row[key])[:2]
    return row


def _statement():  # noqa: ANN202
    # No conflict target on purpose: naming the columns needs SELECT on them, and the writers may only INSERT.
    # The primary key (id, occurred_at) is the only unique constraint, so a replayed record is still skipped.
    return insert(RequestLog).on_conflict_do_nothing()


# ── Writers ───────────────────────────────────────────────────────────────────

def write_batch_sync(session: Session, records: Iterable[dict[str, Any]]) -> int:
    rows = [to_row(enrich(r)) for r in records]
    if rows:
        session.execute(_statement(), rows)
    return len(rows)


async def write_batch_async(records: list[dict[str, Any]]) -> int:
    from app.core.db.session import db_session

    rows = await asyncio.to_thread(lambda: [to_row(enrich(r)) for r in records])
    if rows:
        async with db_session("write") as session:
            await session.execute(_statement(), rows)
    return len(rows)


_file_lock = threading.Lock()


def fallback_dir() -> Path:
    return Path(get_settings().log_dir) / "requests"


def append_to_file(records: Iterable[dict[str, Any]]) -> None:
    folder = fallback_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now(UTC):%Y-%m-%d}.jsonl"
    lines = "".join(json.dumps(r, default=str, ensure_ascii=False) + "\n" for r in records)
    with _file_lock, open(path, "a", encoding="utf-8") as handle:
        handle.write(lines)


def send_to_queue(records: list[dict[str, Any]]) -> None:
    from app.workers.celery_app import celery_app

    payload = json.loads(json.dumps(records, default=str))
    celery_app.send_task("logs.write_request_logs", args=[payload], queue="logs")


# ── Shipper ───────────────────────────────────────────────────────────────────

class RequestLogShipper:
    """Bounded in-memory queue + one background task per process. `submit()` never blocks or raises."""

    def __init__(self, sink: str | None = None) -> None:
        settings = get_settings()
        self.sink = sink or settings.request_log_sink
        self.batch_size = settings.request_log_batch_size
        self.flush_seconds = settings.request_log_flush_seconds
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=settings.request_log_queue_max)
        self._task: asyncio.Task[None] | None = None
        self._last_error_log = 0.0
        self.written = 0
        self.fallback = 0

    def submit(self, record: dict[str, Any]) -> None:
        self._ensure_running()
        try:
            self.queue.put_nowait(record)
        except asyncio.QueueFull:
            self.fallback += 1
            try:
                append_to_file([record])
            except OSError:
                pass

    def _ensure_running(self) -> None:
        if self._task is None or self._task.done():
            try:
                self._task = asyncio.get_running_loop().create_task(self._run(), name="request-log-shipper")
            except RuntimeError:
                self._task = None

    async def _next_batch(self) -> list[dict[str, Any]]:
        first = await self.queue.get()
        batch = [first]
        deadline = time.monotonic() + self.flush_seconds
        while len(batch) < self.batch_size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                batch.append(await asyncio.wait_for(self.queue.get(), remaining))
            except TimeoutError:
                break
        return batch

    async def _run(self) -> None:
        while True:
            batch = await self._next_batch()
            await self.ship(batch)

    async def ship(self, batch: list[dict[str, Any]]) -> None:
        try:
            if self.sink == "database":
                self.written += await write_batch_async(batch)
            elif self.sink == "celery":
                await asyncio.to_thread(send_to_queue, batch)
                self.written += len(batch)
            else:
                await asyncio.to_thread(append_to_file, batch)
                self.written += len(batch)
        except Exception as exc:  # noqa: BLE001 (keep the records: file fallback)
            self.fallback += len(batch)
            try:
                await asyncio.to_thread(append_to_file, batch)
            except OSError as file_exc:
                log.critical("request log fallback file failed, records lost",
                             extra={"count": len(batch), "error": str(file_exc)})
            now = time.monotonic()
            if now - self._last_error_log > 60:  # once a minute, not once per batch
                self._last_error_log = now
                log.error("request log sink failed, writing to the fallback file",
                          extra={"sink": self.sink, "error": str(exc)[:500]})

    async def drain(self) -> None:
        """Writes whatever is queued (shutdown)."""
        if self._task is not None:
            self._task.cancel()
        batch: list[dict[str, Any]] = []
        while not self.queue.empty():
            batch.append(self.queue.get_nowait())
            if len(batch) >= self.batch_size:
                await self.ship(batch)
                batch = []
        if batch:
            await self.ship(batch)
