"""Load the demo seed into an already-migrated database. Run from repo root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.config import settings
from db.database import connect, load_seed, migrate

conn = connect(settings.database_path)
migrate(conn)
load_seed(conn)
print("seed loaded")
