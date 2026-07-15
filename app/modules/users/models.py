"""The Users module has no models of its own.

It manages the same `User` entity owned by the auth module
(app.modules.auth.models.User) — one shared `users` table, not a duplicate.
Re-exported here so `from app.modules.users.models import User` also works,
matching the standard per-module layout.
"""
from app.modules.auth.models import User, UserRole

__all__ = ["User", "UserRole"]
