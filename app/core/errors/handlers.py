"""Exception handlers: every failure leaves as `{ success: false, error: { code, message, trace_id, details } }`."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import current_trace_id, get_context
from app.core.errors.codes import ERROR_CODES
from app.core.errors.exceptions import FrmError, error_body
from app.core.logging.setup import level_number

log = logging.getLogger("formalie.errors")

_HTTP_TO_CODE = {
    400: "FRM-GEN-1001",
    401: "FRM-AUTH-1001",
    403: "FRM-PERM-1001",
    404: "FRM-GEN-1004",
    405: "FRM-GEN-1004",  # an unknown method is an unknown address, like the mock's router
    409: "FRM-GEN-1009",
    413: "FRM-API-1018",
    422: "FRM-GEN-1002",
    429: "FRM-GEN-1029",
    503: "FRM-GEN-5003",
}


def error_response(code: str, details: list[dict[str, str]] | None = None, headers: dict[str, str] | None = None) -> JSONResponse:
    ctx = get_context()
    if ctx is not None:
        ctx.error_code = code
    return JSONResponse(error_body(code, current_trace_id(), details), status_code=ERROR_CODES[code].status, headers=headers)


def _field_path(loc: tuple[object, ...]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts)


async def _frm_error(_: Request, exc: FrmError) -> JSONResponse:
    definition = exc.definition
    log.log(level_number(definition.level), "%s %s", exc.code, definition.message,
            extra={"error_code": exc.code, "details": exc.details, **exc.log_context})
    return error_response(exc.code, exc.details, exc.headers)


async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [{"field": _field_path(tuple(e.get("loc", ()))), "message": str(e.get("msg", ""))} for e in exc.errors()]
    log.info("FRM-GEN-1002 validation failed", extra={"error_code": "FRM-GEN-1002", "details": details})
    return error_response("FRM-GEN-1002", details)


async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_TO_CODE.get(exc.status_code, "FRM-GEN-1001" if exc.status_code < 500 else "FRM-GEN-5000")
    return error_response(code, headers=getattr(exc, "headers", None))


async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
    log.error("FRM-GEN-5000 unhandled exception", exc_info=exc, extra={"error_code": "FRM-GEN-5000"})
    return error_response("FRM-GEN-5000")


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(FrmError, _frm_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled)
