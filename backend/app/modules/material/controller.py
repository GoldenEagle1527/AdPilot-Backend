"""漫剧库 HTTP。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.material.schema import ManhuaSeriesItem, ManhuaSeriesQuery
from app.modules.material.service import export_manhua_series, list_manhua_series
from app.modules.system_admin import require_menu

router = APIRouter(prefix="/api/v1/material", tags=["material"])

PrincipalDep = Annotated[dict[str, Any], Depends(require_menu("95"))]

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/manhua-series",
    response_model=Envelope[PageData[ManhuaSeriesItem]],
    summary="分页查询漫剧库",
)
async def get_manhua_series(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: PrincipalDep,
    query: Annotated[ManhuaSeriesQuery, Query()],
) -> dict[str, Any]:
    """按查询条件分页列出漫剧库。"""
    return success(await list_manhua_series(session, query))


@router.post(
    "/manhua-series/export",
    summary="导出漫剧库",
    response_class=StreamingResponse,
    responses={200: {"content": {_XLSX: {"schema": {"type": "string", "format": "binary"}}}}},
)
async def post_manhua_series_export(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: PrincipalDep,
    query: Annotated[ManhuaSeriesQuery, Query()],
) -> StreamingResponse:
    """按列表相同筛选导出全部匹配行，文件为 xlsx。"""
    payload = await export_manhua_series(session, query)
    return StreamingResponse(
        iter([payload]),
        media_type=_XLSX,
        headers={"Content-Disposition": 'attachment; filename="manhua_series.xlsx"'},
    )
