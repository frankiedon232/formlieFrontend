"""FrmError: the one exception services raise. The code decides the HTTP status, message and log level."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.errors.codes import ERROR_CODES, ErrorDef


class FrmError(Exception):
    def __init__(
        self,
        code: str,
        details: list[Mapping[str, str]] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
        log_context: Mapping[str, Any] | None = None,
    ) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"Unknown error code {code}; add it to docs/ERROR-CODES.md and regenerate")
        super().__init__(code)
        self.code = code
        self.details = [{"field": str(d["field"]), "message": str(d["message"])} for d in (details or [])]
        self.headers = dict(headers or {})
        self.log_context = dict(log_context or {})

    @property
    def definition(self) -> ErrorDef:
        return ERROR_CODES[self.code]

    @property
    def status(self) -> int:
        return self.definition.status


def error_body(code: str, trace_id: str | None, details: list[Mapping[str, str]] | None = None) -> dict[str, Any]:
    """The API error shape (shared/types/api.ts ApiFailure). Never carries internals."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": ERROR_CODES[code].message,
            "trace_id": trace_id or "",
            "details": [{"field": str(d["field"]), "message": str(d["message"])} for d in (details or [])],
        },
    }
