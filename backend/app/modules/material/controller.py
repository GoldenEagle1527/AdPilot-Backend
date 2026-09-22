"""漫剧库 HTTP。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.material.schema import ManhuaSeriesItem, ManhuaSeriesQuery
from app.modules.material.service import list_manhua_series
from app.modules.system_admin import require_menu

router = APIRouter(prefix="/api/v1/material", tags=["material"])

PrincipalDep = Annotated[dict[str, Any], Depends(require_menu("95"))]


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
