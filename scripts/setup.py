"""Apply pending migrations to the configured database (no data loss). Run from repo root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.config import settings
from db.database import connect, migrate

print("migrations applied:", migrate(connect(settings.database_path)) or "none pending")
