from typing import Any, Literal

from pydantic import BaseModel


class ReviewRequest(BaseModel):
    entity_type: Literal["extracted_item", "obligation"]
    entity_id: str
    action: str  # validated by the service so the error code is INVALID_REVIEW_ACTION
    value: Any = None
    note: str | None = None


class ResolveRequest(BaseModel):
    action: str
    entity_id: str | None = None
    value: Any = None
    note: str | None = None
