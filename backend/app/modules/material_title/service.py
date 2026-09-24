"""素材标题业务逻辑。标题只对上传者本人可见可改。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_iso
from app.modules.material_title.crud import existing_titles, own_title, own_titles, page_titles
from app.modules.material_title.model import MaterialTitle
from app.modules.material_title.schema import TitleBatchCreate, TitleIdsBody, TitleQuery, TitleUpdate
from app.modules.system_admin import nicknames_by_ids


def to_item(row: MaterialTitle, nickname: str) -> dict[str, Any]:
    """把标题行收成出参项。昵称查不到时给空串。"""
    return {
        "id": str(row.id),
        "title": row.title,
        "category": row.category,
        "uploader_id": str(row.uploader_id),
        "uploader_nickname": nickname,
        "created_at": beijing_iso(row.created_date),
    }


async def batch_create_titles(
    session: AsyncSession, body: TitleBatchCreate, uploader_id: int
) -> dict[str, Any]:
    """自己同分类下只要有一条标题已存在就整批拒绝，否则一次全插。返回新增条数。"""
    existing = await existing_titles(session, body.category, body.titles, uploader_id)
    if existing:
        names = "、".join(sorted(existing)[:5])
        raise ApiError(409, f"{len(existing)} 条标题已存在：{names}")
    session.add_all(
        [
            MaterialTitle(title=title, category=body.category, uploader_id=uploader_id)
            for title in body.titles
        ]
    )
    await session.commit()
    return {"created": len(body.titles)}


def title_filters(query: TitleQuery, uploader_id: int) -> list[ColumnElement[bool]]:
    """拼列表过滤：恒限本人且未删除；分类精确匹配，标题名模糊且转义 % 和 _。"""
    filters: list[ColumnElement[bool]] = [
        MaterialTitle.is_deleted == 0,
        MaterialTitle.uploader_id == uploader_id,
    ]
    if query.category is not None:
        filters.append(MaterialTitle.category == query.category)
    name = (query.title or "").strip()
    if name:
        escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(MaterialTitle.title.ilike(f"%{escaped}%", escape="\\"))
    return filters


async def list_titles(
    session: AsyncSession, query: TitleQuery, uploader_id: int
) -> dict[str, Any]:
    """分页列出当前用户自己上传、未删除的标题，按上传时间倒序。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    filters = title_filters(query, uploader_id)
    rows, total = await page_titles(session, filters, offset=params.offset, limit=params.page_size)
    nicknames = await nicknames_by_ids(session, {row.uploader_id for row in rows})
    items = [to_item(row, nicknames.get(row.uploader_id, "")) for row in rows]
    return page_data(items, total, params)


def absent_ids(wanted: list[int], found: Iterable[int]) -> list[int]:
    """按传入顺序找出没出现在结果里的 id。"""
    got = {int(item) for item in found}
    return [item for item in wanted if item not in got]


async def batch_delete_titles(
    session: AsyncSession, body: TitleIdsBody, uploader_id: int
) -> dict[str, Any]:
    """软删自己上传的标题，一条或多条。有一条不是自己的就整批不删。"""
    rows = await own_titles(session, body.title_ids, uploader_id)
    missing = absent_ids(body.title_ids, [row.id for row in rows])
    if missing:
        raise ApiError(404, f"标题不存在：{'、'.join(str(item) for item in missing)}")
    for row in rows:
        row.mark_deleted()
    await session.commit()
    return {"ids": [str(title_id) for title_id in body.title_ids], "deleted": True}


async def update_title(
    session: AsyncSession, title_id: int, body: TitleUpdate, uploader_id: int
) -> dict[str, Any]:
    """改自己上传标题的标题名和分类。别人的当不存在，改后同分类下重名则 409。"""
    row = await own_title(session, title_id, uploader_id)
    if row is None:
        raise ApiError(404, "标题不存在")
    clash = await existing_titles(
        session, body.category, [body.title], uploader_id, exclude_id=row.id
    )
    if clash:
        raise ApiError(409, "标题已存在")
    row.title = body.title
    row.category = body.category
    await session.commit()
    nicknames = await nicknames_by_ids(session, [row.uploader_id])
    return to_item(row, nicknames.get(row.uploader_id, ""))
