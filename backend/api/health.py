from fastapi import APIRouter, Depends

from ai.llm.client import check_available
from ai.llm.model_config import load_config
from backend.core.dependencies import get_db

router = APIRouter()


@router.get("/health")
def health(conn=Depends(get_db)):
    try:
        conn.execute("SELECT 1 FROM schema_migrations LIMIT 1")
        database = "ok"
    except Exception:  # noqa: BLE001
        database = "error"
    reachable, model_ok = check_available()
    config = load_config()
    ok = database == "ok" and reachable and model_ok
    return {
        "status": "ok" if ok else "degraded",
        "database": database,
        "llm": {
            "provider": config.provider,
            "model": config.model,
            "reachable": reachable,
            "model_available": model_ok,
        },
    }
