from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.services import analysis_service, common
from db.database import connect, load_seed, migrate

TODAY = date(2026, 10, 3)


@pytest.fixture
def client(monkeypatch):
    db = Path(settings.database_path)
    for suffix in ("", "-wal", "-shm"):
        Path(f"{db}{suffix}").unlink(missing_ok=True)
    conn = connect(db)
    migrate(conn)
    load_seed(conn)
    conn.close()
    # Freeze "today" everywhere the services read it.
    monkeypatch.setattr(common, "today", lambda: TODAY)
    for module in ("calculation_service", "contract_service", "obligation_service", "review_service"):
        monkeypatch.setattr(f"backend.services.{module}.today", lambda: TODAY)
    monkeypatch.setattr(analysis_service, "check_available", lambda: (True, True))
    from backend.main import app

    with TestClient(app) as c:
        yield c
