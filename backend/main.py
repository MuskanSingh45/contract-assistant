"""FastAPI app. Run from repo root: uvicorn backend.main:app --reload"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import analysis, contracts, health, obligations, reviews, versions
from backend.core.config import settings
from backend.core.exceptions import register_error_handlers
from backend.core.limits import UploadSizeLimitMiddleware
from backend.core.logging import REQUEST_ID_HEADER, RequestContextMiddleware, setup_logging
from backend.core.workspace import workspace_databases
from backend.services import analysis_service
from db.database import connect, migrate

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    # The default database plus, on the public deployment, every workspace database.
    for path in [settings.database_path, *workspace_databases()]:
        conn = connect(path)
        try:
            migrate(conn)
            analysis_service.mark_interrupted(conn)
        finally:
            conn.close()
    log.info(
        "Started (env=%s, database=%s, workspaces=%s, log_file=%s)",
        settings.app_env,
        settings.database_path,
        settings.workspaces,
        settings.log_file or "console only",
        extra={"event": "app.started"},
    )
    yield


app = FastAPI(
    title="Contract Obligation and Renewal Assistant API",
    description="Information-management tool. Not legal advice. Contract: docs/api/.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)
# Added last = outermost, so the request ID is set before CORS and every handler runs.
app.add_middleware(UploadSizeLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
register_error_handlers(app)

for module in (health, contracts, analysis, versions, obligations, reviews):
    app.include_router(module.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    """Landing response for the bare server URL (e.g. the hosted Space page)."""
    return {"service": app.title, "api": "/api", "docs": "/docs", "health": "/api/health"}
