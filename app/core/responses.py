"""Standard response models (shared/types/api.ts). Every route returns `ok(...)` or raises FrmError."""

from __future__ import annotations

import math
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class ApiErrorDetail(BaseModel):
    field: str
    message: str


class ApiErrorBody(BaseModel):
    code: str
    message: str
    trace_id: str
    details: list[ApiErrorDetail] = Field(default_factory=list)


class ApiFailure(BaseModel):
    success: Literal[False] = False
    error: ApiErrorBody


class ApiSuccess(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: Literal[True] = True
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)


class ListMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    total_capped: bool | None = None


class CursorMeta(BaseModel):
    next_cursor: str | None


class PageParams(BaseModel):
    """`page`, `page_size` (≤100, default 20) exactly as the mock's paginate()."""

    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @classmethod
    def from_query(cls, page: object = None, page_size: object = None) -> PageParams:
        def as_int(value: object, default: int) -> int:
            try:
                return int(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return default

        p = max(1, as_int(page, 1) or 1)
        size = min(MAX_PAGE_SIZE, max(1, as_int(page_size, DEFAULT_PAGE_SIZE) or DEFAULT_PAGE_SIZE))
        return cls(page=p, page_size=size)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def meta(self, total: int, *, capped: bool = False) -> ListMeta:
        return ListMeta(
            page=self.page,
            page_size=self.page_size,
            total=total,
            total_pages=max(1, math.ceil(total / self.page_size)),
            total_capped=True if capped else None,
        )


def ok(data: T, meta: BaseModel | dict[str, Any] | None = None) -> ApiSuccess[T]:
    if isinstance(meta, BaseModel):
        meta = meta.model_dump(exclude_none=True)
    return ApiSuccess[T](data=data, meta=meta or {})
