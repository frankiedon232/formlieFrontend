"""File sink: one file per level per day, `logs/{level}/{YYYY-MM-DD}.log` (BACKEND-SPEC §8.3)."""

from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TextIO


class DailyLevelFileHandler(logging.Handler):
    """Writes each record to the file of its own level and the current UTC day; prunes files past retention."""

    def __init__(self, base_dir: Path, retention_days: int = 90) -> None:
        super().__init__()
        self.base_dir = Path(base_dir)
        self.retention_days = retention_days
        self._files: dict[str, tuple[str, TextIO]] = {}
        self._io_lock = threading.Lock()
        self._last_prune = 0.0

    def _stream_for(self, level: str, day: str) -> TextIO:
        current = self._files.get(level)
        if current and current[0] == day:
            return current[1]
        if current:
            current[1].close()
        folder = self.base_dir / level.lower()
        folder.mkdir(parents=True, exist_ok=True)
        stream = open(folder / f"{day}.log", "a", encoding="utf-8")  # noqa: SIM115 (kept open until the day changes)
        self._files[level] = (day, stream)
        return stream

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
            day = datetime.fromtimestamp(record.created, UTC).strftime("%Y-%m-%d")
            with self._io_lock:
                stream = self._stream_for(record.levelname, day)
                stream.write(line + "\n")
                stream.flush()
                self._maybe_prune()
        except Exception:  # noqa: BLE001 (a logging failure must never break a request)
            self.handleError(record)

    def _maybe_prune(self) -> None:
        now = time.monotonic()
        if now - self._last_prune < 3600:
            return
        self._last_prune = now
        cutoff = (datetime.now(UTC) - timedelta(days=self.retention_days)).strftime("%Y-%m-%d")
        for file in self.base_dir.glob("*/*.log"):
            if file.stem < cutoff:
                file.unlink(missing_ok=True)

    def close(self) -> None:
        with self._io_lock:
            for _, stream in self._files.values():
                stream.close()
            self._files.clear()
        super().close()
