from fastapi import APIRouter, Depends

from ai.llm.model_config import load_config
from ai.llm.ollama_client import check_available
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
    ok = database == "ok" and reachable and model_ok
    return {
        "status": "ok" if ok else "degraded",
        "database": database,
        "ollama": {"reachable": reachable, "model": load_config().model, "model_available": model_ok},
    }
