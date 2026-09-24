"""视频素材业务逻辑。素材名称后缀在这里按当日日期拼好再落库，标签名用前端传入的文案。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import String, and_, cast, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_iso, beijing_now
from app.modules.material import book_names_by_ids
from app.modules.material_video.crud import (
    active_share,
    ensure_tag,
    live_video,
    own_video,
    page_tags,
    page_videos,
    pitcher_ids_by_videos,
    pitcher_rows_by_operator,
    share_rows,
    share_user_ids_by_videos,
    tag_names_by_ids,
)
from app.modules.material_video.model import (
    MaterialVideo,
    MaterialVideoPitcher,
    MaterialVideoShare,
    MaterialVideoTag,
    Ownership,
)
from app.modules.material_video.schema import PitcherChange, ShareChange, TagQuery, VideoCreate, VideoQuery
from app.modules.system_admin import nicknames_by_ids


def dated_name(name: str, now: datetime) -> str:
    """素材名称拼当日日期后缀，如 甲 → 甲_20260923。"""
    return f"{name}_{now:%Y%m%d}"


def user_items(user_ids: list[int], nicknames: dict[int, str]) -> list[dict[str, str]]:
    """按传入顺序收成 id 和昵称。昵称查不到给空串。"""
    return [
        {"id": str(user_id), "nickname": nicknames.get(user_id, "")} for user_id in user_ids
    ]


def to_item(
    row: MaterialVideo,
    book_name: str,
    nicknames: dict[int, str],
    share_ids: list[int],
    pitcher_ids: list[int],
    tag_name: str,
) -> dict[str, Any]:
    """把视频素材行收成出参项。共享人和投手按传入顺序出。"""
    return {
        "id": str(row.id),
        "name": row.name,
        "material_type": row.material_type,
        "file_urls": list(row.file_urls),
        "series_id": str(row.series_id),
        "book_name": book_name,
        "platform": row.platform,
        "tag": tag_name,
        "ownership": row.ownership,
        "shares": user_items(share_ids, nicknames),
        "pitchers": user_items(pitcher_ids, nicknames),
        "uploader_id": str(row.uploader_id),
        "uploader_nickname": nicknames.get(row.uploader_id, ""),
        "created_at": beijing_iso(row.created_date),
    }


async def create_video(
    session: AsyncSession, body: VideoCreate, uploader_id: int
) -> dict[str, Any]:
    """新增一条视频素材：短剧和用户都得在，共享写入共享表，名称按当日日期拼好。"""
    book_name = (await book_names_by_ids(session, [body.series_id])).get(body.series_id)
    if book_name is None:
        raise ApiError(404, "短剧不存在")
    wanted = [*body.share_user_ids, uploader_id]
    nicknames = await nicknames_by_ids(session, wanted)
    missing = [user_id for user_id in wanted if user_id not in nicknames]
    if missing:
        raise ApiError(404, f"用户不存在：{'、'.join(str(item) for item in missing)}")
    now = beijing_now()
    tag = await ensure_tag(session, body.tag)
    row = MaterialVideo(
        name=dated_name(body.name, now),
        material_type=body.material_type,
        file_urls=body.file_urls,
        series_id=body.series_id,
        platform=body.platform,
        tag_id=tag.id,
        ownership=body.ownership,
        uploader_id=uploader_id,
    )
    session.add(row)
    await session.flush()
    session.add_all(
        [
            MaterialVideoShare(video_id=row.id, user_id=user_id)
            for user_id in body.share_user_ids
        ]
    )
    await session.commit()
    return to_item(row, book_name, nicknames, body.share_user_ids, [], tag.name)


def restore(row: MaterialVideoShare | MaterialVideoPitcher) -> None:
    """把软删行恢复成未删，避免同一对人再插入时撞唯一约束。"""
    row.is_deleted = 0
    row.deleted_at = None


async def operable_video(session: AsyncSession, video_id: int, operator_id: int) -> MaterialVideo:
    """上传者或仍在共享里的人才能操作。其他人按素材不存在。"""
    row = await live_video(session, video_id)
    if row is None or (
        row.uploader_id != operator_id and await active_share(session, video_id, operator_id) is None
    ):
        raise ApiError(404, "视频素材不存在")
    return row


def missing_users(wanted: list[int], nicknames: dict[int, str]) -> list[int]:
    """找出查不到昵称的用户 id，保持传入顺序。"""
    return [user_id for user_id in wanted if user_id not in nicknames]


def align_members(
    existing: dict[int, MaterialVideoShare | MaterialVideoPitcher],
    desired: list[int],
    make_row,
) -> tuple[list, list[int], list[int]]:
    """按完整名单对齐已有行。返回 (新插入的行, 新增 id, 取消 id)。"""
    wanted = set(desired)
    fresh = []
    added: list[int] = []
    for user_id in desired:
        row = existing.get(user_id)
        if row is None:
            fresh.append(make_row(user_id))
            added.append(user_id)
        elif row.is_deleted:
            restore(row)
            added.append(user_id)
    removed = [
        user_id
        for user_id, row in existing.items()
        if user_id not in wanted and not row.is_deleted
    ]
    for user_id in removed:
        existing[user_id].mark_deleted()
    return fresh, added, removed


async def change_shares(
    session: AsyncSession, video_id: int, body: ShareChange, operator_id: int
) -> dict[str, Any]:
    """按上传者提交的完整共享名单对齐。名单里没有的人取消共享，他分过的投手保留。"""
    if await own_video(session, video_id, operator_id) is None:
        raise ApiError(404, "视频素材不存在")
    existing = {row.user_id: row for row in await share_rows(session, video_id)}
    active = [user_id for user_id, row in existing.items() if not row.is_deleted]
    nicknames = await nicknames_by_ids(session, [*body.user_ids, *active])
    missing = missing_users(body.user_ids, nicknames)
    if missing:
        raise ApiError(404, f"用户不存在：{'、'.join(str(item) for item in missing)}")
    fresh, added, removed = align_members(
        existing,
        body.user_ids,
        lambda user_id: MaterialVideoShare(video_id=video_id, user_id=user_id),
    )
    session.add_all(fresh)
    await session.commit()
    return {
        "id": str(video_id),
        "added": user_items(added, nicknames),
        "removed": user_items(removed, nicknames),
    }


async def change_pitchers(
    session: AsyncSession, video_id: int, body: PitcherChange, operator_id: int
) -> dict[str, Any]:
    """按当前操作人提交的完整投手名单对齐。只动这个人分出去的行。"""
    await operable_video(session, video_id, operator_id)
    existing = {row.user_id: row for row in await pitcher_rows_by_operator(session, video_id, operator_id)}
    active = [user_id for user_id, row in existing.items() if not row.is_deleted]
    nicknames = await nicknames_by_ids(session, [*body.user_ids, *active])
    missing = missing_users(body.user_ids, nicknames)
    if missing:
        raise ApiError(404, f"用户不存在：{'、'.join(str(item) for item in missing)}")
    fresh, added, removed = align_members(
        existing,
        body.user_ids,
        lambda user_id: MaterialVideoPitcher(video_id=video_id, operator_id=operator_id, user_id=user_id),
    )
    session.add_all(fresh)
    await session.commit()
    return {
        "id": str(video_id),
        "added": user_items(added, nicknames),
        "removed": user_items(removed, nicknames),
    }


async def delete_video(session: AsyncSession, video_id: int, uploader_id: int) -> dict[str, Any]:
    """软删自己上传的视频素材。别人的或已删的当不存在。"""
    row = await own_video(session, video_id, uploader_id)
    if row is None:
        raise ApiError(404, "视频素材不存在")
    row.mark_deleted()
    await session.commit()
    return {"id": str(row.id), "deleted": True}


def like_text(raw: str) -> str:
    """把用户输入收成 ILIKE 片段，% 和 _ 按字面量匹配。"""
    escaped = raw.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def shared_with(user_id: int) -> ColumnElement[bool]:
    """这条素材的共享里有这个人，且共享行未删。"""
    return exists(
        select(MaterialVideoShare.id).where(
            MaterialVideoShare.video_id == MaterialVideo.id,
            MaterialVideoShare.user_id == user_id,
            MaterialVideoShare.is_deleted == 0,
        )
    )


def pitched_to(user_id: int) -> ColumnElement[bool]:
    """这条素材的投手归属里有这个人，且归属行未删。"""
    return exists(
        select(MaterialVideoPitcher.id).where(
            MaterialVideoPitcher.video_id == MaterialVideo.id,
            MaterialVideoPitcher.user_id == user_id,
            MaterialVideoPitcher.is_deleted == 0,
        )
    )


def video_filters(query: VideoQuery, user_id: int) -> list[ColumnElement[bool]]:
    """拼列表条件：未删除，且公有、自己创建、或私有并且自己是共享人或投手。"""
    filters: list[ColumnElement[bool]] = [
        MaterialVideo.is_deleted == 0,
        or_(
            MaterialVideo.ownership == Ownership.PUBLIC,
            MaterialVideo.uploader_id == user_id,
            and_(
                MaterialVideo.ownership == Ownership.PRIVATE,
                or_(shared_with(user_id), pitched_to(user_id)),
            ),
        ),
    ]
    if query.id is not None:
        filters.append(MaterialVideo.id == query.id)
    if query.series_id is not None:
        filters.append(MaterialVideo.series_id == query.series_id)
    if query.uploader_id is not None:
        filters.append(MaterialVideo.uploader_id == query.uploader_id)
    if query.ownership is not None:
        filters.append(MaterialVideo.ownership == query.ownership)
    if query.pitcher_id is not None:
        filters.append(pitched_to(query.pitcher_id))
    if query.tag_id is not None:
        filters.append(MaterialVideo.tag_id == query.tag_id)
    name = (query.name or "").strip()
    if name:
        filters.append(MaterialVideo.name.ilike(like_text(name), escape="\\"))
    file_name = (query.file_name or "").strip()
    if file_name:
        filters.append(cast(MaterialVideo.file_urls, String).ilike(like_text(file_name), escape="\\"))
    return filters


async def list_videos(session: AsyncSession, query: VideoQuery, user_id: int) -> dict[str, Any]:
    """分页列出当前用户能看见的视频素材，按上传时间倒序。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_videos(
        session, video_filters(query, user_id), offset=params.offset, limit=params.page_size
    )
    video_ids = [row.id for row in rows]
    shares = await share_user_ids_by_videos(session, video_ids)
    pitchers = await pitcher_ids_by_videos(session, video_ids)
    books = await book_names_by_ids(session, {row.series_id for row in rows})
    tags = await tag_names_by_ids(session, {row.tag_id for row in rows})
    user_ids = {row.uploader_id for row in rows}
    for ids in shares.values():
        user_ids.update(ids)
    for ids in pitchers.values():
        user_ids.update(ids)
    nicknames = await nicknames_by_ids(session, user_ids)
    items = [
        to_item(
            row,
            books.get(row.series_id, ""),
            nicknames,
            shares.get(row.id, []),
            pitchers.get(row.id, []),
            tags.get(row.tag_id, ""),
        )
        for row in rows
    ]
    return page_data(items, total, params)


def tag_filters(query: TagQuery, user_id: int) -> list[ColumnElement[bool]]:
    """只列出当前用户能看见的素材用过的未删标签。名称有值时模糊。"""
    visible_tag_ids = select(MaterialVideo.tag_id).where(*video_filters(VideoQuery(), user_id))
    filters: list[ColumnElement[bool]] = [
        MaterialVideoTag.is_deleted == 0,
        MaterialVideoTag.id.in_(visible_tag_ids),
    ]
    name = (query.name or "").strip()
    if name:
        filters.append(MaterialVideoTag.name.ilike(like_text(name), escape="\\"))
    return filters


async def list_tags(session: AsyncSession, query: TagQuery, user_id: int) -> dict[str, Any]:
    """分页列出视频标签，供下拉模糊选择。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_tags(
        session, tag_filters(query, user_id), offset=params.offset, limit=params.page_size
    )
    items = [{"id": str(row.id), "name": row.name} for row in rows]
    return page_data(items, total, params)
