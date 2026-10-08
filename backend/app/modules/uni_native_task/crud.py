"""端原生投放任务的表查询。关联行在保存时整表替换。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, delete, exists, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.account.model import AdvertiserAccount, DouyinAccount
from app.modules.material.model import ManhuaSeries
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo, MaterialVideoPitcher
from app.modules.standard_delivery.model import DeliveryTemplate
from app.modules.uni_native_task.model import (
    UniNativeTask,
    UniNativeTaskAccount,
    UniNativeTaskBatchTitle,
    UniNativeTaskLink,
    UniNativeTaskTitle,
    UniNativeTaskVideo,
)

_TABLES_SQL = text(
    "SELECT to_regclass('public.manhua_series'), "
    "to_regclass('public.material_videos'), "
    "to_regclass('public.material_titles')"
)
_TABLE_NAMES = ("manhua_series", "material_videos", "material_titles")

TaskHead = tuple[UniNativeTask, DeliveryTemplate, str]


class SeriesBrief:
    """短剧只取主键和剧名，避免把尚未迁到本库的列选出来。"""

    def __init__(self, series_id: int, book_name: str) -> None:
        self.id = series_id
        self.book_name = book_name


def present_names(row: Any) -> set[str]:
    """把 to_regclass 的三列收成存在的表名。空值表示这张表不在库里。"""
    return {name for name, value in zip(_TABLE_NAMES, row, strict=True) if value is not None}


async def present_tables(session: AsyncSession) -> set[str]:
    """短剧、视频、标题三张表里，当前库实际有哪些。"""
    row = (await session.execute(_TABLES_SQL)).one()
    return present_names(row)


def series_stmt(series_id: int) -> Select[tuple[int, str]]:
    """未删除短剧的主键和剧名。"""
    return select(ManhuaSeries.id, ManhuaSeries.book_name).where(
        ManhuaSeries.id == series_id, ManhuaSeries.is_deleted == 0
    )


async def get_series(session: AsyncSession, series_id: int) -> SeriesBrief | None:
    """取一条未删除短剧。调用方须先确认 manhua_series 存在。"""
    row = (await session.execute(series_stmt(series_id))).one_or_none()
    if row is None:
        return None
    return SeriesBrief(int(row[0]), str(row[1]))


def owned_advertisers_stmt(advertiser_ids: list[int], user_id: int) -> Select[tuple[AdvertiserAccount]]:
    """当前投手名下、仍然有效的广告主。advertiser_ids 是巨量广告主 id。"""
    return select(AdvertiserAccount).where(
        AdvertiserAccount.advertiser_id.in_(advertiser_ids),
        AdvertiserAccount.is_deleted == 0,
        AdvertiserAccount.pitcher_user_id == user_id,
        AdvertiserAccount.sync_status == "active",
    )


async def owned_advertisers(
    session: AsyncSession, advertiser_ids: list[int], user_id: int
) -> list[AdvertiserAccount]:
    """当前投手名下的有效广告主。"""
    result = await session.execute(owned_advertisers_stmt(advertiser_ids, user_id))
    return list(result.scalars().all())


def _pitched_to(user_id: int) -> ColumnElement[bool]:
    """素材的投手归属里有这个人。"""
    return exists(
        select(MaterialVideoPitcher.id).where(
            MaterialVideoPitcher.video_id == MaterialVideo.id,
            MaterialVideoPitcher.user_id == user_id,
            MaterialVideoPitcher.is_deleted == 0,
        )
    )


def pitcher_videos_stmt(video_ids: list[int], series_id: int, user_id: int) -> Select[tuple[MaterialVideo]]:
    """这部剧里、上传者或投手归属是当前用户的未删除视频。"""
    return select(MaterialVideo).where(
        MaterialVideo.id.in_(video_ids),
        MaterialVideo.series_id == series_id,
        MaterialVideo.is_deleted == 0,
        or_(MaterialVideo.uploader_id == user_id, _pitched_to(user_id)),
    )


async def pitcher_videos(
    session: AsyncSession, video_ids: list[int], series_id: int, user_id: int
) -> list[MaterialVideo]:
    """这部剧里归当前投手的视频。调用方须先确认 material_videos 存在。"""
    result = await session.execute(pitcher_videos_stmt(video_ids, series_id, user_id))
    return list(result.scalars().all())


def own_titles_stmt(title_ids: list[int], user_id: int) -> Select[tuple[MaterialTitle]]:
    """当前用户自己上传、未删除的标题。"""
    return select(MaterialTitle).where(
        MaterialTitle.id.in_(title_ids),
        MaterialTitle.uploader_id == user_id,
        MaterialTitle.is_deleted == 0,
    )


async def own_titles(session: AsyncSession, title_ids: list[int], user_id: int) -> list[MaterialTitle]:
    """当前用户自己的标题。调用方须先确认 material_titles 存在。"""
    result = await session.execute(own_titles_stmt(title_ids, user_id))
    return list(result.scalars().all())


def _joined(series_present: bool):
    """任务连带模板。短剧表在库里时才连接剧名。"""
    book_name = ManhuaSeries.book_name if series_present else literal("").label("book_name")
    stmt = select(UniNativeTask, DeliveryTemplate, book_name).join(
        DeliveryTemplate, DeliveryTemplate.id == UniNativeTask.template_id
    )
    if series_present:
        stmt = stmt.join(ManhuaSeries, ManhuaSeries.id == UniNativeTask.series_id)
    return stmt


def _as_head(row: Any) -> TaskHead:
    """第三列是剧名。没有短剧表时它是空串。"""
    task, template, book_name = row
    return task, template, str(book_name or "")


async def page_tasks(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    series_present: bool,
    offset: int,
    limit: int,
) -> tuple[list[TaskHead], int]:
    """按创建时间倒序分页当前投手的任务。"""
    joined = _joined(series_present).where(*filters)
    total = int(
        (await session.execute(select(func.count()).select_from(joined.subquery()))).scalar_one()
    )
    result = await session.execute(
        joined.order_by(UniNativeTask.created_date.desc(), UniNativeTask.id.desc()).offset(offset).limit(limit)
    )
    return [_as_head(item) for item in result.all()], total


async def get_task_row(
    session: AsyncSession, task_id: int, user_id: int, *, series_present: bool
) -> TaskHead | None:
    """取当前投手自己的一条未删除任务。"""
    result = await session.execute(
        _joined(series_present).where(
            UniNativeTask.id == task_id,
            UniNativeTask.pitcher_user_id == user_id,
            UniNativeTask.is_deleted == 0,
        )
    )
    found = result.one_or_none()
    return None if found is None else _as_head(found)


async def accounts_by_tasks(
    session: AsyncSession, task_ids: list[int]
) -> dict[int, list[tuple[DouyinAccount, AdvertiserAccount]]]:
    """按任务分组的抖音号和账户，保持保存时的顺序。"""
    grouped: dict[int, list[tuple[DouyinAccount, AdvertiserAccount]]] = {item: [] for item in task_ids}
    if not task_ids:
        return grouped
    result = await session.execute(
        select(UniNativeTaskAccount, DouyinAccount, AdvertiserAccount)
        .join(DouyinAccount, DouyinAccount.id == UniNativeTaskAccount.douyin_account_id)
        .join(AdvertiserAccount, AdvertiserAccount.id == UniNativeTaskAccount.advertiser_account_id)
        .where(UniNativeTaskAccount.task_id.in_(task_ids))
        .order_by(UniNativeTaskAccount.sort_order, UniNativeTaskAccount.id)
    )
    for account, douyin, advertiser in result.all():
        grouped.setdefault(account.task_id, []).append((douyin, advertiser))
    return grouped


async def links_by_tasks(session: AsyncSession, task_ids: list[int]) -> dict[int, list[UniNativeTaskLink]]:
    """按任务分组的推广链文本。"""
    grouped: dict[int, list[UniNativeTaskLink]] = {item: [] for item in task_ids}
    if not task_ids:
        return grouped
    result = await session.execute(
        select(UniNativeTaskLink)
        .where(UniNativeTaskLink.task_id.in_(task_ids))
        .order_by(UniNativeTaskLink.sort_order, UniNativeTaskLink.id)
    )
    for link in result.scalars().all():
        grouped.setdefault(link.task_id, []).append(link)
    return grouped


async def videos_by_tasks(session: AsyncSession, task_ids: list[int]) -> dict[int, list[MaterialVideo]]:
    """按任务分组的视频。调用方须先确认 material_videos 存在。"""
    grouped: dict[int, list[MaterialVideo]] = {item: [] for item in task_ids}
    if not task_ids:
        return grouped
    result = await session.execute(
        select(UniNativeTaskVideo.task_id, MaterialVideo)
        .join(MaterialVideo, MaterialVideo.id == UniNativeTaskVideo.material_video_id)
        .where(UniNativeTaskVideo.task_id.in_(task_ids))
        .order_by(UniNativeTaskVideo.sort_order, UniNativeTaskVideo.id)
    )
    for task_id, video in result.all():
        grouped.setdefault(task_id, []).append(video)
    return grouped


async def titles_by_tasks(session: AsyncSession, task_ids: list[int]) -> dict[int, list[MaterialTitle]]:
    """按任务分组的标题库标题。调用方须先确认 material_titles 存在。"""
    grouped: dict[int, list[MaterialTitle]] = {item: [] for item in task_ids}
    if not task_ids:
        return grouped
    result = await session.execute(
        select(UniNativeTaskTitle.task_id, MaterialTitle)
        .join(MaterialTitle, MaterialTitle.id == UniNativeTaskTitle.material_title_id)
        .where(UniNativeTaskTitle.task_id.in_(task_ids))
        .order_by(UniNativeTaskTitle.sort_order, UniNativeTaskTitle.id)
    )
    for task_id, title in result.all():
        grouped.setdefault(task_id, []).append(title)
    return grouped


async def batch_titles_by_tasks(session: AsyncSession, task_ids: list[int]) -> dict[int, list[str]]:
    """按任务分组的临时标题文本。"""
    grouped: dict[int, list[str]] = {item: [] for item in task_ids}
    if not task_ids:
        return grouped
    result = await session.execute(
        select(UniNativeTaskBatchTitle)
        .where(UniNativeTaskBatchTitle.task_id.in_(task_ids))
        .order_by(UniNativeTaskBatchTitle.sort_order, UniNativeTaskBatchTitle.id)
    )
    for row in result.scalars().all():
        grouped.setdefault(row.task_id, []).append(row.title)
    return grouped


async def replace_children(
    session: AsyncSession,
    task_id: int,
    pairs: list[tuple[DouyinAccount, AdvertiserAccount]],
    links: list[tuple[str, str]],
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
    batch_titles: list[str],
) -> None:
    """用这次提交换掉账户、推广链、视频、标题库引用和临时标题。不写标题库。"""
    await session.execute(delete(UniNativeTaskAccount).where(UniNativeTaskAccount.task_id == task_id))
    await session.execute(delete(UniNativeTaskLink).where(UniNativeTaskLink.task_id == task_id))
    await session.execute(delete(UniNativeTaskVideo).where(UniNativeTaskVideo.task_id == task_id))
    await session.execute(delete(UniNativeTaskTitle).where(UniNativeTaskTitle.task_id == task_id))
    await session.execute(delete(UniNativeTaskBatchTitle).where(UniNativeTaskBatchTitle.task_id == task_id))
    for index, (douyin, advertiser) in enumerate(pairs):
        session.add(
            UniNativeTaskAccount(
                task_id=task_id,
                douyin_account_id=douyin.id,
                advertiser_account_id=advertiser.id,
                sort_order=index,
            )
        )
    for index, (charge_mode, link_text) in enumerate(links):
        session.add(
            UniNativeTaskLink(
                task_id=task_id, charge_mode=charge_mode, link_text=link_text, sort_order=index
            )
        )
    for index, video in enumerate(videos):
        session.add(UniNativeTaskVideo(task_id=task_id, material_video_id=video.id, sort_order=index))
    for index, title in enumerate(titles):
        session.add(UniNativeTaskTitle(task_id=task_id, material_title_id=title.id, sort_order=index))
    for index, title in enumerate(batch_titles):
        session.add(UniNativeTaskBatchTitle(task_id=task_id, title=title, sort_order=index))
