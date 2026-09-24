"""Centralised error handling: consistent JSON errors, no stack traces to clients."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("opportunityos.errors")


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: object | None = None) -> None:
        self.status, self.code, self.message, self.details = status, code, message, details


def _body(code: str, message: str, request: Request, details: object | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details,
                      "request_id": getattr(request.state, "request_id", None)}}


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message, request, exc.details), status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed",
                413: "payload_too_large", 429: "rate_limited"}.get(exc.status_code, "http_error")
        headers = getattr(exc, "headers", None)
        return JSONResponse(_body(code, str(exc.detail), request), status_code=exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo submitted values back (they may contain secrets or financial data).
        details = [{"field": ".".join(str(p) for p in e.get("loc", [])[1:]), "message": e.get("msg")}
                   for e in exc.errors()]
        return JSONResponse(_body("validation_error", "Some fields are invalid.", request, details),
                            status_code=422)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", uuid.uuid4().hex)
        log.exception("unhandled error request_id=%s path=%s", rid, request.url.path)
        return JSONResponse(_body("internal_error", "Something went wrong. The error has been logged.", request),
                            status_code=500)
