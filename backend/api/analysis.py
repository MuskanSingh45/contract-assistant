from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request

from backend.core.dependencies import get_db
from backend.core.workspace import check_analysis_allowed, workspace_from_request
from backend.schemas.analysis import AnalyzeRequest
from backend.services import analysis_service

router = APIRouter()


@router.post("/contracts/{contract_id}/analyze", status_code=202)
def analyze(
    contract_id: str,
    request: Request,
    background: BackgroundTasks,
    body: AnalyzeRequest | None = Body(None),
    conn=Depends(get_db),
):
    workspace = workspace_from_request(request)
    check_analysis_allowed(request, workspace)
    version = analysis_service.start(conn, contract_id, body.version_id if body else None)
    # The background task opens its own connection, so it must know which workspace database to use.
    background.add_task(analysis_service.run, version["id"], workspace)
    return {"contract_id": contract_id, "version_id": version["id"], "analysis_status": "queued"}


@router.get("/contracts/{contract_id}/analysis")
def analysis_status(contract_id: str, version_id: str | None = None, conn=Depends(get_db)):
    return analysis_service.status(conn, contract_id, version_id)
