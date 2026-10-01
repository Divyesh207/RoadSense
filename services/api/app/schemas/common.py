from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ResponseMeta(BaseModel):
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaginationMeta(ResponseMeta):
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ResponseEnvelope(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT | None = None
    error: ErrorDetail | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class PaginatedResponseEnvelope(BaseModel, Generic[DataT]):
    success: bool = True
    data: list[DataT] = Field(default_factory=list)
    error: ErrorDetail | None = None
    meta: PaginationMeta
