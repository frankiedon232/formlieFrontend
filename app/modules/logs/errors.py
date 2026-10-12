"""Error logs into the database (BACKEND-SPEC §8.3).

Every process (API, workers, Beat) already writes JSON lines to `logs/{level}/{YYYY-MM-DD}.log`. A Beat task reads
the warning, error and critical files from where it stopped (`log_ingest_offsets`) and inserts each complete line
into `formaly.error_logs`. The row id is derived from the file, the line's position and its content, so a file read
twice (a crash before the offset was saved) adds nothing. Logging itself never touches the database, so a database problem
can't lose its own error lines or loop on them. CRITICAL lines also email ALERT_EMAILS.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.logs.models import ErrorLog, LogIngestOffset

log = logging.getLogger("formalie.errorlog")

LEVELS = ("warning", "error", "critical")
ID_NAMESPACE = uuid.UUID("5b0e5c1e-4f3a-4b7e-9c51-0f6e2a9d1c11")
MAX_BYTES_PER_RUN = 8 * 1024 * 1024  # per file; the next run carries on
KNOWN = {"time", "level", "logger", "message", "error_code", "security_event", "trace_id", "tenant_id",
         "organisation_id", "user_id", "method", "path", "stack", "env", "release"}
FILE_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.log$")


def _uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value)) if value else None
    except ValueError:
        return None


def _text(value: Any, size: int) -> str | None:
    return str(value)[:size] if value not in (None, "") else None


def to_row(entry: dict[str, Any], source: str, line: str = "") -> dict[str, Any] | None:
    try:
        occurred = datetime.fromisoformat(str(entry["time"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None
    return {
        # the same line read twice gives the same id; another file of the same name (another machine) does not
        "id": uuid.uuid5(ID_NAMESPACE, f"{source}:{hashlib.sha256(line.encode()).hexdigest()}"),
        "occurred_at": occurred,
        "level": str(entry.get("level") or "WARNING")[:10],
        "logger": _text(entry.get("logger"), 120),
        "message": str(entry.get("message") or "")[:4000],
        "error_code": _text(entry.get("error_code"), 20),
        "security_event": _text(entry.get("security_event"), 60),
        "trace_id": _text(entry.get("trace_id"), 36),
        "tenant_id": _uuid(entry.get("tenant_id")),
        "organisation_id": _uuid(entry.get("organisation_id")),
        "user_id": _uuid(entry.get("user_id")),
        "method": _text(entry.get("method"), 10),
        "path": _text(entry.get("path"), 500),
        "stack": _text(entry.get("stack"), 8000),
        "context": {k: v for k, v in entry.items() if k not in KNOWN},
        "environment": _text(entry.get("env"), 20),
        "release": _text(entry.get("release"), 40),
        "source": source[:200],
    }


def read_new_lines(path: Path, offset: int) -> tuple[list[tuple[int, str]], int]:
    """Complete lines after `offset` (a line still being written waits for the next run) and the new offset."""
    with path.open("rb") as f:
        f.seek(offset)
        chunk = f.read(MAX_BYTES_PER_RUN)
    end = chunk.rfind(b"\n")
    if end < 0:
        return [], offset
    lines, position = [], offset
    for raw in chunk[: end + 1].split(b"\n")[:-1]:
        lines.append((position, raw.decode("utf-8", errors="replace").strip()))
        position += len(raw) + 1
    return lines, offset + end + 1


def ingest(session: Session, log_dir: Path | None = None, days: int = 2) -> list[dict[str, Any]]:
    """One pass over the last `days` days of warning / error / critical files; returns the rows read."""
    base = Path(log_dir or get_settings().log_dir)
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    offsets = {o.file: o for o in session.execute(select(LogIngestOffset)).scalars()}
    inserted: list[dict[str, Any]] = []
    for level in LEVELS:
        folder = base / level
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if not FILE_NAME.match(path.name) or path.stem < since:
                continue
            name = f"{level}/{path.name}"
            known = offsets.get(name)
            start = known.offset if known else 0
            size = path.stat().st_size
            if size < start:
                start = 0  # the file was replaced (restored, moved between machines): read it again, ids dedupe
            if size <= start:
                continue
            lines, new_offset = read_new_lines(path, start)
            rows = []
            for position, line in lines:
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    entry = {"time": datetime.now(UTC).isoformat(), "level": level.upper(), "message": line}
                row = to_row(entry, f"{name}:{position}", line) if isinstance(entry, dict) else None
                if row is not None:
                    rows.append(row)
            if rows:
                # No RETURNING: the worker may only insert. A file read twice re-sends lines that already exist.
                session.execute(insert(ErrorLog).values(rows).on_conflict_do_nothing())
                inserted.extend(rows)
            now = datetime.now(UTC)
            session.execute(insert(LogIngestOffset).values(file=name, offset=new_offset, updated_at=now)
                            .on_conflict_do_update(index_elements=["file"],
                                                   set_={"offset": new_offset, "updated_at": now}))
    return inserted


def alert_message(rows: list[dict[str, Any]], to: str) -> dict[str, str]:
    """One email for the CRITICAL lines of a pass (never secrets: the lines are already masked)."""
    settings = get_settings()
    lines = [f"{r['occurred_at']:%Y-%m-%d %H:%M:%S} UTC  {r['error_code'] or ''}  {r['message'][:300]}  "
             f"(trace {r['trace_id'] or '-'})" for r in rows[:20]]
    more = f"\n… and {len(rows) - 20} more." if len(rows) > 20 else ""
    text = (f"{len(rows)} critical log line(s) on {settings.app_env} ({settings.app_release}):\n\n"
            + "\n".join(lines) + more + "\n\nSearch them in formaly.error_logs by trace id.")
    html = "<pre style=\"font-family:monospace\">" + text.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"
    return {"to": to, "subject": f"[Formalie {settings.app_env}] {len(rows)} critical error(s)", "text": text,
            "html": html}
