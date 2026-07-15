"""Structured, rotating logging configuration. No print() anywhere in the app."""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

_JSON_FORMAT = (
    '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", '
    '"message": "%(message)s"}'
)

_CONFIGURED = False


def configure_logging() -> None:
    """Configure root and named loggers (app, audit, login, payment, api). Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_JSON_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S")

    root = logging.getLogger()
    root.setLevel(settings.log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    for logger_name in ("app", "audit", "login", "payment", "api"):
        _attach_rotating_file_handler(logger_name, log_dir, formatter)

    _CONFIGURED = True


def _attach_rotating_file_handler(logger_name: str, log_dir: Path, formatter: logging.Formatter) -> None:
    logger = logging.getLogger(logger_name)
    logger.setLevel(settings.log_level)
    handler = TimedRotatingFileHandler(
        filename=log_dir / f"{logger_name}.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return one of the named application loggers (app, audit, login, payment, api)."""
    return logging.getLogger(name)
