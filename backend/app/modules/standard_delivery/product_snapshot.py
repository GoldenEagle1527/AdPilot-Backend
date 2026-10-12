"""产品快照的保存、列表，以及抄到标准模板。没有全域厂商同步。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_iso, beijing_now
from app.modules.standard_delivery.model import DeliveryProductSnapshot, DeliveryTemplate
from app.modules.standard_delivery.schema import ProductSnapshotQuery, ProductSnapshotWrite
from app.modules.standard_delivery.service import get_template, template_item


def _like(raw: str) -> str:
    """ILIKE 片段。% 和 _ 按字面量匹配。"""
    escaped = raw.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def snapshot_item(row: DeliveryProductSnapshot) -> dict[str, Any]:
    """把快照收成出参。"""
    return {
        "id": str(row.id),
        "name": row.name,
        "product_name": row.product_name,
        "product_image_id": row.product_image_id,
        "selling_points": list(row.selling_points or []),
        "call_to_action_buttons": list(row.call_to_action_buttons or []),
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def snapshot_filters(query: ProductSnapshotQuery) -> list[ColumnElement[bool]]:
    """未删除的快照。名称空白当没传。"""
    filters: list[ColumnElement[bool]] = [DeliveryProductSnapshot.is_deleted == 0]
    name = (query.name or "").strip()
    if name:
        filters.append(DeliveryProductSnapshot.name.ilike(_like(name), escape="\\"))
    return filters


async def list_snapshots(session: AsyncSession, query: ProductSnapshotQuery) -> dict[str, Any]:
    """分页列出产品快照。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    filters = snapshot_filters(query)
    total = int(
        (
            await session.execute(select(func.count()).select_from(DeliveryProductSnapshot).where(*filters))
        ).scalar_one()
    )
    rows = await session.scalars(
        select(DeliveryProductSnapshot)
        .where(*filters)
        .order_by(DeliveryProductSnapshot.id.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    return page_data([snapshot_item(row) for row in rows.all()], total, params)


async def create_snapshot(session: AsyncSession, body: ProductSnapshotWrite) -> dict[str, Any]:
    """新增一条产品快照。同名未删除的拒绝。"""
    taken = await session.scalar(
        select(DeliveryProductSnapshot.id)
        .where(DeliveryProductSnapshot.name == body.name, DeliveryProductSnapshot.is_deleted == 0)
        .limit(1)
    )
    if taken is not None:
        raise ApiError(409, "产品快照名称已存在")
    row = DeliveryProductSnapshot(
        name=body.name,
        product_name=body.product_name,
        product_image_id=body.product_image_id,
        selling_points=list(body.selling_points),
        call_to_action_buttons=list(body.call_to_action_buttons),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return snapshot_item(row)


async def copy_snapshot_onto_template(
    session: AsyncSession, template_id: int, snapshot_id: int, allowed: set[str]
) -> dict[str, Any]:
    """把快照的名称、主图、卖点、行动号召抄到标准模板。其它列不动。"""
    found = await get_template(session, template_id, allowed)
    snapshot = await session.scalar(
        select(DeliveryProductSnapshot).where(
            DeliveryProductSnapshot.id == snapshot_id,
            DeliveryProductSnapshot.is_deleted == 0,
        )
    )
    if snapshot is None:
        raise ApiError(404, "产品快照不存在")
    template = await session.get(DeliveryTemplate, template_id)
    if template is None:
        raise ApiError(404, "模板不存在")
    template.product_name = snapshot.product_name
    template.product_image_id = snapshot.product_image_id
    template.selling_points = list(snapshot.selling_points or [])
    template.call_to_action_buttons = list(snapshot.call_to_action_buttons or [])
    template.updated_date = beijing_now()
    await session.commit()
    await session.refresh(template)
    return template_item(template, found["subject_name"])
