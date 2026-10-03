from fastapi import APIRouter, BackgroundTasks, Body, Depends

from backend.core.dependencies import get_db
from backend.schemas.analysis import AnalyzeRequest
from backend.services import analysis_service

router = APIRouter()


@router.post("/contracts/{contract_id}/analyze", status_code=202)
def analyze(
    contract_id: str, background: BackgroundTasks, body: AnalyzeRequest | None = Body(None), conn=Depends(get_db)
):
    version = analysis_service.start(conn, contract_id, body.version_id if body else None)
    background.add_task(analysis_service.run, version["id"])
    return {"contract_id": contract_id, "version_id": version["id"], "analysis_status": "queued"}


@router.get("/contracts/{contract_id}/analysis")
def analysis_status(contract_id: str, version_id: str | None = None, conn=Depends(get_db)):
    return analysis_service.status(conn, contract_id, version_id)
