from fastapi import APIRouter, Depends, File, UploadFile

from backend.core.dependencies import get_db
from backend.services import document_service, version_service

router = APIRouter()


@router.get("/contracts/{contract_id}/versions")
def list_versions(contract_id: str, conn=Depends(get_db)):
    return {"items": version_service.list_versions(conn, contract_id)}


@router.post("/contracts/{contract_id}/versions", status_code=201)
async def upload_version(contract_id: str, file: UploadFile | None = File(None), conn=Depends(get_db)):
    data = await file.read() if file else b""
    version_id = document_service.create_version(conn, contract_id, file.filename if file else None, data)
    return version_service.get_version_out(conn, contract_id, version_id)


@router.get("/contracts/{contract_id}/versions/{version_id}/changes")
def version_changes(contract_id: str, version_id: str, conn=Depends(get_db)):
    return version_service.changes(conn, contract_id, version_id)
