"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SMM Panel"
    app_env: str = "production"
    debug: bool = False

    database_path: str = "./data/smm_panel.db"

    secret_key: str = "insecure-dev-secret-key-change-me"
    session_cookie_name: str = "smm_session"
    session_max_age_seconds: int = 86400
    remember_cookie_name: str = "smm_remember"
    remember_max_age_seconds: int = 2592000

    jwt_secret_key: str = "insecure-dev-jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    csrf_header_name: str = "X-CSRF-Token"
    csrf_field_name: str = "csrf_token"

    log_dir: str = "./logs"
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        """Build the SQLite SQLAlchemy URL, ensuring the parent directory exists."""
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
