"""Configuration from environment variables (see .env.example)."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    database_path: str = os.getenv("DATABASE_PATH", "data/app.db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    frontend_origins: list[str] = field(
        default_factory=lambda: _list(os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://localhost:8080"))
    )
    upcoming_window_days: int = int(os.getenv("UPCOMING_WINDOW_DAYS", "60"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    # Empty disables the file log (console only).
    log_file: str = os.getenv("LOG_FILE", "data/logs/backend.log")
    # "text" (human-readable) or "json" (one JSON object per line, for log tooling).
    log_format: str = os.getenv("LOG_FORMAT", "text")


settings = Settings()
