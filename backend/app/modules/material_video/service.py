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
    ensure_tag,
    page_tags,
    page_videos,
    pitcher_ids_by_videos,
    tag_names_by_ids,
)
from app.modules.material_video.model import (
    MaterialVideo,
    MaterialVideoPitcher,
    MaterialVideoTag,
    Ownership,
)
from app.modules.material_video.schema import TagQuery, VideoCreate, VideoQuery
from app.modules.system_admin import nicknames_by_ids


def dated_name(name: str, now: datetime) -> str:
    """素材名称拼当日日期后缀，如 甲 → 甲_20260923。"""
    return f"{name}_{now:%Y%m%d}"


def to_item(
    row: MaterialVideo,
    book_name: str,
    nicknames: dict[int, str],
    pitcher_ids: list[int],
    tag_name: str,
) -> dict[str, Any]:
    """把视频素材行收成出参项。投手按传入顺序出，昵称查不到给空串。"""
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
        "pitchers": [
            {"id": str(pitcher_id), "nickname": nicknames.get(pitcher_id, "")}
            for pitcher_id in pitcher_ids
        ],
        "uploader_id": str(row.uploader_id),
        "uploader_nickname": nicknames.get(row.uploader_id, ""),
        "created_at": beijing_iso(row.created_date),
    }


async def create_video(
    session: AsyncSession, body: VideoCreate, uploader_id: int
) -> dict[str, Any]:
    """新增一条视频素材：短剧和用户都得在，投手写入关联表，名称按当日日期拼好，标签用传入文案。"""
    book_name = (await book_names_by_ids(session, [body.series_id])).get(body.series_id)
    if book_name is None:
        raise ApiError(404, "短剧不存在")
    wanted = [*body.pitcher_ids, uploader_id]
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
            MaterialVideoPitcher(video_id=row.id, user_id=pitcher_id)
            for pitcher_id in body.pitcher_ids
        ]
    )
    await session.commit()
    return to_item(row, book_name, nicknames, body.pitcher_ids, tag.name)


def like_text(raw: str) -> str:
    """把用户输入收成 ILIKE 片段，% 和 _ 按字面量匹配。"""
    escaped = raw.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def assigned_to(user_id: int) -> ColumnElement[bool]:
    """这条素材的投手关联里有这个人，且关联行未删。"""
    return exists(
        select(MaterialVideoPitcher.id).where(
            MaterialVideoPitcher.video_id == MaterialVideo.id,
            MaterialVideoPitcher.user_id == user_id,
            MaterialVideoPitcher.is_deleted == 0,
        )
    )


def video_filters(query: VideoQuery, user_id: int) -> list[ColumnElement[bool]]:
    """拼列表条件：未删除，且公有、或自己创建、或私有并分配给自己。其余筛选项有值才加上。"""
    filters: list[ColumnElement[bool]] = [
        MaterialVideo.is_deleted == 0,
        or_(
            MaterialVideo.ownership == Ownership.PUBLIC,
            MaterialVideo.uploader_id == user_id,
            and_(MaterialVideo.ownership == Ownership.PRIVATE, assigned_to(user_id)),
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
        filters.append(assigned_to(query.pitcher_id))
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
    pitchers = await pitcher_ids_by_videos(session, video_ids)
    books = await book_names_by_ids(session, {row.series_id for row in rows})
    tags = await tag_names_by_ids(session, {row.tag_id for row in rows})
    user_ids = {row.uploader_id for row in rows}
    for ids in pitchers.values():
        user_ids.update(ids)
    nicknames = await nicknames_by_ids(session, user_ids)
    items = [
        to_item(
            row,
            books.get(row.series_id, ""),
            nicknames,
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
