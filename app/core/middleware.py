"""CSRF token issuance and secure HTTP headers middleware.

Actual CSRF *verification* is done via the `verify_csrf` dependency in
app.core.csrf, applied per-route. Doing it in middleware would require
reading the request body (request.form()) ahead of the route handler,
which conflicts with FastAPI's own body parsing under BaseHTTPMiddleware.
"""
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import generate_csrf_token


class CSRFMiddleware(BaseHTTPMiddleware):
    """Ensures every session has a CSRF token available to render into forms."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not request.session.get("csrf_token"):
            request.session["csrf_token"] = generate_csrf_token()
        return await call_next(request)


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """Attaches standard hardening headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
