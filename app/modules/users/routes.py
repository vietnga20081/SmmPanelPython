"""HTTP routes for the users module (admin-only)."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

from app.core.csrf import verify_csrf
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.templates import templates
from app.modules.auth.models import User, UserRole
from app.modules.users.service import (
    DuplicateUserError,
    LastAdminGuardError,
    SelfActionError,
    UsersError,
    UsersService,
)
from app.modules.users.validators import sanitize_role_filter, sanitize_status_filter

router = APIRouter(prefix="/admin/users", tags=["users"])


@router.get("")
def list_users(
    request: Request,
    q: str = Query(default=""),
    role: str = Query(default=""),
    status_filter: str = Query(default="", alias="status"),
    page: int = Query(default=1, ge=1),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List users with search/filter/pagination."""
    service = UsersService(db)
    role = sanitize_role_filter(role)
    status_filter = sanitize_status_filter(status_filter)
    items, current_page, total_pages, total = service.list_users(q, role, status_filter, page)
    return templates.TemplateResponse(
        request,
        "users/list.html",
        {
            "user": current_user,
            "active_page": "users",
            "breadcrumb": "Quản trị > Người dùng",
            "items": items,
            "q": q,
            "role": role,
            "status_filter": status_filter,
            "page": current_page,
            "total_pages": total_pages,
            "total": total,
            "roles": list(UserRole),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/new")
def new_user_form(
    request: Request,
    current_user: User = Depends(require_admin),
):
    """Render the create-user form."""
    return templates.TemplateResponse(
        request,
        "users/form.html",
        {
            "user": current_user,
            "active_page": "users",
            "breadcrumb": "Quản trị > Người dùng > Thêm mới",
            "mode": "create",
            "target": None,
            "error": None,
            "roles": list(UserRole),
            "csrf_token": request.session.get("csrf_token"),
        },
    )


@router.post("/new")
def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Handle create-user form submission."""
    service = UsersService(db)
    try:
        role_enum = UserRole(role)
        service.create_user(username=username.strip(), email=email.strip(), password=password, role=role_enum)
    except (DuplicateUserError, ValueError) as exc:
        message = str(exc) if isinstance(exc, DuplicateUserError) else "Vai trò không hợp lệ."
        return templates.TemplateResponse(
            request,
            "users/form.html",
            {
                "user": current_user,
                "active_page": "users",
                "breadcrumb": "Quản trị > Người dùng > Thêm mới",
                "mode": "create",
                "target": None,
                "error": message,
                "roles": list(UserRole),
                "csrf_token": request.session.get("csrf_token"),
                "form_username": username,
                "form_email": email,
                "form_role": role,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)


@router.get("/{target_id}/edit")
def edit_user_form(
    request: Request,
    target_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Render the edit-user form."""
    service = UsersService(db)
    target = service.get_user(target_id)
    if target is None:
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request,
        "users/form.html",
        {
            "user": current_user,
            "active_page": "users",
            "breadcrumb": "Quản trị > Người dùng > Sửa",
            "mode": "edit",
            "target": target,
            "error": None,
            "roles": list(UserRole),
            "csrf_token": request.session.get("csrf_token"),
        },
    )


@router.post("/{target_id}/edit")
def update_user(
    request: Request,
    target_id: int,
    email: str = Form(...),
    role: str = Form(...),
    is_active: bool = Form(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Handle edit-user form submission."""
    service = UsersService(db)
    target = service.get_user(target_id)
    try:
        role_enum = UserRole(role)
        service.update_user(current_user, target_id, email=email.strip(), role=role_enum, is_active=is_active)
    except (DuplicateUserError, SelfActionError, LastAdminGuardError, UsersError, ValueError) as exc:
        message = str(exc) if not isinstance(exc, ValueError) else "Vai trò không hợp lệ."
        return templates.TemplateResponse(
            request,
            "users/form.html",
            {
                "user": current_user,
                "active_page": "users",
                "breadcrumb": "Quản trị > Người dùng > Sửa",
                "mode": "edit",
                "target": target,
                "error": message,
                "roles": list(UserRole),
                "csrf_token": request.session.get("csrf_token"),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)


@router.post("/{target_id}/reset-password")
def reset_password(
    request: Request,
    target_id: int,
    new_password: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Reset a user's password from the edit page."""
    service = UsersService(db)
    target = service.get_user(target_id)
    error = None
    try:
        service.reset_password(target_id, new_password)
    except Exception as exc:  # ValidationFailure or UsersError
        error = str(exc)

    if error:
        return templates.TemplateResponse(
            request,
            "users/form.html",
            {
                "user": current_user,
                "active_page": "users",
                "breadcrumb": "Quản trị > Người dùng > Sửa",
                "mode": "edit",
                "target": target,
                "error": error,
                "roles": list(UserRole),
                "csrf_token": request.session.get("csrf_token"),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url=f"/admin/users/{target_id}/edit", status_code=status.HTTP_302_FOUND)


@router.post("/{target_id}/toggle-active")
def toggle_active(
    request: Request,
    target_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Quick activate/deactivate toggle from the users list."""
    service = UsersService(db)
    try:
        service.toggle_active(current_user, target_id)
    except (SelfActionError, LastAdminGuardError, UsersError) as exc:
        return RedirectResponse(
            url=f"/admin/users?error={quote(str(exc))}", status_code=status.HTTP_302_FOUND
        )
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
