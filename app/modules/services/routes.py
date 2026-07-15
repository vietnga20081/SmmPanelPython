"""HTTP routes for the services module (admin-only)."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

from app.core.csrf import verify_csrf
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.templates import templates
from app.modules.auth.models import User
from app.modules.providers.repository import ProvidersRepository
from app.modules.providers.validators import ProviderValidationFailure, validate_markup_percent
from app.modules.services.service import ServicesError, ServicesService
from app.modules.services.validators import ServiceValidationFailure

router = APIRouter(prefix="/admin/services", tags=["services"])


@router.get("")
def list_services(
    request: Request,
    q: str = Query(default=""),
    platform_id: str = Query(default="", alias="platform"),
    category_id: str = Query(default="", alias="category"),
    provider_id: str = Query(default="", alias="provider"),
    status_filter: str = Query(default="", alias="status"),
    page: int = Query(default=1, ge=1),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List synced services with search/filter/pagination + platform breakdown KPIs."""
    service = ServicesService(db)

    platform_id_int = int(platform_id) if platform_id.isdigit() else None
    category_id_int = int(category_id) if category_id.isdigit() else None
    provider_id_int = int(provider_id) if provider_id.isdigit() else None

    items, total = service.list_services(q, platform_id_int, category_id_int, provider_id_int, status_filter, page)
    stats = service.get_stats()
    platforms = service.list_platforms()
    categories = service.list_categories(platform_id_int) if platform_id_int else []
    all_categories = service.list_all_categories()
    providers = ProvidersRepository(db).list_all()

    import math
    total_pages = max(math.ceil(total / 15), 1)

    return templates.TemplateResponse(
        request,
        "services/list.html",
        {
            "user": current_user,
            "active_page": "services",
            "breadcrumb": "Quản trị > Dịch vụ",
            "items": items,
            "stats": stats,
            "platforms": platforms,
            "categories": categories,
            "all_categories": all_categories,
            "providers": providers,
            "q": q,
            "platform_id": platform_id,
            "category_id": category_id,
            "provider_id": provider_id,
            "status_filter": status_filter,
            "page": page,
            "total": total,
            "total_pages": total_pages,
            "info": request.query_params.get("info"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/sync")
def sync_provider(
    request: Request,
    provider_id: int = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Sync a provider's full catalog into the local service catalog."""
    service = ServicesService(db)
    try:
        result = service.sync_provider(provider_id)
    except ServicesError as exc:
        return RedirectResponse(url=f"/admin/services?error={quote(str(exc))}", status_code=status.HTTP_302_FOUND)

    message = (
        f"Đồng bộ xong: {result.created} mới, {result.updated} cập nhật, "
        f"{result.failed} lỗi (tổng {result.total_from_provider} dịch vụ từ provider)."
    )
    return RedirectResponse(url=f"/admin/services?info={quote(message)}", status_code=status.HTTP_302_FOUND)


@router.post("/bulk")
def bulk_action(
    request: Request,
    action: str = Form(...),
    service_ids: list[int] = Form(default=[]),
    markup_percent: float = Form(default=0.0),
    status_value: str = Form(default="active"),
    platform_id: int | None = Form(default=None),
    category_id: int | None = Form(default=None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Apply a bulk action (markup %, status, or category) to selected services."""
    if not service_ids:
        return RedirectResponse(
            url=f"/admin/services?error={quote('Chưa chọn dịch vụ nào.')}", status_code=status.HTTP_302_FOUND
        )

    service = ServicesService(db)
    try:
        if action == "markup":
            markup_percent = validate_markup_percent(markup_percent)
            count = service.bulk_apply_markup(service_ids, markup_percent)
            message = f"Đã áp dụng markup {markup_percent}% cho {count} dịch vụ."
        elif action == "status":
            is_active = status_value == "active"
            count = service.bulk_set_status(service_ids, is_active)
            message = f"Đã đổi trạng thái {count} dịch vụ thành {'Đang bán' if is_active else 'Chưa bán'}."
        elif action == "category":
            if platform_id is None or category_id is None:
                raise ServicesError("Vui lòng chọn Platform và Category.")
            count = service.bulk_set_category(service_ids, platform_id, category_id)
            message = f"Đã cập nhật danh mục cho {count} dịch vụ."
        else:
            raise ServicesError("Hành động không hợp lệ.")
    except (ServicesError, ProviderValidationFailure) as exc:
        return RedirectResponse(url=f"/admin/services?error={quote(str(exc))}", status_code=status.HTTP_302_FOUND)

    return RedirectResponse(url=f"/admin/services?info={quote(message)}", status_code=status.HTTP_302_FOUND)


@router.get("/{service_id}/edit")
def edit_service_form(
    request: Request,
    service_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Render the edit-service form (name, platform/category override, sell price)."""
    service = ServicesService(db)
    target = service.get_service(service_id)
    if target is None:
        return RedirectResponse(url="/admin/services", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request,
        "services/edit.html",
        {
            "user": current_user,
            "active_page": "services",
            "breadcrumb": "Quản trị > Dịch vụ > Sửa",
            "target": target,
            "platforms": service.list_platforms(),
            "categories": service.list_all_categories(),
            "error": None,
            "csrf_token": request.session.get("csrf_token"),
        },
    )


@router.post("/{service_id}/edit")
def update_service(
    request: Request,
    service_id: int,
    name: str = Form(...),
    platform_id: int = Form(...),
    category_id: int = Form(...),
    sell_price: float = Form(...),
    is_active: bool = Form(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Handle edit-service form submission."""
    service = ServicesService(db)
    try:
        service.update_service(
            service_id, name=name, platform_id=platform_id, category_id=category_id,
            sell_price=sell_price, is_active=is_active,
        )
    except (ServicesError, ServiceValidationFailure) as exc:
        target = service.get_service(service_id)
        return templates.TemplateResponse(
            request,
            "services/edit.html",
            {
                "user": current_user,
                "active_page": "services",
                "breadcrumb": "Quản trị > Dịch vụ > Sửa",
                "target": target,
                "platforms": service.list_platforms(),
                "categories": service.list_all_categories(),
                "error": str(exc),
                "csrf_token": request.session.get("csrf_token"),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/admin/services", status_code=status.HTTP_302_FOUND)


@router.post("/{service_id}/toggle-active")
def toggle_active(
    service_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf),
):
    """Quick activate/deactivate toggle from the services list."""
    service = ServicesService(db)
    try:
        service.toggle_active(service_id)
    except ServicesError as exc:
        return RedirectResponse(url=f"/admin/services?error={quote(str(exc))}", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/admin/services", status_code=status.HTTP_302_FOUND)
