"""HTTP routes for the auth module (session-based web login)."""
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.csrf import verify_csrf
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional
from app.core.templates import templates
from app.modules.auth.models import User
from app.modules.auth.service import (
    AccountLockedError,
    AuthService,
    InvalidCredentialsError,
)

router = APIRouter(tags=["auth"])
settings = get_settings()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/login")
def login_page(request: Request, current_user: User | None = Depends(get_current_user_optional)):
    """Render the login form. Redirects away if already authenticated."""
    if current_user is not None:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"error": None, "csrf_token": request.session.get("csrf_token")},
    )


@router.post("/login")
def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Process a login form submission."""
    service = AuthService(db)
    ip_address = _client_ip(request)
    try:
        user = service.authenticate(username=username.strip(), password=password, ip_address=ip_address)
    except (InvalidCredentialsError, AccountLockedError) as exc:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": str(exc), "csrf_token": request.session.get("csrf_token")},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["user_id"] = user.id
    request.session["role"] = user.role.value

    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    if remember_me:
        raw_token = service.create_remember_token(user.id)
        redirect.set_cookie(
            key=settings.remember_cookie_name,
            value=raw_token,
            max_age=settings.remember_max_age_seconds,
            httponly=True,
            samesite="lax",
            secure=not get_settings().debug,
        )
    return redirect


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), _csrf: None = Depends(verify_csrf)):
    """Log out the current user: clear session and revoke remember-me token if present."""
    raw_token = request.cookies.get(settings.remember_cookie_name)
    if raw_token:
        AuthService(db).revoke_remember_token(raw_token)
    request.session.clear()
    redirect = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    redirect.delete_cookie(settings.remember_cookie_name)
    return redirect
