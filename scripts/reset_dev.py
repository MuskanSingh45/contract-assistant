"""Delete the dev database, re-apply migrations and load the demo seed. Run from repo root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.config import settings
from db.database import connect, load_seed, migrate

db_path = Path(settings.database_path)
for suffix in ("", "-wal", "-shm"):
    Path(f"{db_path}{suffix}").unlink(missing_ok=True)
conn = connect(db_path)
print("migrations applied:", migrate(conn))
if "--no-seed" not in sys.argv:
    load_seed(conn)
    print("seed loaded")
