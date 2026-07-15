"""HTTP routes for the providers module (admin-only)."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

from app.core.csrf import verify_csrf
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.templates import templates
from app.modules.auth.models import User
from app.modules.providers.service import DuplicateProviderNameError, ProvidersError, ProvidersService
from app.modules.providers.validators import ProviderValidationFailure
from app.providers.registry import DRIVER_LABELS

router = APIRouter(prefix="/admin/providers", tags=["providers"])


@router.get("")
def list_providers(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all configured provider accounts."""
    service = ProvidersService(db)
    return templates.TemplateResponse(
        request,
        "providers/list.html",
        {
            "user": current_user,
            "active_page": "providers",
            "breadcrumb": "Quản trị > Nhà cung cấp",
            "providers": service.list_providers(),
            "info": request.query_params.get("info"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/new")
def new_provider_form(request: Request, current_user: User = Depends(require_admin)):
    """Render the create-provider form."""
    return templates.TemplateResponse(
        request,
        "providers/form.html",
        {
            "user": current_user,
            "active_page": "providers",
            "breadcrumb": "Quản trị > Nhà cung cấp > Thêm mới",
            "mode": "create",
            "provider": None,
            "error": None,
            "drivers": DRIVER_LABELS,
            "csrf_token": request.session.get("csrf_token"),
            "form_markup_percent": 0,
        },
    )


@router.post("/new")
def create_provider(
    request: Request,
    name: str = Form(...),
    driver: str = Form(...),
    api_url: str = Form(...),
    api_key: str = Form(...),
    markup_percent: float = Form(0.0),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Handle create-provider form submission."""
    service = ProvidersService(db)
    try:
        service.create_provider(
            name=name, driver=driver, api_url=api_url, api_key=api_key, markup_percent=markup_percent
        )
    except (DuplicateProviderNameError, ProviderValidationFailure) as exc:
        return templates.TemplateResponse(
            request,
            "providers/form.html",
            {
                "user": current_user,
                "active_page": "providers",
                "breadcrumb": "Quản trị > Nhà cung cấp > Thêm mới",
                "mode": "create",
                "provider": None,
                "error": str(exc),
                "drivers": DRIVER_LABELS,
                "csrf_token": request.session.get("csrf_token"),
                "form_name": name,
                "form_driver": driver,
                "form_api_url": api_url,
                "form_markup_percent": markup_percent,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/admin/providers", status_code=status.HTTP_302_FOUND)


@router.get("/{provider_id}/edit")
def edit_provider_form(
    request: Request,
    provider_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Render the edit-provider form."""
    service = ProvidersService(db)
    provider = service.get_provider(provider_id)
    if provider is None:
        return RedirectResponse(url="/admin/providers", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request,
        "providers/form.html",
        {
            "user": current_user,
            "active_page": "providers",
            "breadcrumb": "Quản trị > Nhà cung cấp > Sửa",
            "mode": "edit",
            "provider": provider,
            "error": None,
            "drivers": DRIVER_LABELS,
            "csrf_token": request.session.get("csrf_token"),
        },
    )


@router.post("/{provider_id}/edit")
def update_provider(
    request: Request,
    provider_id: int,
    name: str = Form(...),
    driver: str = Form(...),
    api_url: str = Form(...),
    api_key: str = Form(...),
    markup_percent: float = Form(0.0),
    is_active: bool = Form(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Handle edit-provider form submission."""
    service = ProvidersService(db)
    try:
        service.update_provider(
            provider_id,
            name=name,
            driver=driver,
            api_url=api_url,
            api_key=api_key,
            markup_percent=markup_percent,
            is_active=is_active,
        )
    except (DuplicateProviderNameError, ProviderValidationFailure, ProvidersError) as exc:
        provider = service.get_provider(provider_id)
        return templates.TemplateResponse(
            request,
            "providers/form.html",
            {
                "user": current_user,
                "active_page": "providers",
                "breadcrumb": "Quản trị > Nhà cung cấp > Sửa",
                "mode": "edit",
                "provider": provider,
                "error": str(exc),
                "drivers": DRIVER_LABELS,
                "csrf_token": request.session.get("csrf_token"),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/admin/providers", status_code=status.HTTP_302_FOUND)


@router.post("/{provider_id}/delete")
def delete_provider(
    provider_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Delete a provider account."""
    service = ProvidersService(db)
    try:
        service.delete_provider(provider_id)
    except ProvidersError as exc:
        return RedirectResponse(url=f"/admin/providers?error={quote(str(exc))}", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/admin/providers", status_code=status.HTTP_302_FOUND)


@router.post("/{provider_id}/toggle-active")
def toggle_active(
    provider_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Quick activate/deactivate toggle from the providers list."""
    service = ProvidersService(db)
    try:
        service.toggle_active(provider_id)
    except ProvidersError as exc:
        return RedirectResponse(url=f"/admin/providers?error={quote(str(exc))}", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/admin/providers", status_code=status.HTTP_302_FOUND)


@router.post("/{provider_id}/test")
def test_connection(
    provider_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Call the provider's balance endpoint and cache the result."""
    service = ProvidersService(db)
    try:
        success, message = service.test_connection(provider_id)
    except ProvidersError as exc:
        return RedirectResponse(url=f"/admin/providers?error={quote(str(exc))}", status_code=status.HTTP_302_FOUND)
    param = "info" if success else "error"
    return RedirectResponse(url=f"/admin/providers?{param}={quote(message)}", status_code=status.HTTP_302_FOUND)
