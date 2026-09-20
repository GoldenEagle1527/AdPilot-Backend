from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, false, select
from sqlalchemy.sql import ColumnElement

from app.modules.material.domain.models import ManhuaSeries
from app.modules.material.domain.times import beijing_today_prefix, to_beijing_naive


def list_filters(
    *,
    category_text: str | None,
    book_name: str | None,
    estimate_publish_time_from: datetime | None,
    estimate_publish_time_to: datetime | None,
    collected_at_from: datetime | None,
    collected_at_to: datetime | None,
    publish_status: int | None,
    listed_today: bool | None,
    department_id: str | None,
    episode_amount_min: int | None,
    episode_amount_max: int | None,
    now: datetime | None = None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if department_id:
        filters.append(false())
        return filters
    if category_text:
        filters.append(ManhuaSeries.category_text == category_text.strip())
    if book_name:
        filters.append(ManhuaSeries.book_name.ilike(f"%{book_name.strip()}%"))
    if estimate_publish_time_from is not None:
        filters.append(ManhuaSeries.estimate_publish_time >= to_beijing_naive(estimate_publish_time_from))
    if estimate_publish_time_to is not None:
        filters.append(ManhuaSeries.estimate_publish_time <= to_beijing_naive(estimate_publish_time_to))
    if collected_at_from is not None:
        filters.append(ManhuaSeries.collected_at >= collected_at_from)
    if collected_at_to is not None:
        filters.append(ManhuaSeries.collected_at <= collected_at_to)
    if publish_status is not None:
        filters.append(ManhuaSeries.publish_status == publish_status)
    if listed_today is True:
        filters.append(ManhuaSeries.publish_time.startswith(beijing_today_prefix(now)))
    elif listed_today is False:
        filters.append(~ManhuaSeries.publish_time.startswith(beijing_today_prefix(now)))
    if episode_amount_min is not None:
        filters.append(ManhuaSeries.episode_amount >= episode_amount_min)
    if episode_amount_max is not None:
        filters.append(ManhuaSeries.episode_amount <= episode_amount_max)
    return filters


def list_statement(filters: list[ColumnElement[bool]]) -> Select[tuple[ManhuaSeries]]:
    stmt = select(ManhuaSeries)
    if filters:
        stmt = stmt.where(*filters)
    return stmt.order_by(ManhuaSeries.collected_at.desc(), ManhuaSeries.id.desc())
