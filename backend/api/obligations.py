from datetime import date

from fastapi import APIRouter, Body, Depends

from backend.core.dependencies import get_db
from backend.services import obligation_service, review_service

router = APIRouter()


@router.get("/obligations")
def list_obligations(
    contract_id: str | None = None,
    version_id: str | None = None,
    status: str | None = None,
    review_status: str | None = None,
    responsible_party: str | None = None,
    due_before: date | None = None,
    conn=Depends(get_db),
):
    return {
        "items": obligation_service.list_obligations(
            conn,
            contract_id=contract_id,
            version_id=version_id,
            status=status,
            review_status=review_status,
            responsible_party=responsible_party,
            due_before=due_before,
        )
    }


@router.get("/obligations/{obligation_id}")
def get_obligation(obligation_id: str, conn=Depends(get_db)):
    return obligation_service.get_obligation(conn, obligation_id)


@router.patch("/obligations/{obligation_id}")
def patch_obligation(obligation_id: str, body: dict = Body(...), conn=Depends(get_db)):
    # A raw object (not a Pydantic model), so any field other than `status` can be rejected with
    # VALIDATION_ERROR by review_service.set_obligation_status.
    return review_service.set_obligation_status(conn, obligation_id, body)


@router.get("/renewals")
def list_renewals(within_days: int | None = None, calculation_status: str | None = None, conn=Depends(get_db)):
    return {"items": obligation_service.list_renewals(conn, within_days, calculation_status)}
