"""视频素材业务逻辑。素材名称后缀和素材标签都在这里按当日日期拼好再落库。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.times import beijing_iso, beijing_now
from app.modules.material import book_names_by_ids
from app.modules.material_video.model import MaterialVideo
from app.modules.material_video.schema import VideoCreate
from app.modules.system_admin import nicknames_by_ids


def dated_name(name: str, now: datetime) -> str:
    """素材名称拼当日日期后缀，如 甲 → 甲_20260923。"""
    return f"{name}_{now:%Y%m%d}"


def dated_tag(book_name: str, now: datetime) -> str:
    """素材标签 = 短剧名称 + 当前月日，如 甲剧0923。"""
    return f"{book_name}{now:%m%d}"


def to_item(row: MaterialVideo, book_name: str, nicknames: dict[int, str]) -> dict[str, Any]:
    """把视频素材行收成出参项。投手按落库顺序出，昵称必须齐，缺就是调用方没先校验。"""
    return {
        "id": str(row.id),
        "name": row.name,
        "material_type": row.material_type,
        "file_urls": list(row.file_urls),
        "series_id": str(row.series_id),
        "book_name": book_name,
        "platform": row.platform,
        "tag": row.tag,
        "ownership": row.ownership,
        "pitchers": [
            {"id": str(pitcher_id), "nickname": nicknames[pitcher_id]}
            for pitcher_id in row.pitcher_ids
        ],
        "uploader_id": str(row.uploader_id),
        "uploader_nickname": nicknames[row.uploader_id],
        "created_at": beijing_iso(row.created_date),
    }


async def create_video(
    session: AsyncSession, body: VideoCreate, uploader_id: int
) -> dict[str, Any]:
    """新增一条视频素材：短剧、投手、上传者都得在，名称与标签按当日日期拼好，上传者取当前登录用户。"""
    book_name = (await book_names_by_ids(session, [body.series_id])).get(body.series_id)
    if book_name is None:
        raise ApiError(404, "短剧不存在")
    wanted = [*body.pitcher_ids, uploader_id]
    nicknames = await nicknames_by_ids(session, wanted)
    missing = [user_id for user_id in wanted if user_id not in nicknames]
    if missing:
        raise ApiError(404, f"用户不存在：{'、'.join(str(item) for item in missing)}")
    now = beijing_now()
    row = MaterialVideo(
        name=dated_name(body.name, now),
        material_type=body.material_type,
        file_urls=body.file_urls,
        series_id=body.series_id,
        platform=body.platform,
        tag=dated_tag(book_name, now),
        ownership=body.ownership,
        pitcher_ids=body.pitcher_ids,
        uploader_id=uploader_id,
    )
    session.add(row)
    await session.commit()
    return to_item(row, book_name, nicknames)
