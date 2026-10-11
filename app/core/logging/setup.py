"""Structured logging (std logging, one JSON object per line) with trace_id and secret masking.

Every record carries: time (UTC, ms), level, logger, message, trace_id, tenant/org/user when known,
environment and release, plus any `extra={...}` fields (masked). Never log secrets (CLAUDE.md rule 12).
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.context import get_context
from app.core.logging.sinks import DailyLevelFileHandler

NOTICE = 25
logging.addLevelName(NOTICE, "NOTICE")

_LEVELS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "NOTICE": NOTICE, "WARNING": logging.WARNING,
           "ERROR": logging.ERROR, "CRITICAL": logging.CRITICAL}

SENSITIVE_KEYS = (
    "password", "passwd", "secret", "token", "authorization", "cookie", "otp", "code_hash", "totp",
    "api_key", "apikey", "private_key", "client_secret", "refresh", "csrf", "recovery", "card_number", "cvv",
    "fernet", "credential", "session_key", "set-cookie", "ticket", "signature",
)
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime", "taskName"}
MASK = "***"


def level_number(level: str) -> int:
    return _LEVELS.get(level.upper(), logging.INFO)


def is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(word in lowered for word in SENSITIVE_KEYS)


def mask(value: Any, depth: int = 0) -> Any:
    """Masks sensitive keys at any depth (dicts, lists). Long strings are cut to 512 characters."""
    if depth > 6:
        return "…"
    if isinstance(value, Mapping):
        return {str(k): (MASK if is_sensitive(str(k)) else mask(v, depth + 1)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [mask(v, depth + 1) for v in list(value)[:50]]
    if isinstance(value, str) and len(value) > 512:
        return value[:512] + "…"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class JsonFormatter(logging.Formatter):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.environment = settings.app_env
        self.release = settings.app_release

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "env": self.environment,
            "release": self.release,
        }
        ctx = get_context()
        if ctx is not None:
            entry["trace_id"] = ctx.trace_id
            if ctx.tenant is not None:
                entry["tenant_id"] = str(ctx.tenant.id)
                entry["organisation_id"] = str(ctx.tenant.organisation_id)
            if ctx.user_id is not None:
                entry["user_id"] = str(ctx.user_id)
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = MASK if is_sensitive(key) else mask(value)
        if record.exc_info:
            entry["stack"] = "".join(traceback.format_exception(*record.exc_info))[-8000:]
        return json.dumps(entry, ensure_ascii=False, default=str)


class _DropClientResets(logging.Filter):
    """Windows' proactor loop logs a client closing its TLS connection as an asyncio ERROR; it is not one."""

    def filter(self, record: logging.LogRecord) -> bool:
        exc = record.exc_info[1] if record.exc_info else None
        return not isinstance(exc, (ConnectionResetError, ConnectionAbortedError))


class PrettyFormatter(logging.Formatter):
    """One readable line per entry for the development console: time level logger: message  key=value ..."""

    ESC = "\033["
    COLORS = {"DEBUG": "90m", "INFO": "36m", "NOTICE": "34m", "WARNING": "33m", "ERROR": "31m", "CRITICAL": "1;31m"}

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.json = JsonFormatter(settings)

    def format(self, record: logging.LogRecord) -> str:
        entry = json.loads(self.json.format(record))
        stack = entry.pop("stack", None)
        color = self.ESC + self.COLORS.get(record.levelname, "0m")
        reset, grey = self.ESC + "0m", self.ESC + "90m"
        head = (f"{entry.pop('time')[11:23]} {color}{entry.pop('level'):<8}{reset} "
                f"{entry.pop('logger')}: {entry.pop('message')}")
        for key in ("env", "release", "color_message", "data"):
            entry.pop(key, None)
        details = " ".join(
            f"{k}={v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)}"
            for k, v in entry.items() if v not in (None, "", [], {}))
        line = f"{head}  {grey}{details}{reset}" if details else head
        return f"{line}\n{stack}" if stack else line


class _DropIdleRelay(logging.Filter):
    """The outbox relay runs every 2 s; a run with nothing to send is not worth a log line (one that sends logs
    "outbox relayed")."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "events.relay_outbox" not in message:
            return True
        return not (message.endswith(" received") or message.endswith(": 0"))


_configured = False


def configure_logging(settings: Settings) -> None:
    """Idempotent. Files per level and day under LOG_DIR, plus the console in development."""
    global _configured
    if _configured:
        return
    root = logging.getLogger()
    root.setLevel(level_number(settings.log_level))
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = JsonFormatter(settings)
    file_handler = DailyLevelFileHandler(settings.log_dir, settings.log_retention_days)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if settings.log_console:
        console = logging.StreamHandler(sys.stdout)
        style = settings.log_console_format or ("pretty" if settings.is_development else "json")
        console.setFormatter(PrettyFormatter(settings) if style == "pretty" else formatter)
        root.addHandler(console)

    logging.getLogger("asyncio").addFilter(_DropClientResets())
    for name in ("celery.app.trace", "celery.worker.strategy"):
        logging.getLogger(name).addFilter(_DropIdleRelay())
    # Uvicorn's access log is replaced by the request log middleware.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    _configured = True
