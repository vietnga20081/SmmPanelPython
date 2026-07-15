"""HTTP routes for the dashboard module."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.templates import templates
from app.modules.auth.models import User, UserRole
from app.modules.dashboard.service import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render the role-appropriate dashboard: system overview or personal overview."""
    service = DashboardService(db)

    if current_user.role in (UserRole.ADMIN, UserRole.STAFF):
        stats = service.get_admin_dashboard()
        return templates.TemplateResponse(
            request,
            "dashboard/admin.html",
            {"user": current_user, "stats": stats, "active_page": "dashboard", "breadcrumb": "Dashboard"},
        )

    stats = service.get_client_dashboard(current_user)
    return templates.TemplateResponse(
        request,
        "dashboard/client.html",
        {"user": current_user, "stats": stats, "active_page": "dashboard", "breadcrumb": "Dashboard"},
    )
