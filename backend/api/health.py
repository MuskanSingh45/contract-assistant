from fastapi import APIRouter, Depends

from ai.llm.client import active_config, available_for
from ai.llm.model_config import fallback_provider, load_config
from backend.core.dependencies import get_db

router = APIRouter()


@router.get("/health")
def health(conn=Depends(get_db)):
    try:
        conn.execute("SELECT 1 FROM schema_migrations LIMIT 1")
        database = "ok"
    except Exception:  # noqa: BLE001
        database = "error"
    config = active_config()  # the primary provider, or the fallback when the primary is down
    reachable, model_ok = available_for(config)
    ok = database == "ok" and reachable and model_ok
    return {
        "status": "ok" if ok else "degraded",
        "database": database,
        "llm": {
            "provider": config.provider,
            "primary": load_config().provider,
            "fallback": fallback_provider(),
            "model": config.model,
            "reachable": reachable,
            "model_available": model_ok,
        },
    }
