"""端原生投放任务的本地保存。本文件不上传素材，也不调用巨量。

页面上的保存由控制器在落库后再走提交。机器人调用 create_task 时不要求抖音号已挂到模板。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import BEIJING, beijing_iso, beijing_now
from app.modules.account.model import AdvertiserAccount, DouyinAccount
from app.modules.material.model import ManhuaSeries
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.standard_delivery.model import DeliveryTemplate
from app.modules.system_admin.domain.scope import DataScope, owner_match
from app.modules.theater.lookup import enabled_series_links, link_charge_mode
from app.modules.uni_native_task.crud import (
    SeriesBrief,
    TaskHead,
    accounts_by_tasks,
    batch_titles_by_tasks,
    get_series,
    get_task_row,
    links_by_tasks,
    owned_advertisers,
    own_titles,
    page_tasks,
    pitcher_series_videos,
    pitcher_videos,
    present_tables,
    replace_children,
    titles_by_tasks,
    videos_by_tasks,
)
from app.modules.uni_native_task.model import (
    NativeTaskStatus,
    UniNativeTask,
    UniNativeTaskAccount,
    UniNativeTaskLink,
)
from app.modules.uni_native_task.schema import TaskQuery, TaskWrite
from app.modules.uni_template.crud import douyin_by_ids, get_uni_template_row, pitcher_owned_ids
from app.modules.uni_template.model import DeliveryTemplateDouyin

T = TypeVar("T")


def series_short_name(book_name: str) -> str:
    """短剧简称是剧名前两个字。不足两个字就用原名。"""
    return book_name[:2]


def _like(raw: str) -> str:
    """ILIKE 片段，% 和 _ 按字面量匹配。"""
    escaped = raw.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _money(value: Decimal) -> str:
    """金额保留两位小数。"""
    return format(value.quantize(Decimal("0.01")), "f")


def _roi(value: Decimal) -> str:
    """ROI 系数保留三位小数。"""
    return format(value.quantize(Decimal("0.001")), "f")


def _day_start(value: date) -> datetime:
    """北京时间当天 0 点。"""
    return datetime(value.year, value.month, value.day, tzinfo=BEIJING)


def _order(rows: list[T], wanted: list[int], key) -> list[T]:
    """按请求里的 id 顺序重排。缺一条就返回空列表，调用方再报错。"""
    found = {key(row): row for row in rows}
    if any(item not in found for item in wanted):
        return []
    return [found[item] for item in wanted]


def _account_dict(
    douyin: DouyinAccount, advertiser: AdvertiserAccount, ocean_project_id: int | None = None
) -> dict[str, Any]:
    """把一对抖音号和账户收成出参。巨量项目 id 先原样带上，再按任务状态决定是否露出。"""
    return {
        "douyin_account_id": str(douyin.id),
        "aweme_id": douyin.aweme_id,
        "douyin_name": douyin.name,
        "advertiser_account_id": str(advertiser.id),
        "advertiser_id": int(advertiser.advertiser_id),
        "name": advertiser.local_name or advertiser.name,
        "ocean_project_id": None if ocean_project_id is None else int(ocean_project_id),
    }


def _link_dict(charge_mode: str, link_text: str, recharge_template_name: str = "") -> dict[str, str]:
    """把一条推广链收成出参。档位名没有则为空串。"""
    return {
        "charge_mode": charge_mode,
        "link_text": link_text,
        "recharge_template_name": recharge_template_name,
    }


def _stored_tier(link: UniNativeTaskLink) -> str:
    """库里的档位名。旧行或没填就是空串。"""
    value = getattr(link, "recharge_template_name", "")
    return "" if value is None else str(value)


def task_item(
    row: UniNativeTask,
    template: DeliveryTemplate,
    book_name: str,
    theater_name: str,
    accounts: list[dict[str, Any]],
    links: list[dict[str, str]],
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
    batch_titles: list[str],
) -> dict[str, Any]:
    """把任务收成出参。只有执行中和完成才返回巨量项目 id，失败时列表为空。"""
    show_projects = row.status in (NativeTaskStatus.RUNNING, NativeTaskStatus.DONE)
    visible_accounts: list[dict[str, Any]] = []
    project_ids: list[int] = []
    for item in accounts:
        raw = item.get("ocean_project_id")
        shown = int(raw) if show_projects and raw is not None else None
        visible_accounts.append({**item, "ocean_project_id": shown})
        if shown is not None:
            project_ids.append(shown)
    return {
        "id": str(row.id),
        "template_id": str(template.id),
        "template_name": template.name,
        "project_budget": _money(row.project_budget),
        "roi_coefficient": _roi(row.roi_coefficient),
        "pitcher_user_id": str(row.pitcher_user_id),
        "series_id": str(row.series_id),
        "book_name": book_name,
        "series_short_name": series_short_name(book_name),
        "theater_name": theater_name,
        "accounts": visible_accounts,
        "ocean_project_ids": project_ids,
        "promotion_links": links,
        "videos": [{"id": str(video.id), "name": video.name} for video in videos],
        "titles": [{"id": str(title.id), "title": title.title} for title in titles],
        "batch_titles": list(batch_titles),
        "status": row.status,
        "failure_reason": row.failure_reason,
        "materials_uploaded": bool(row.materials_uploaded),
        "executed_at": None if row.executed_at is None else beijing_iso(row.executed_at),
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def task_filters(
    query: TaskQuery, user_id: int, scope: DataScope | None = None
) -> list[ColumnElement[bool]]:
    """列表：仅本人看自己的任务，勾了部门则看这些部门里投手的。日期段含起止当天，剧名模糊。"""
    filters: list[ColumnElement[bool]] = [
        UniNativeTask.is_deleted == 0,
        owner_match(UniNativeTask.pitcher_user_id, user_id, scope),
    ]
    if query.date_start is not None:
        filters.append(UniNativeTask.created_date >= _day_start(query.date_start))
    if query.date_end is not None:
        filters.append(UniNativeTask.created_date < _day_start(query.date_end) + timedelta(days=1))
    name = (query.series_name or "").strip()
    if name:
        filters.append(ManhuaSeries.book_name.ilike(_like(name), escape="\\"))
    return filters


def _amounts(template: DeliveryTemplate, body: TaskWrite) -> tuple[Decimal, Decimal]:
    """不传预算或 ROI 就抄模板，传了就用本次的数。"""
    budget = template.project_budget if body.project_budget is None else body.project_budget
    roi = template.roi_coefficient if body.roi_coefficient is None else body.roi_coefficient
    if budget is None:
        raise ApiError(400, "模板缺少项目预算")
    if roi is None:
        raise ApiError(400, "模板缺少 ROI 系数")
    return budget, roi


async def _template_douyin_ids(
    session: AsyncSession, template_id: int, user_id: int, douyin_ids: list[int]
) -> set[int]:
    """这条模板上，当前投手已经挂上的抖音号。"""
    if not douyin_ids:
        return set()
    result = await session.execute(
        select(DeliveryTemplateDouyin.douyin_account_id).where(
            DeliveryTemplateDouyin.template_id == template_id,
            DeliveryTemplateDouyin.user_id == user_id,
            DeliveryTemplateDouyin.douyin_account_id.in_(douyin_ids),
            DeliveryTemplateDouyin.is_deleted == 0,
        )
    )
    return set(result.scalars().all())


async def _douyin_pairs(
    session: AsyncSession,
    body: TaskWrite,
    user_id: int,
    *,
    template_id: int,
    require_template_assignment: bool = False,
) -> list[tuple[DouyinAccount, AdvertiserAccount]]:
    """每个抖音号配一个当前投手的账户。号必须是已分配的全域号。

    require_template_assignment 只给页面上的新建和保存。机器人和 record_failed_task 不走这里的强制校验。
    """
    douyin_ids = [item.douyin_account_id for item in body.accounts]
    found = {row.id: row for row in await douyin_by_ids(session, douyin_ids)}
    if any(item not in found for item in douyin_ids):
        raise ApiError(404, "抖音号不存在")
    if any(found[item].delivery_mode != "uni" for item in douyin_ids):
        raise ApiError(400, "只能使用全域抖音号")
    owned = await pitcher_owned_ids(session, douyin_ids, user_id)
    if any(item not in owned for item in douyin_ids):
        raise ApiError(400, "抖音号未分配给当前投手")
    advertiser_ids = [item.advertiser_id for item in body.accounts]
    advertisers = _order(
        await owned_advertisers(session, advertiser_ids, user_id),
        advertiser_ids,
        lambda row: int(row.advertiser_id),
    )
    if not advertisers:
        raise ApiError(400, "账户不存在、未分配给当前投手或已失效")
    if require_template_assignment:
        assigned = await _template_douyin_ids(session, template_id, user_id, douyin_ids)
        if any(item not in assigned for item in douyin_ids):
            raise ApiError(400, "抖音号未分配到这条模板")
    return [
        (found[item.douyin_account_id], advertiser)
        for item, advertiser in zip(body.accounts, advertisers, strict=True)
    ]


async def _videos(
    session: AsyncSession, body: TaskWrite, series_id: int, user_id: int, present: set[str]
) -> list[MaterialVideo]:
    """素材表在库里才查。没有表又传了 id，就拒绝，不造素材行。"""
    if not body.video_ids:
        return []
    if "material_videos" not in present:
        raise ApiError(400, "视频素材表不存在")
    videos = _order(
        await pitcher_videos(session, list(body.video_ids), series_id, user_id),
        list(body.video_ids),
        lambda row: row.id,
    )
    if not videos:
        raise ApiError(400, "视频不存在、不属于该短剧或未归属当前投手")
    return videos


async def _titles(
    session: AsyncSession, body: TaskWrite, user_id: int, present: set[str]
) -> list[MaterialTitle]:
    """标题库在库里才查。临时标题不走这里，也不会插入标题库。"""
    if not body.title_ids:
        return []
    if "material_titles" not in present:
        raise ApiError(400, "标题库不存在")
    titles = _order(
        await own_titles(session, list(body.title_ids), user_id),
        list(body.title_ids),
        lambda row: row.id,
    )
    if not titles:
        raise ApiError(400, "标题不存在或不属于当前账号")
    return titles


async def _refs(
    session: AsyncSession,
    body: TaskWrite,
    user_id: int,
    present: set[str] | None = None,
    *,
    require_template_assignment: bool = False,
) -> tuple[
    DeliveryTemplate,
    SeriesBrief,
    list[tuple[DouyinAccount, AdvertiserAccount]],
    list[MaterialVideo],
    list[MaterialTitle],
    Decimal,
    Decimal,
    str,
]:
    """核模板、短剧、账户、视频和标题。剧场名取模板上的投放主体。"""
    found = await get_uni_template_row(session, body.template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    template, subject = found
    if present is None:
        present = await present_tables(session)
    if "manhua_series" not in present:
        raise ApiError(400, "短剧库不存在")
    series = await get_series(session, body.series_id)
    if series is None:
        raise ApiError(404, "短剧不存在")
    pairs = await _douyin_pairs(
        session,
        body,
        user_id,
        template_id=int(template.id),
        require_template_assignment=require_template_assignment,
    )
    videos = await _videos(session, body, series.id, user_id, present)
    titles = await _titles(session, body, user_id, present)
    if not body.video_ids and "material_videos" in present:
        videos = await pitcher_series_videos(session, int(series.id), user_id)
    if not body.title_ids and not titles and template.title_select_mode == "auto" and "material_titles" in present:
        from app.modules.standard_delivery.match import library_titles

        category = "paid" if template.charge_mode == "IAP" else "common"
        titles = await library_titles(session, user_id, limit=10, category=category)
    budget, roi = _amounts(template, body)
    return template, series, pairs, videos, titles, budget, roi, str(subject.theater_name)


def _fill(
    row: UniNativeTask,
    template: DeliveryTemplate,
    series: SeriesBrief,
    budget: Decimal,
    roi: Decimal,
    user_id: int,
) -> None:
    """把校验过的字段写到任务上。状态保持已保存未提交。"""
    row.template_id = template.id
    row.pitcher_user_id = user_id
    row.series_id = series.id
    row.project_budget = budget
    row.roi_coefficient = roi
    row.status = NativeTaskStatus.SAVED
    row.executed_at = None


async def resolve_links(
    session: AsyncSession, body: TaskWrite, series_id: int
) -> list[tuple[str, str, str]]:
    """客户端传了链接就按原文保存。没传时带出这部剧启用的全部推广链。"""
    if body.promotion_links:
        return [
            (item.charge_mode, item.link_text, item.recharge_template_name) for item in body.promotion_links
        ]
    found: list[tuple[str, str, str]] = []
    for link in await enabled_series_links(session, series_id):
        name = str(link.recharge_template_name or "")
        url = str(link.promotion_url or "").strip()
        if not url:
            continue
        found.append((link_charge_mode(name, int(link.media_config_type or 0)), url, name))
    return found


async def ensure_one_plan(
    session: AsyncSession, series_id: int, douyin_ids: list[int], exclude_task_id: int
) -> None:
    """一部剧在一个抖音号里只能有一个未失败的投放计划。"""
    if not douyin_ids:
        return
    stmt = (
        select(UniNativeTask.id)
        .join(UniNativeTaskAccount, UniNativeTaskAccount.task_id == UniNativeTask.id)
        .where(
            UniNativeTask.series_id == series_id,
            UniNativeTask.is_deleted == 0,
            UniNativeTask.status.in_(("saved", "running", "done")),
            UniNativeTaskAccount.douyin_account_id.in_(douyin_ids),
            UniNativeTaskAccount.is_deleted == 0,
            UniNativeTask.id != exclude_task_id,
        )
        .limit(1)
    )
    row = (await session.execute(stmt)).one_or_none()
    if row is not None and isinstance(row[0], int):
        raise ApiError(400, "这部剧在该抖音号已有投放计划")


def _saved_item(
    row: UniNativeTask,
    template: DeliveryTemplate,
    series: SeriesBrief,
    pairs: list[tuple[DouyinAccount, AdvertiserAccount]],
    links: list[tuple[str, str, str]],
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
    batch_titles: list[str],
    theater_name: str,
) -> dict[str, Any]:
    """用刚校验过的对象拼出参，不再回表。"""
    return task_item(
        row,
        template,
        series.book_name,
        theater_name,
        [_account_dict(douyin, advertiser) for douyin, advertiser in pairs],
        [_link_dict(charge_mode, link_text, tier_name) for charge_mode, link_text, tier_name in links],
        videos,
        titles,
        list(batch_titles),
    )


async def create_task(
    session: AsyncSession,
    body: TaskWrite,
    user_id: int,
    *,
    require_template_assignment: bool = False,
) -> dict[str, Any]:
    """新增一条已保存未提交的任务。不在这里建项目，避免和随后的提交各建一套。"""
    template, series, pairs, videos, titles, budget, roi, theater_name = await _refs(
        session, body, user_id, require_template_assignment=require_template_assignment
    )
    row = UniNativeTask(
        template_id=template.id,
        pitcher_user_id=user_id,
        series_id=series.id,
        project_budget=budget,
        roi_coefficient=roi,
        status=NativeTaskStatus.SAVED,
        executed_at=None,
    )
    session.add(row)
    await session.flush()
    links = await resolve_links(session, body, series.id)
    await replace_children(
        session,
        row.id,
        pairs,
        links,
        videos,
        titles,
        list(body.batch_titles),
    )
    await ensure_one_plan(session, int(series.id), [int(douyin.id) for douyin, _account in pairs], int(row.id))
    await session.commit()
    await session.refresh(row)
    return _saved_item(
        row, template, series, pairs, links, videos, titles, list(body.batch_titles), theater_name
    )


async def record_failed_task(
    session: AsyncSession,
    *,
    template: DeliveryTemplate,
    series_id: int,
    user_id: int,
    pairs: list[tuple[DouyinAccount, AdvertiserAccount]],
    links: list[tuple[str, str, str]],
    reason: str,
) -> UniNativeTask:
    """直接落一条失败任务，不带视频，也不自动带出视频。不提交、不调客户端。"""
    budget = template.project_budget
    roi = template.roi_coefficient
    if budget is None:
        raise ApiError(400, "模板缺少项目预算")
    if roi is None:
        raise ApiError(400, "模板缺少 ROI 系数")
    row = UniNativeTask(
        template_id=template.id,
        pitcher_user_id=user_id,
        series_id=series_id,
        project_budget=budget,
        roi_coefficient=roi,
        status=NativeTaskStatus.FAILED,
        failure_reason=reason,
        materials_uploaded=False,
        executed_at=None,
    )
    session.add(row)
    await session.flush()
    await replace_children(session, row.id, pairs, links, [], [], [])
    await session.commit()
    return row


async def mark_failed_if_saved(session: AsyncSession, task_id: int, user_id: int, reason: str) -> None:
    """页面保存已经落库，但提交在改状态前失败时，把 saved 改成 failed。已经不是 saved 就不动。"""
    present = await present_tables(session)
    found = await get_task_row(session, task_id, user_id, series_present="manhua_series" in present)
    if found is None:
        return
    task, *_rest = found
    if task.status != NativeTaskStatus.SAVED:
        return
    task.status = NativeTaskStatus.FAILED
    task.failure_reason = reason
    task.materials_uploaded = False
    await session.commit()


async def update_task(
    session: AsyncSession,
    task_id: int,
    body: TaskWrite,
    user_id: int,
    *,
    require_template_assignment: bool = False,
) -> dict[str, Any]:
    """整表保存自己仍是 saved 的任务。已经创建过项目的不再改，也不在这里建项目。"""
    present = await present_tables(session)
    found = await get_task_row(session, task_id, user_id, series_present="manhua_series" in present)
    if found is None:
        raise ApiError(404, "投放任务不存在")
    current, *_rest = found
    if current.status != NativeTaskStatus.SAVED:
        raise ApiError(409, "任务已创建，不能再修改")
    template, series, pairs, videos, titles, budget, roi, theater_name = await _refs(
        session,
        body,
        user_id,
        present,
        require_template_assignment=require_template_assignment,
    )
    _fill(current, template, series, budget, roi, user_id)
    current.updated_date = beijing_now()
    links = await resolve_links(session, body, series.id)
    await replace_children(
        session,
        current.id,
        pairs,
        links,
        videos,
        titles,
        list(body.batch_titles),
    )
    await ensure_one_plan(
        session, int(series.id), [int(douyin.id) for douyin, _account in pairs], int(current.id)
    )
    await session.commit()
    await session.refresh(current)
    return _saved_item(
        current, template, series, pairs, links, videos, titles, list(body.batch_titles), theater_name
    )


async def delete_task(session: AsyncSession, task_id: int, user_id: int) -> dict[str, Any]:
    """软删自己的任务。"""
    present = await present_tables(session)
    found = await get_task_row(session, task_id, user_id, series_present="manhua_series" in present)
    if found is None:
        raise ApiError(404, "投放任务不存在")
    row, *_rest = found
    row.mark_deleted()
    await session.commit()
    return {"id": str(row.id), "deleted": True}


async def _children(
    session: AsyncSession, task_ids: list[int], present: set[str]
) -> tuple[
    dict[int, list[tuple[UniNativeTaskAccount, DouyinAccount, AdvertiserAccount]]],
    dict[int, list[UniNativeTaskLink]],
    dict[int, list[MaterialVideo]],
    dict[int, list[MaterialTitle]],
    dict[int, list[str]],
]:
    """补一页任务的关联。素材表不在库里就不去连它。"""
    accounts = await accounts_by_tasks(session, task_ids)
    links = await links_by_tasks(session, task_ids)
    videos = (
        await videos_by_tasks(session, task_ids)
        if "material_videos" in present
        else {item: [] for item in task_ids}
    )
    titles = (
        await titles_by_tasks(session, task_ids)
        if "material_titles" in present
        else {item: [] for item in task_ids}
    )
    batches = await batch_titles_by_tasks(session, task_ids)
    return accounts, links, videos, titles, batches


def _page_item(
    head: TaskHead,
    accounts: dict[int, list[tuple[UniNativeTaskAccount, DouyinAccount, AdvertiserAccount]]],
    links: dict[int, list[UniNativeTaskLink]],
    videos: dict[int, list[MaterialVideo]],
    titles: dict[int, list[MaterialTitle]],
    batches: dict[int, list[str]],
) -> dict[str, Any]:
    """把列表行和关联收成一条出参。"""
    row, template, book_name, theater_name = head
    return task_item(
        row,
        template,
        book_name,
        theater_name,
        [
            _account_dict(douyin, advertiser, account.ocean_project_id)
            for account, douyin, advertiser in accounts.get(row.id, [])
        ],
        [_link_dict(link.charge_mode, link.link_text, _stored_tier(link)) for link in links.get(row.id, [])],
        videos.get(row.id, []),
        titles.get(row.id, []),
        batches.get(row.id, []),
    )


async def list_tasks(
    session: AsyncSession, query: TaskQuery, user_id: int, scope: DataScope | None = None
) -> dict[str, Any]:
    """分页列任务。仅本人时只看自己，勾了部门则看这些部门里投手的。剧名筛选依赖短剧表。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    present = await present_tables(session)
    name = (query.series_name or "").strip()
    if name and "manhua_series" not in present:
        return page_data([], 0, params)
    rows, total = await page_tasks(
        session,
        task_filters(query, user_id, scope),
        series_present="manhua_series" in present,
        offset=params.offset,
        limit=params.page_size,
    )
    if not rows:
        return page_data([], total, params)
    task_ids = [row.id for row, _template, _book, _theater in rows]
    accounts, links, videos, titles, batches = await _children(session, task_ids, present)
    items = [_page_item(head, accounts, links, videos, titles, batches) for head in rows]
    return page_data(items, total, params)


async def get_task(
    session: AsyncSession, task_id: int, user_id: int, scope: DataScope | None = None
) -> dict[str, Any]:
    """取数据范围内的一条任务。范围外的按不存在。"""
    present = await present_tables(session)
    found = await get_task_row(
        session, task_id, user_id, series_present="manhua_series" in present, scope=scope
    )
    if found is None:
        raise ApiError(404, "投放任务不存在")
    accounts, links, videos, titles, batches = await _children(session, [found[0].id], present)
    return _page_item(found, accounts, links, videos, titles, batches)
