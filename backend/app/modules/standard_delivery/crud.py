"""漫剧标准投放的表查询。关联行在保存时整表替换。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.account.model import AdvertiserAccount, DeliverySubject, DouyinAccount, ProductLibrary, ProductLibraryPitcher
from app.modules.material.model import ManhuaSeries
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.material_video.schema import VideoQuery
from app.modules.material_video.service import video_filters
from app.modules.standard_delivery.model import (
    DeliveryAutoRule,
    DeliveryAutoRuleSeries,
    DeliveryTaskAccount,
    DeliveryTaskDraft,
    DeliveryTaskTitle,
    DeliveryTaskVideo,
    DeliveryTemplate,
)


class SeriesBrief:
    """短剧只取主键和剧名，避免把模型里尚未迁到本库的列选出来。"""

    def __init__(self, series_id: int, book_name: str) -> None:
        self.id = series_id
        self.book_name = book_name


TemplateRow = tuple[DeliveryTemplate, DeliverySubject]
DraftRow = tuple[DeliveryTaskDraft, DeliveryTemplate, DeliverySubject, DouyinAccount, SeriesBrief, ProductLibrary]
RuleRow = tuple[DeliveryAutoRule, DeliveryTemplate]


def standard_douyin_stmt(douyin_id: int) -> Select[tuple[DouyinAccount]]:
    """已启用的标准号。不读 douyin_pitcher，标准号全员共用。"""
    return select(DouyinAccount).where(
        DouyinAccount.id == douyin_id,
        DouyinAccount.is_deleted == 0,
        DouyinAccount.delivery_mode == "standard",
        DouyinAccount.enabled.is_(True),
    )


def owned_advertisers_stmt(advertiser_ids: list[int], user_id: int) -> Select[tuple[AdvertiserAccount]]:
    """当前投手名下、仍然有效的广告主。advertiser_ids 是巨量广告主 id。"""
    return select(AdvertiserAccount).where(
        AdvertiserAccount.advertiser_id.in_(advertiser_ids),
        AdvertiserAccount.is_deleted == 0,
        AdvertiserAccount.pitcher_user_id == user_id,
        AdvertiserAccount.sync_status == "active",
    )


def visible_videos_stmt(video_ids: list[int], series_id: int, user_id: int) -> Select[tuple[MaterialVideo]]:
    """这部剧里、当前用户能看见的视频。"""
    return select(MaterialVideo).where(
        MaterialVideo.id.in_(video_ids),
        *video_filters(VideoQuery(series_id=series_id), user_id),
    )


def own_titles_stmt(title_ids: list[int], user_id: int) -> Select[tuple[MaterialTitle]]:
    """当前用户自己上传、未删除的标题。"""
    return select(MaterialTitle).where(
        MaterialTitle.id.in_(title_ids),
        MaterialTitle.uploader_id == user_id,
        MaterialTitle.is_deleted == 0,
    )


async def get_subject(session: AsyncSession, subject_id: int) -> DeliverySubject | None:
    """取一条未删除的投放主体。"""
    result = await session.execute(
        select(DeliverySubject).where(DeliverySubject.id == subject_id, DeliverySubject.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def get_template_row(session: AsyncSession, template_id: int) -> TemplateRow | None:
    """取未删除的模板，连带主体。"""
    result = await session.execute(
        select(DeliveryTemplate, DeliverySubject)
        .join(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
        .where(DeliveryTemplate.id == template_id, DeliveryTemplate.is_deleted == 0)
    )
    return result.one_or_none()


async def template_name_taken(
    session: AsyncSession, charge_mode: str, name: str, exclude_id: int | None
) -> bool:
    """同一收费模式下未删除的模板是否已有这个名字。"""
    stmt = select(DeliveryTemplate.id).where(
        DeliveryTemplate.charge_mode == charge_mode,
        DeliveryTemplate.name == name,
        DeliveryTemplate.is_deleted == 0,
    )
    if exclude_id is not None:
        stmt = stmt.where(DeliveryTemplate.id != exclude_id)
    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none() is not None


async def template_in_use(session: AsyncSession, template_id: int) -> bool:
    """未删除的草稿或规则还指着这个模板。"""
    draft = await session.execute(
        select(DeliveryTaskDraft.id)
        .where(DeliveryTaskDraft.template_id == template_id, DeliveryTaskDraft.is_deleted == 0)
        .limit(1)
    )
    if draft.scalar_one_or_none() is not None:
        return True
    rule = await session.execute(
        select(DeliveryAutoRule.id)
        .where(DeliveryAutoRule.template_id == template_id, DeliveryAutoRule.is_deleted == 0)
        .limit(1)
    )
    return rule.scalar_one_or_none() is not None


def _template_select():
    """模板列表和计数共用的连接。"""
    return select(DeliveryTemplate, DeliverySubject).join(
        DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id
    )


async def page_templates(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[TemplateRow], int]:
    """按创建时间倒序分页模板。"""
    total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(DeliveryTemplate)
                .join(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
                .where(*filters)
            )
        ).scalar_one()
    )
    result = await session.execute(
        _template_select()
        .where(*filters)
        .order_by(DeliveryTemplate.created_date.desc(), DeliveryTemplate.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.all()), total


async def get_standard_douyin(session: AsyncSession, douyin_id: int) -> DouyinAccount | None:
    """取已启用的标准号。"""
    result = await session.execute(standard_douyin_stmt(douyin_id))
    return result.scalar_one_or_none()


def _series_brief(row: Any) -> SeriesBrief:
    """行上只要有 id 和 book_name。"""
    return SeriesBrief(int(row.id), str(row.book_name))


async def get_series(session: AsyncSession, series_id: int) -> SeriesBrief | None:
    """取一条未删除短剧的主键和剧名。"""
    result = await session.execute(
        select(ManhuaSeries.id, ManhuaSeries.book_name).where(
            ManhuaSeries.id == series_id, ManhuaSeries.is_deleted == 0
        )
    )
    row = result.one_or_none()
    return None if row is None else _series_brief(row)


async def get_series_by_ids(session: AsyncSession, series_ids: list[int]) -> list[SeriesBrief]:
    """取未删除短剧的主键和剧名。顺序由调用方按请求重排。"""
    result = await session.execute(
        select(ManhuaSeries.id, ManhuaSeries.book_name).where(
            ManhuaSeries.id.in_(series_ids), ManhuaSeries.is_deleted == 0
        )
    )
    return [_series_brief(row) for row in result.all()]


async def owned_advertisers(
    session: AsyncSession, advertiser_ids: list[int], user_id: int
) -> list[AdvertiserAccount]:
    """当前投手名下的有效广告主。"""
    result = await session.execute(owned_advertisers_stmt(advertiser_ids, user_id))
    return list(result.scalars().all())


async def visible_videos(
    session: AsyncSession, video_ids: list[int], series_id: int, user_id: int
) -> list[MaterialVideo]:
    """这部剧里当前用户能看见的视频。"""
    result = await session.execute(visible_videos_stmt(video_ids, series_id, user_id))
    return list(result.scalars().all())


async def own_titles(session: AsyncSession, title_ids: list[int], user_id: int) -> list[MaterialTitle]:
    """当前用户自己的标题。"""
    result = await session.execute(own_titles_stmt(title_ids, user_id))
    return list(result.scalars().all())


async def get_library_by_no(session: AsyncSession, library_no: int) -> ProductLibrary | None:
    """按巨量商品库 id 取未删除的库。"""
    result = await session.execute(
        select(ProductLibrary).where(ProductLibrary.library_no == library_no, ProductLibrary.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def library_assigned(session: AsyncSession, library_id: int, user_id: int) -> bool:
    """标准库是否分给了这个投手。"""
    result = await session.execute(
        select(ProductLibraryPitcher.id)
        .where(
            ProductLibraryPitcher.product_library_id == library_id,
            ProductLibraryPitcher.user_id == user_id,
            ProductLibraryPitcher.is_deleted == 0,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


def _draft_joined():
    """草稿列表连带模板、主体、抖音号、短剧名、商品库。短剧只选主键和剧名。"""
    return (
        select(
            DeliveryTaskDraft,
            DeliveryTemplate,
            DeliverySubject,
            DouyinAccount,
            ManhuaSeries.id,
            ManhuaSeries.book_name,
            ProductLibrary,
        )
        .join(DeliveryTemplate, DeliveryTemplate.id == DeliveryTaskDraft.template_id)
        .join(DeliverySubject, DeliverySubject.id == DeliveryTemplate.subject_id)
        .join(DouyinAccount, DouyinAccount.id == DeliveryTaskDraft.douyin_account_id)
        .join(ManhuaSeries, ManhuaSeries.id == DeliveryTaskDraft.series_id)
        .join(ProductLibrary, ProductLibrary.id == DeliveryTaskDraft.product_library_id)
    )


def _as_draft_row(row: Any) -> DraftRow:
    """把短剧两列收成剧名对象，列表和详情都不读短剧表的其它列。"""
    draft, template, subject, douyin, series_id, book_name, library = row
    return draft, template, subject, douyin, SeriesBrief(int(series_id), str(book_name)), library


async def page_drafts(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[DraftRow], int]:
    """按创建时间倒序分页草稿。"""
    total = int(
        (
            await session.execute(select(func.count()).select_from(_draft_joined().where(*filters).subquery()))
        ).scalar_one()
    )
    result = await session.execute(
        _draft_joined()
        .where(*filters)
        .order_by(DeliveryTaskDraft.created_date.desc(), DeliveryTaskDraft.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_as_draft_row(item) for item in result.all()], total


async def get_draft_row(session: AsyncSession, draft_id: int, user_id: int) -> DraftRow | None:
    """取当前投手自己的一条未删除草稿。"""
    result = await session.execute(
        _draft_joined().where(
            DeliveryTaskDraft.id == draft_id,
            DeliveryTaskDraft.pitcher_user_id == user_id,
            DeliveryTaskDraft.is_deleted == 0,
        )
    )
    found = result.one_or_none()
    return None if found is None else _as_draft_row(found)


async def accounts_by_drafts(
    session: AsyncSession, draft_ids: list[int]
) -> dict[int, list[AdvertiserAccount]]:
    """按草稿分组的账户，保持保存时的顺序。"""
    grouped: dict[int, list[AdvertiserAccount]] = {item: [] for item in draft_ids}
    if not draft_ids:
        return grouped
    result = await session.execute(
        select(DeliveryTaskAccount.task_id, AdvertiserAccount)
        .join(AdvertiserAccount, AdvertiserAccount.id == DeliveryTaskAccount.advertiser_account_id)
        .where(DeliveryTaskAccount.task_id.in_(draft_ids))
        .order_by(DeliveryTaskAccount.sort_order, DeliveryTaskAccount.id)
    )
    for task_id, account in result.all():
        grouped.setdefault(task_id, []).append(account)
    return grouped


async def videos_by_drafts(session: AsyncSession, draft_ids: list[int]) -> dict[int, list[MaterialVideo]]:
    """按草稿分组的视频，保持保存时的顺序。"""
    grouped: dict[int, list[MaterialVideo]] = {item: [] for item in draft_ids}
    if not draft_ids:
        return grouped
    result = await session.execute(
        select(DeliveryTaskVideo.task_id, MaterialVideo)
        .join(MaterialVideo, MaterialVideo.id == DeliveryTaskVideo.material_video_id)
        .where(DeliveryTaskVideo.task_id.in_(draft_ids))
        .order_by(DeliveryTaskVideo.sort_order, DeliveryTaskVideo.id)
    )
    for task_id, video in result.all():
        grouped.setdefault(task_id, []).append(video)
    return grouped


async def titles_by_drafts(session: AsyncSession, draft_ids: list[int]) -> dict[int, list[MaterialTitle]]:
    """按草稿分组的标题，保持保存时的顺序。"""
    grouped: dict[int, list[MaterialTitle]] = {item: [] for item in draft_ids}
    if not draft_ids:
        return grouped
    result = await session.execute(
        select(DeliveryTaskTitle.task_id, MaterialTitle)
        .join(MaterialTitle, MaterialTitle.id == DeliveryTaskTitle.material_title_id)
        .where(DeliveryTaskTitle.task_id.in_(draft_ids))
        .order_by(DeliveryTaskTitle.sort_order, DeliveryTaskTitle.id)
    )
    for task_id, title in result.all():
        grouped.setdefault(task_id, []).append(title)
    return grouped


async def replace_task_links(
    session: AsyncSession,
    task_id: int,
    accounts: list[AdvertiserAccount],
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
) -> None:
    """用这次提交的账户、视频、标题换掉原来的关联行。"""
    await session.execute(delete(DeliveryTaskAccount).where(DeliveryTaskAccount.task_id == task_id))
    await session.execute(delete(DeliveryTaskVideo).where(DeliveryTaskVideo.task_id == task_id))
    await session.execute(delete(DeliveryTaskTitle).where(DeliveryTaskTitle.task_id == task_id))
    for index, account in enumerate(accounts):
        session.add(
            DeliveryTaskAccount(task_id=task_id, advertiser_account_id=account.id, sort_order=index)
        )
    for index, video in enumerate(videos):
        session.add(DeliveryTaskVideo(task_id=task_id, material_video_id=video.id, sort_order=index))
    for index, title in enumerate(titles):
        session.add(DeliveryTaskTitle(task_id=task_id, material_title_id=title.id, sort_order=index))


def _rule_joined():
    """规则列表连带模板。"""
    return select(DeliveryAutoRule, DeliveryTemplate).join(
        DeliveryTemplate, DeliveryTemplate.id == DeliveryAutoRule.template_id
    )


async def page_rules(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[RuleRow], int]:
    """按创建时间倒序分页规则。"""
    total = int(
        (
            await session.execute(select(func.count()).select_from(_rule_joined().where(*filters).subquery()))
        ).scalar_one()
    )
    result = await session.execute(
        _rule_joined()
        .where(*filters)
        .order_by(DeliveryAutoRule.created_date.desc(), DeliveryAutoRule.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.all()), total


async def get_rule_row(session: AsyncSession, rule_id: int, user_id: int) -> RuleRow | None:
    """取当前投手自己的一条未删除规则。"""
    result = await session.execute(
        _rule_joined().where(
            DeliveryAutoRule.id == rule_id,
            DeliveryAutoRule.pitcher_user_id == user_id,
            DeliveryAutoRule.is_deleted == 0,
        )
    )
    return result.one_or_none()


async def rule_name_taken(
    session: AsyncSession, user_id: int, charge_mode: str, name: str, exclude_id: int | None
) -> bool:
    """同一投手、同一收费模式下未删除的规则是否已有这个名字。"""
    stmt = select(DeliveryAutoRule.id).where(
        DeliveryAutoRule.pitcher_user_id == user_id,
        DeliveryAutoRule.charge_mode == charge_mode,
        DeliveryAutoRule.name == name,
        DeliveryAutoRule.is_deleted == 0,
    )
    if exclude_id is not None:
        stmt = stmt.where(DeliveryAutoRule.id != exclude_id)
    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none() is not None


async def series_by_rules(session: AsyncSession, rule_ids: list[int]) -> dict[int, list[SeriesBrief]]:
    """按规则分组的短剧名，保持保存时的顺序。只读主键和剧名。"""
    grouped: dict[int, list[SeriesBrief]] = {item: [] for item in rule_ids}
    if not rule_ids:
        return grouped
    result = await session.execute(
        select(DeliveryAutoRuleSeries.rule_id, ManhuaSeries.id, ManhuaSeries.book_name)
        .join(ManhuaSeries, ManhuaSeries.id == DeliveryAutoRuleSeries.series_id)
        .where(DeliveryAutoRuleSeries.rule_id.in_(rule_ids))
        .order_by(DeliveryAutoRuleSeries.sort_order, DeliveryAutoRuleSeries.id)
    )
    for rule_id, series_id, book_name in result.all():
        grouped.setdefault(int(rule_id), []).append(SeriesBrief(int(series_id), str(book_name)))
    return grouped


def rule_has_series(series_id: int) -> ColumnElement[bool]:
    """规则选中了这部短剧。"""
    return exists(
        select(DeliveryAutoRuleSeries.id).where(
            DeliveryAutoRuleSeries.rule_id == DeliveryAutoRule.id,
            DeliveryAutoRuleSeries.series_id == series_id,
        )
    )


async def replace_rule_series(session: AsyncSession, rule_id: int, series_rows: list[SeriesBrief]) -> None:
    """用这次提交的短剧换掉原来的关联行。"""
    await session.execute(delete(DeliveryAutoRuleSeries).where(DeliveryAutoRuleSeries.rule_id == rule_id))
    for index, series in enumerate(series_rows):
        session.add(DeliveryAutoRuleSeries(rule_id=rule_id, series_id=series.id, sort_order=index))
