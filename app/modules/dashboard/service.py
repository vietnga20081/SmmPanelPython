"""Business logic assembling dashboard views for admin/staff vs. client roles."""
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole
from app.modules.dashboard.repository import DashboardRepository, seven_days_ago
from app.modules.dashboard.schemas import AdminDashboardStats, ClientDashboardStats, RecentUserItem


class DashboardService:
    """Builds the read-only dashboard payload for the current user's role."""

    def __init__(self, db: Session) -> None:
        self._repo = DashboardRepository(db)

    def get_admin_dashboard(self) -> AdminDashboardStats:
        """System-wide stats, shown to admin and staff."""
        total_users = self._repo.count_total_users()
        active_users = self._repo.count_active_users()
        recent = self._repo.get_recent_users()
        return AdminDashboardStats(
            total_users=total_users,
            total_admins=self._repo.count_users_by_role(UserRole.ADMIN),
            total_staff=self._repo.count_users_by_role(UserRole.STAFF),
            total_clients=self._repo.count_users_by_role(UserRole.CLIENT),
            active_users=active_users,
            inactive_users=total_users - active_users,
            new_users_last_7_days=self._repo.count_new_users_since(seven_days_ago()),
            recent_users=[RecentUserItem.model_validate(u) for u in recent],
        )

    def get_client_dashboard(self, user: User) -> ClientDashboardStats:
        """Personal stats for a client account."""
        return ClientDashboardStats(
            username=user.username,
            email=user.email,
            balance=user.balance,
            role=user.role,
            is_active=user.is_active,
            member_since=user.created_at,
        )
