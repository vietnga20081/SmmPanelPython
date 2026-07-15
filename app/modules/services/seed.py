"""Seed the standard Platform list on first run (idempotent)."""
from sqlalchemy.orm import Session

from app.modules.services.classifier import DEFAULT_PLATFORM, PLATFORM_RULES, slugify
from app.modules.services.repository import PlatformRepository

_EXTRA_PLATFORMS = [DEFAULT_PLATFORM]


def seed_platforms(db: Session) -> None:
    """Create every platform referenced by the classifier rules, if missing."""
    repo = PlatformRepository(db)
    names = [name for name, _ in PLATFORM_RULES] + _EXTRA_PLATFORMS
    for order, name in enumerate(names):
        if repo.get_by_name(name) is None:
            db.add(_new_platform(name, order))
    db.commit()


def _new_platform(name: str, sort_order: int):
    from app.modules.services.models import Platform

    return Platform(name=name, slug=slugify(name), sort_order=sort_order)
