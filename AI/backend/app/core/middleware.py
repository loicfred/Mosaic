"""HTTP middleware: request ids, security headers, body-size limits, access logs."""

from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

access_log = logging.getLogger("opportunityos.access")

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
DOCS_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'")


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        s = get_settings()
        request.state.request_id = uuid.uuid4().hex[:16]
        started = time.perf_counter()

        # Reject oversized bodies early (uploads are also checked while streaming).
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > s.max_upload_bytes + 64 * 1024:
            return JSONResponse({"error": {"code": "payload_too_large", "message": "Request body too large.",
                                           "request_id": request.state.request_id}}, status_code=413)

        response = await call_next(request)
        path = request.url.path
        is_docs = path.startswith(("/docs", "/redoc", "/openapi.json"))
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = DOCS_CSP if is_docs else API_CSP
        if path.startswith(s.api_prefix):
            response.headers["Cache-Control"] = "no-store"
        if s.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        access_log.info(json.dumps({
            "request_id": request.state.request_id, "method": request.method, "path": path,
            "status": response.status_code, "ms": round((time.perf_counter() - started) * 1000, 1),
        }))
        return response
