"""FastAPI application entry point. Run with: uvicorn app.main:app"""
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine, init_engine
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware import CSRFMiddleware, SecureHeadersMiddleware
from app.core.schema_migrations import apply_schema_migrations
from app.modules.auth.models import UserRole
from app.modules.auth.routes import router as auth_router
from app.modules.auth.service import AuthService
from app.modules.dashboard.routes import router as dashboard_router
from app.modules.providers.routes import router as providers_router
from app.modules.services.routes import router as services_router
from app.modules.services.seed import seed_platforms
from app.modules.users.routes import router as users_router

settings = get_settings()

configure_logging()
logger = get_logger("app")

init_engine()
Base.metadata.create_all(bind=engine)
apply_schema_migrations(engine)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(SecureHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=not settings.debug,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(users_router)
app.include_router(providers_router)
app.include_router(services_router)


def _seed_default_admin() -> None:
    """Create a default admin account on first run if the users table is empty."""
    db = SessionLocal()
    try:
        service = AuthService(db)
        existing = service.get_user(1)
        if existing is not None:
            return
        from app.modules.auth.repository import UserRepository

        if UserRepository(db).get_by_username("admin") is not None:
            return
        service.register_user(
            username="admin",
            email="admin@localhost",
            password="ChangeMe123!",
            role=UserRole.ADMIN,
        )
        logger.info("seeded default admin account (username=admin, password=ChangeMe123!)")
    finally:
        db.close()


def _seed_service_platforms() -> None:
    """Seed the standard Platform list (Facebook, TikTok, ...) on first run."""
    db = SessionLocal()
    try:
        seed_platforms(db)
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    """Application startup hook: seed default data."""
    _seed_default_admin()
    _seed_service_platforms()


@app.get("/")
def root() -> RedirectResponse:
    """Redirect the root path to the dashboard (which itself requires login)."""
    return RedirectResponse(url="/dashboard")
