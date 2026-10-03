from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.core.dependencies import get_db
from backend.services import contract_service, document_service, version_service
from backend.services.common import get_contract

router = APIRouter()


@router.get("/dashboard")
def dashboard(conn=Depends(get_db)):
    return contract_service.dashboard(conn)


@router.get("/contracts")
def list_contracts(
    search: str | None = None,
    lifecycle_status: str | None = None,
    needs_review: bool | None = None,
    conn=Depends(get_db),
):
    return {"items": contract_service.list_contracts(conn, search, lifecycle_status, needs_review)}


@router.post("/contracts", status_code=201)
async def upload_contract(file: UploadFile | None = File(None), name: str | None = Form(None), conn=Depends(get_db)):
    data = await file.read() if file else b""
    contract_id, version_id = document_service.create_contract(conn, file.filename if file else None, data, name)
    return {
        "contract": contract_service.contract_summary(conn, get_contract(conn, contract_id)),
        "version": version_service.get_version_out(conn, contract_id, version_id),
    }


@router.get("/contracts/{contract_id}")
def contract_detail(contract_id: str, version_id: str | None = None, conn=Depends(get_db)):
    return contract_service.contract_detail(conn, contract_id, version_id)


@router.get("/contracts/{contract_id}/extracted-items")
def extracted_items(
    contract_id: str, version_id: str | None = None, field_name: str | None = None, conn=Depends(get_db)
):
    return {"items": contract_service.extracted_items(conn, contract_id, version_id, field_name)}
