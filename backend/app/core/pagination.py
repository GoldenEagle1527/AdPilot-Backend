from __future__ import annotations

from typing import Generic, Sequence, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PageData(BaseModel, Generic[T]):
    """分页响应体。列表字段名对外是 list。"""

    items: Sequence[T] = Field(serialization_alias="list", validation_alias="list")
    total: int
    page: int
    page_size: int


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


def page_data(
    items: Sequence[T],
    total: int,
    params: PageParams,
) -> dict[str, object]:
    return {
        "list": list(items),
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
    }


def page_slice(items: Sequence[T], params: PageParams) -> dict[str, object]:
    """按页截取已经在内存里的序列。total 是截取前的条数。"""
    start = params.offset
    return page_data(list(items[start : start + params.page_size]), len(items), params)
