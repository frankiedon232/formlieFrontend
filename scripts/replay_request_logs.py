"""Loads request-log records that went to the fallback files (`logs/requests/*.jsonl`) into the database.

    fmly\\Scripts\\python.exe scripts\\replay_request_logs.py [--include-today]

Runs as formalie_worker (DB_RELAY_URL). Each finished file is renamed `*.jsonl.done`. Safe to run again:
records already in the table are skipped (same id and time).
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from app.modules.logs.service import fallback_dir, write_batch_sync  # noqa: E402
from app.workers.db import worker_engine  # noqa: E402

BATCH = 500


def main() -> None:
    today = f"{datetime.now(UTC):%Y-%m-%d}.jsonl"
    include_today = "--include-today" in sys.argv
    files = sorted(p for p in fallback_dir().glob("*.jsonl") if include_today or p.name != today)
    if not files:
        print("Nothing to replay.")
        return
    for path in files:
        written = 0
        batch: list[dict] = []
        with open(path, encoding="utf-8") as handle, Session(worker_engine()) as session, session.begin():
            for line in handle:
                if line.strip():
                    batch.append(json.loads(line))
                if len(batch) >= BATCH:
                    written += write_batch_sync(session, batch)
                    batch = []
            if batch:
                written += write_batch_sync(session, batch)
        path.rename(path.with_suffix(".jsonl.done"))
        print(f"{path.name}: {written} records")


if __name__ == "__main__":
    main()
