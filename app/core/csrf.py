"""CSRF verification dependency, applied explicitly on state-changing routes."""
from fastapi import Form, HTTPException, Request, status

from app.core.security import verify_csrf_token


def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    """FastAPI dependency that validates the submitted CSRF token against the session.

    Usage: add `_: None = Depends(verify_csrf)` to any state-changing route
    that renders a form with a `csrf_token` hidden field.
    """
    session_token = request.session.get("csrf_token")
    if not verify_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
