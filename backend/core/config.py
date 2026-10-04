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
    # Public deployment: one database per browser workspace (backend/core/workspace.py).
    workspaces: bool = os.getenv("WORKSPACES", "false").strip().lower() in ("1", "true", "yes")
    workspace_dir: str = os.getenv("WORKSPACE_DIR", "data/workspaces")
    max_new_workspaces_per_hour: int = int(os.getenv("MAX_NEW_WORKSPACES_PER_HOUR", "30"))
    max_analyses_per_hour: int = int(os.getenv("MAX_ANALYSES_PER_HOUR", "20"))
    # Optional: POST a phone alert here when a new browser opens the app (backend/core/notify.py).
    notify_url: str = os.getenv("NOTIFY_URL", "").strip()
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    # Empty disables the file log (console only).
    log_file: str = os.getenv("LOG_FILE", "data/logs/backend.log")
    # "text" (human-readable) or "json" (one JSON object per line, for log tooling).
    log_format: str = os.getenv("LOG_FORMAT", "text")


settings = Settings()
