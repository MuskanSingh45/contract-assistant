from typing import Literal

from fastapi import APIRouter, Depends

from backend.core.dependencies import get_db
from backend.schemas.review import ResolveRequest, ReviewRequest
from backend.services import review_service

router = APIRouter()


@router.get("/reviews/queue")
def review_queue(
    contract_id: str | None = None,
    entity_type: Literal["extracted_item", "obligation"] | None = None,
    conn=Depends(get_db),
):
    return {"items": review_service.queue(conn, contract_id, entity_type)}


@router.get("/reviews/recent")
def recent_reviews(limit: int = 10, conn=Depends(get_db)):
    return {"items": review_service.recent(conn, min(max(limit, 1), 50))}


@router.post("/reviews")
def review(body: ReviewRequest, conn=Depends(get_db)):
    return review_service.apply_review(conn, body.entity_type, body.entity_id, body.action, body.value, body.note)


@router.get("/reviews")
def review_history(entity_type: Literal["extracted_item", "obligation"], entity_id: str, conn=Depends(get_db)):
    return {"items": review_service.history(conn, entity_type, entity_id)}


@router.get("/items/{entity_type}/{entity_id}")
def item_detail(entity_type: Literal["extracted_item", "obligation"], entity_id: str, conn=Depends(get_db)):
    return review_service.entity_detail(conn, entity_type, entity_id)


@router.get("/clarifications")
def clarifications(
    contract_id: str | None = None, status: Literal["open", "resolved", "dismissed"] | None = None, conn=Depends(get_db)
):
    return {"items": review_service.list_clarifications(conn, contract_id, status)}


@router.post("/clarifications/{clarification_id}/resolve")
def resolve(clarification_id: str, body: ResolveRequest, conn=Depends(get_db)):
    return review_service.resolve_clarification(conn, clarification_id, body.model_dump())


@router.get("/citations/{citation_id}")
def citation(citation_id: str, conn=Depends(get_db)):
    return review_service.citation_detail(conn, citation_id)
