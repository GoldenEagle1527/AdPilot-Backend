"""视频素材表查询和删除。"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.material_video.model import (
    MaterialVideo,
    MaterialVideoPitcher,
    MaterialVideoShare,
    MaterialVideoTag,
)


async def own_video(session: AsyncSession, video_id: int, uploader_id: int) -> MaterialVideo | None:
    """取该用户自己上传且未删除的一条视频。别人的一律当不存在。"""
    result = await session.execute(
        select(MaterialVideo).where(
            MaterialVideo.id == video_id,
            MaterialVideo.uploader_id == uploader_id,
            MaterialVideo.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()


async def live_video(session: AsyncSession, video_id: int) -> MaterialVideo | None:
    """取未删除的一条视频。"""
    result = await session.execute(
        select(MaterialVideo).where(MaterialVideo.id == video_id, MaterialVideo.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def active_share(
    session: AsyncSession, video_id: int, user_id: int
) -> MaterialVideoShare | None:
    """取这条素材上还没取消的一条共享。"""
    result = await session.execute(
        select(MaterialVideoShare).where(
            MaterialVideoShare.video_id == video_id,
            MaterialVideoShare.user_id == user_id,
            MaterialVideoShare.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()


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


async def share_user_ids_by_videos(
    session: AsyncSession, video_ids: Iterable[int]
) -> dict[int, list[int]]:
    """一次取出这些素材未取消的共享人，按共享行 id 顺序。没有共享的素材不出现。"""
    pks = {int(video_id) for video_id in video_ids}
    if not pks:
        return {}
    rows = await session.execute(
        select(MaterialVideoShare.video_id, MaterialVideoShare.user_id)
        .where(
            MaterialVideoShare.video_id.in_(pks),
            MaterialVideoShare.is_deleted == 0,
        )
        .order_by(MaterialVideoShare.id)
    )
    grouped: dict[int, list[int]] = {}
    for video_id, user_id in rows.all():
        grouped.setdefault(int(video_id), []).append(int(user_id))
    return grouped


async def pitcher_ids_by_videos(
    session: AsyncSession, video_ids: Iterable[int]
) -> dict[int, list[int]]:
    """一次取出这些素材未删除的投手，按归属行 id 顺序。同一投手只留第一次。"""
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
    seen: set[tuple[int, int]] = set()
    for video_id, user_id in rows.all():
        key = (int(video_id), int(user_id))
        if key in seen:
            continue
        seen.add(key)
        grouped.setdefault(key[0], []).append(key[1])
    return grouped


async def share_rows(session: AsyncSession, video_id: int) -> list[MaterialVideoShare]:
    """这条素材上的全部共享行，含已取消的。"""
    rows = await session.execute(
        select(MaterialVideoShare).where(MaterialVideoShare.video_id == video_id)
    )
    return list(rows.scalars().all())


async def pitcher_rows_by_operator(
    session: AsyncSession, video_id: int, operator_id: int
) -> list[MaterialVideoPitcher]:
    """这个人在这条素材上分过的投手行，含已取消的。"""
    rows = await session.execute(
        select(MaterialVideoPitcher).where(
            MaterialVideoPitcher.video_id == video_id,
            MaterialVideoPitcher.operator_id == operator_id,
        )
    )
    return list(rows.scalars().all())


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
