from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData, PageParams, page_data, page_params
from app.core.times import iso8601_z
from app.modules.material.domain.models import ManhuaSeries
from app.modules.material.domain.queries import list_filters, list_statement
from app.modules.material.domain.times import display_changdu_time
from app.modules.material.schemas.manhua_series import ManhuaSeriesItem
from app.modules.system_admin import require_menu

MENU_MANHUA_SERIES = "95"

router = APIRouter(prefix="/api/v1/material", tags=["material"])
PrincipalDep = Annotated[dict, Depends(require_menu(MENU_MANHUA_SERIES))]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def serialize_item(row: ManhuaSeries) -> ManhuaSeriesItem:
    return ManhuaSeriesItem(
        id=str(row.id),
        playlet_id=str(row.playlet_id),
        book_id=str(row.book_id),
        category_text=row.category_text,
        thumb_url=row.thumb_url,
        book_name=row.book_name,
        episode_amount=row.episode_amount,
        department_name=None,
        publish_status=row.publish_status,
        delivery_status=row.delivery_status,
        publish_time=display_changdu_time(row.publish_time),
        estimate_publish_time=display_changdu_time(row.estimate_publish_time),
        create_time=display_changdu_time(row.create_time),
        collected_at=iso8601_z(row.collected_at),
        douyin_nick_name=row.douyin_nick_name,
    )


@router.get("/manhua-series", response_model=Envelope[PageData[ManhuaSeriesItem]])
async def list_manhua_series(
    _user: PrincipalDep,
    session: SessionDep,
    paging: Annotated[PageParams, Depends(page_params)],
    category_text: str | None = None,
    book_name: str | None = None,
    estimate_publish_time_from: datetime | None = None,
    estimate_publish_time_to: datetime | None = None,
    collected_at_from: datetime | None = None,
    collected_at_to: datetime | None = None,
    publish_status: int | None = Query(default=None),
    listed_today: bool | None = None,
    department_id: str | None = None,
    episode_amount_min: int | None = None,
    episode_amount_max: int | None = None,
):
    filters = list_filters(
        category_text=category_text,
        book_name=book_name,
        estimate_publish_time_from=estimate_publish_time_from,
        estimate_publish_time_to=estimate_publish_time_to,
        collected_at_from=collected_at_from,
        collected_at_to=collected_at_to,
        publish_status=publish_status,
        listed_today=listed_today,
        department_id=department_id,
        episode_amount_min=episode_amount_min,
        episode_amount_max=episode_amount_max,
    )
    stmt = list_statement(filters)
    total = int(await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = (await session.execute(stmt.offset(paging.offset).limit(paging.page_size))).scalars().all()
    return success(page_data([serialize_item(row) for row in rows], total, paging))
