"""HTTP request/response logging middleware.

Uses raw ASGI middleware (not BaseHTTPMiddleware) for reliability.
Logs every request with: method, path, status, duration, user_id, client_ip.
Also captures request body for mutation requests (truncated for safety).
Skips noisy health-check and static asset requests.
"""

import logging
import time
import uuid
from typing import Any, Callable

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("app.http")

SKIP_PATHS = frozenset({"/health", "/openapi.json", "/docs", "/redoc", "/favicon.ico"})
MAX_BODY_LOG = 2048


class RequestLoggerMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in SKIP_PATHS or path.startswith("/static"):
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex[:12]
        method = scope.get("method", "?")
        client = scope.get("client")
        client_ip = client[0] if client else "-"
        query = scope.get("query_string", b"").decode("utf-8", errors="replace")

        body_chunks: list[bytes] = []

        async def logging_receive() -> Message:
            message = await receive()
            if method in ("POST", "PUT", "PATCH") and message.get("type") == "http.request":
                body_chunks.append(message.get("body", b""))
            return message

        status_code = 0

        async def logging_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        user_id = None
        headers_raw = dict(scope.get("headers", []))
        auth_header = headers_raw.get(b"authorization", b"").decode("utf-8", errors="replace")
        if auth_header.startswith("Bearer ") and len(auth_header) > 20:
            try:
                from app.services.auth_service import AuthService
                payload = AuthService.decode_token(auth_header[7:])
                if payload:
                    user_id = payload.get("sub")
            except Exception:
                pass

        start = time.perf_counter()
        try:
            await self.app(scope, logging_receive, logging_send)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.error(
                "← %s %s 500 (unhandled) %.1fms",
                method, path, duration_ms,
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                    "client_ip": client_ip,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        level = logging.WARNING if status_code >= 400 else logging.INFO

        log_msg = f"← {method} {path} {status_code} {duration_ms}ms"
        if query:
            log_msg += f" ?{query}"

        extra: dict[str, Any] = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "client_ip": client_ip,
        }

        logger.log(level, log_msg, extra=extra)

        if status_code >= 400 and body_chunks:
            body_text = b"".join(body_chunks).decode("utf-8", errors="replace")[:MAX_BODY_LOG]
            logger.debug("  request body: %s", body_text[:500], extra=extra)
