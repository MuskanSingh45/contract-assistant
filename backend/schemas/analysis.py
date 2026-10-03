from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    version_id: str | None = None
