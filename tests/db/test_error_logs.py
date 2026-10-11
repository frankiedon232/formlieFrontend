"""Error logs into the database (B2, BACKEND-SPEC §8.3): the level files written by the real JSON formatter are
loaded by the worker role, once, from where the last run stopped; CRITICAL lines make one alert email."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import RequestContext, reset_context, set_context
from app.core.logging.setup import JsonFormatter
from app.core.logging.sinks import DailyLevelFileHandler
from app.modules.logs.errors import alert_message, ingest
from app.workers.db import _sync_url

pytestmark = pytest.mark.db


def write_lines(log_dir: Path, marker: str) -> None:
    """Through the same handler and formatter as the app, inside a request context."""
    logger = logging.getLogger(f"formalie.test.{marker}")
    logger.propagate = False
    handler = DailyLevelFileHandler(log_dir)
    handler.setFormatter(JsonFormatter(get_settings()))
    logger.addHandler(handler)
    token = set_context(RequestContext(trace_id=f"t-{marker}", started_at=0.0, method="GET", path="/api/v1/forms"))
    try:
        logger.warning("FRM-TEN-1003 %s", marker, extra={"error_code": "FRM-TEN-1003",
                                                         "security_event": "token_tenant_mismatch", "password": "x"})
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            logger.exception("FRM-GEN-5000 %s", marker, extra={"error_code": "FRM-GEN-5000"})
        logger.critical("database down %s", marker)
        logger.info("not loaded %s", marker)
    finally:
        reset_context(token)
        logger.removeHandler(handler)
        handler.close()


def rows(superuser: psycopg.Connection, marker: str) -> list[tuple]:
    return superuser.execute(
        "SELECT level, error_code, security_event, trace_id, method, path, stack IS NOT NULL, context "
        "FROM formaly.error_logs WHERE message LIKE %s ORDER BY level", (f"%{marker}",)).fetchall()


def test_level_files_are_loaded_once(tmp_path: Path, worker_dsn: str, superuser) -> None:  # noqa: ANN001
    marker = uuid.uuid4().hex[:10]
    superuser.execute('UPDATE formaly.log_ingest_offsets SET "offset" = 0')  # another test's files had these names
    write_lines(tmp_path, marker)
    engine = create_engine(_sync_url(worker_dsn))
    try:
        with Session(engine) as session, session.begin():  # as formalie_worker: insert-only
            read = ingest(session, tmp_path)
        assert {r["level"] for r in read} == {"WARNING", "ERROR", "CRITICAL"}
        found = rows(superuser, marker)
        assert [r[0] for r in found] == ["CRITICAL", "ERROR", "WARNING"]
        critical, error, warning = found
        assert warning[1:6] == ("FRM-TEN-1003", "token_tenant_mismatch", f"t-{marker}", "GET", "/api/v1/forms")
        assert warning[7]["password"] == "***"  # masked by the formatter, never stored as it was
        assert error[1] == "FRM-GEN-5000" and error[6] is True  # the stack stays on the server
        assert critical[1] is None

        # Nothing new: nothing added. A line still being written waits for the next run.
        with (tmp_path / "warning").joinpath(next((tmp_path / "warning").iterdir()).name).open("a") as f:
            f.write(json.dumps({"time": "2026-10-11T10:00:00.000Z", "level": "WARNING", "message": f"half {marker}"}))
        with Session(engine) as session, session.begin():
            assert ingest(session, tmp_path) == []
        assert len(rows(superuser, marker)) == 3
        with (tmp_path / "warning").joinpath(next((tmp_path / "warning").iterdir()).name).open("a") as f:
            f.write("\n")
        with Session(engine) as session, session.begin():
            assert [r["message"] for r in ingest(session, tmp_path)] == [f"half {marker}"]

        # Read again from the start (offsets lost): the same rows, no duplicates
        superuser.execute("UPDATE formaly.log_ingest_offsets SET \"offset\" = 0")
        with Session(engine) as session, session.begin():
            ingest(session, tmp_path)
        assert len(rows(superuser, marker)) == 4
    finally:
        engine.dispose()


def test_critical_alert_email() -> None:
    from datetime import UTC, datetime

    row = {"occurred_at": datetime(2026, 10, 11, 9, 30, tzinfo=UTC), "error_code": None,
           "message": "database <down>", "trace_id": "t-1"}
    message = alert_message([row], "ops@example.test")
    assert message["to"] == "ops@example.test" and "1 critical error" in message["subject"]
    assert "2026-10-11 09:30:00 UTC" in message["text"] and "trace t-1" in message["text"]
    assert "&lt;down>" in message["html"]
