"""视频素材表查询。"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.material_video.model import MaterialVideo, MaterialVideoPitcher, MaterialVideoTag


async def page_videos(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[MaterialVideo], int]:
    """按上传时间倒序分页视频素材。返回 (行, 总数)。"""
    total = int(
        (
            await session.execute(select(func.count()).select_from(MaterialVideo).where(*filters))
        ).scalar_one()
    )
    result = await session.execute(
        select(MaterialVideo)
        .where(*filters)
        .order_by(MaterialVideo.created_date.desc(), MaterialVideo.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def pitcher_ids_by_videos(
    session: AsyncSession, video_ids: Iterable[int]
) -> dict[int, list[int]]:
    """一次取出这些素材未删除的投手，按关联行 id 顺序。没有投手的素材不出现。"""
    pks = {int(video_id) for video_id in video_ids}
    if not pks:
        return {}
    rows = await session.execute(
        select(MaterialVideoPitcher.video_id, MaterialVideoPitcher.user_id)
        .where(
            MaterialVideoPitcher.video_id.in_(pks),
            MaterialVideoPitcher.is_deleted == 0,
        )
        .order_by(MaterialVideoPitcher.id)
    )
    grouped: dict[int, list[int]] = {}
    for video_id, user_id in rows.all():
        grouped.setdefault(int(video_id), []).append(int(user_id))
    return grouped


async def ensure_tag(session: AsyncSession, name: str) -> MaterialVideoTag:
    """按文案取未删除标签，没有就插入。同一文案多条素材共用一行。"""
    found = (
        await session.execute(
            select(MaterialVideoTag).where(
                MaterialVideoTag.name == name,
                MaterialVideoTag.is_deleted == 0,
            )
        )
    ).scalars().all()
    if found:
        return found[0]
    # ponytail: 并发创建同一标签会撞唯一约束。要扛并发再改成 ON CONFLICT 后重查。
    row = MaterialVideoTag(name=name)
    session.add(row)
    await session.flush()
    return row


async def tag_names_by_ids(session: AsyncSession, tag_ids: Iterable[int]) -> dict[int, str]:
    """一次取出这些标签的文案。已删或不存在的 id 不出现。"""
    pks = {int(tag_id) for tag_id in tag_ids}
    if not pks:
        return {}
    rows = await session.execute(
        select(MaterialVideoTag.id, MaterialVideoTag.name).where(
            MaterialVideoTag.id.in_(pks),
            MaterialVideoTag.is_deleted == 0,
        )
    )
    return {int(tag_id): name for tag_id, name in rows.all()}


async def page_tags(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[MaterialVideoTag], int]:
    """按标签名分页。返回 (行, 总数)。"""
    total = int(
        (
            await session.execute(
                select(func.count()).select_from(MaterialVideoTag).where(*filters)
            )
        ).scalar_one()
    )
    result = await session.execute(
        select(MaterialVideoTag)
        .where(*filters)
        .order_by(MaterialVideoTag.name, MaterialVideoTag.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total
