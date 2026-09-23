"""素材标题表查询和写入。"""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.material_title.model import MaterialTitle


async def existing_titles(
    session: AsyncSession,
    category: str,
    titles: list[str],
    uploader_id: int,
    *,
    exclude_id: int | None = None,
) -> set[str]:
    """该用户同分类下未删除的重名标题，一次查完，供写入前排重。exclude_id 用于改标题时排除自己。"""
    if not titles:
        return set()
    filters = [
        MaterialTitle.uploader_id == uploader_id,
        MaterialTitle.category == category,
        MaterialTitle.title.in_(titles),
        MaterialTitle.is_deleted == 0,
    ]
    if exclude_id is not None:
        filters.append(MaterialTitle.id != exclude_id)
    result = await session.execute(select(MaterialTitle.title).where(*filters))
    return {row[0] for row in result.all()}


async def page_titles(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[MaterialTitle], int]:
    """按上传时间倒序分页标题。返回 (行, 总数)。"""
    total = int(
        (
            await session.execute(select(func.count()).select_from(MaterialTitle).where(*filters))
        ).scalar_one()
    )
    result = await session.execute(
        select(MaterialTitle)
        .where(*filters)
        .order_by(MaterialTitle.created_date.desc(), MaterialTitle.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def own_title(session: AsyncSession, title_id: int, uploader_id: int) -> MaterialTitle | None:
    """取该用户自己上传且未删除的一条标题。别人的一律当不存在。"""
    result = await session.execute(
        select(MaterialTitle).where(
            MaterialTitle.id == title_id,
            MaterialTitle.uploader_id == uploader_id,
            MaterialTitle.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()
