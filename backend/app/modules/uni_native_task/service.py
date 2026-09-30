"""端原生投放任务的本地保存。不上传素材，也不调用巨量。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import BEIJING, beijing_iso, beijing_now
from app.modules.account.model import AdvertiserAccount, DouyinAccount
from app.modules.material.model import ManhuaSeries
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.standard_delivery.model import DeliveryTemplate
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
    pitcher_videos,
    present_tables,
    replace_children,
    titles_by_tasks,
    videos_by_tasks,
)
from app.modules.uni_native_task.model import NativeTaskStatus, UniNativeTask, UniNativeTaskLink
from app.modules.uni_native_task.schema import TaskQuery, TaskWrite
from app.modules.uni_template.crud import douyin_by_ids, get_uni_template_row, pitcher_owned_ids

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


def _account_dict(douyin: DouyinAccount, advertiser: AdvertiserAccount) -> dict[str, Any]:
    """把一对抖音号和账户收成出参。"""
    return {
        "douyin_account_id": str(douyin.id),
        "aweme_id": douyin.aweme_id,
        "douyin_name": douyin.name,
        "advertiser_account_id": str(advertiser.id),
        "advertiser_id": int(advertiser.advertiser_id),
        "name": advertiser.local_name or advertiser.name,
    }


def _link_dict(charge_mode: str, link_text: str) -> dict[str, str]:
    """把一条推广链收成出参。"""
    return {"charge_mode": charge_mode, "link_text": link_text}


def task_item(
    row: UniNativeTask,
    template: DeliveryTemplate,
    book_name: str,
    accounts: list[dict[str, Any]],
    links: list[dict[str, str]],
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
    batch_titles: list[str],
) -> dict[str, Any]:
    """把任务收成出参。状态保持已保存未提交。"""
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
        "accounts": accounts,
        "promotion_links": links,
        "videos": [{"id": str(video.id), "name": video.name} for video in videos],
        "titles": [{"id": str(title.id), "title": title.title} for title in titles],
        "batch_titles": list(batch_titles),
        "status": row.status,
        "executed_at": None if row.executed_at is None else beijing_iso(row.executed_at),
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def task_filters(query: TaskQuery, user_id: int) -> list[ColumnElement[bool]]:
    """列表只看当前投手未删除的任务。日期段含起止当天，剧名模糊。"""
    filters: list[ColumnElement[bool]] = [
        UniNativeTask.is_deleted == 0,
        UniNativeTask.pitcher_user_id == user_id,
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


async def _douyin_pairs(
    session: AsyncSession, body: TaskWrite, user_id: int
) -> list[tuple[DouyinAccount, AdvertiserAccount]]:
    """每个抖音号配一个当前投手的账户。号必须是已分配的全域号。"""
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
    session: AsyncSession, body: TaskWrite, user_id: int, present: set[str] | None = None
) -> tuple[
    DeliveryTemplate,
    SeriesBrief,
    list[tuple[DouyinAccount, AdvertiserAccount]],
    list[MaterialVideo],
    list[MaterialTitle],
    Decimal,
    Decimal,
]:
    """核模板、短剧、账户、视频和标题。剧场表不参与。"""
    found = await get_uni_template_row(session, body.template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    template, _subject = found
    if present is None:
        present = await present_tables(session)
    if "manhua_series" not in present:
        raise ApiError(400, "短剧库不存在")
    series = await get_series(session, body.series_id)
    if series is None:
        raise ApiError(404, "短剧不存在")
    pairs = await _douyin_pairs(session, body, user_id)
    videos = await _videos(session, body, series.id, user_id, present)
    titles = await _titles(session, body, user_id, present)
    budget, roi = _amounts(template, body)
    return template, series, pairs, videos, titles, budget, roi


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


def _saved_item(
    row: UniNativeTask,
    template: DeliveryTemplate,
    series: SeriesBrief,
    pairs: list[tuple[DouyinAccount, AdvertiserAccount]],
    body: TaskWrite,
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
) -> dict[str, Any]:
    """用刚校验过的对象拼出参，不再回表。"""
    return task_item(
        row,
        template,
        series.book_name,
        [_account_dict(douyin, advertiser) for douyin, advertiser in pairs],
        [_link_dict(item.charge_mode, item.link_text) for item in body.promotion_links],
        videos,
        titles,
        list(body.batch_titles),
    )


async def create_task(session: AsyncSession, body: TaskWrite, user_id: int) -> dict[str, Any]:
    """新增一条已保存未提交的任务。"""
    template, series, pairs, videos, titles, budget, roi = await _refs(session, body, user_id)
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
    await replace_children(
        session,
        row.id,
        pairs,
        [(item.charge_mode, item.link_text) for item in body.promotion_links],
        videos,
        titles,
        list(body.batch_titles),
    )
    await session.commit()
    await session.refresh(row)
    return _saved_item(row, template, series, pairs, body, videos, titles)


async def update_task(
    session: AsyncSession, task_id: int, body: TaskWrite, user_id: int
) -> dict[str, Any]:
    """整表保存自己的任务。账户、推广链、视频和标题按本次提交替换。"""
    present = await present_tables(session)
    found = await get_task_row(session, task_id, user_id, series_present="manhua_series" in present)
    if found is None:
        raise ApiError(404, "投放任务不存在")
    current, *_rest = found
    template, series, pairs, videos, titles, budget, roi = await _refs(session, body, user_id, present)
    _fill(current, template, series, budget, roi, user_id)
    current.updated_date = beijing_now()
    await replace_children(
        session,
        current.id,
        pairs,
        [(item.charge_mode, item.link_text) for item in body.promotion_links],
        videos,
        titles,
        list(body.batch_titles),
    )
    await session.commit()
    await session.refresh(current)
    return _saved_item(current, template, series, pairs, body, videos, titles)


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
    dict[int, list[tuple[DouyinAccount, AdvertiserAccount]]],
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
    accounts: dict[int, list[tuple[DouyinAccount, AdvertiserAccount]]],
    links: dict[int, list[UniNativeTaskLink]],
    videos: dict[int, list[MaterialVideo]],
    titles: dict[int, list[MaterialTitle]],
    batches: dict[int, list[str]],
) -> dict[str, Any]:
    """把列表行和关联收成一条出参。"""
    row, template, book_name = head
    return task_item(
        row,
        template,
        book_name,
        [_account_dict(douyin, advertiser) for douyin, advertiser in accounts.get(row.id, [])],
        [_link_dict(link.charge_mode, link.link_text) for link in links.get(row.id, [])],
        videos.get(row.id, []),
        titles.get(row.id, []),
        batches.get(row.id, []),
    )


async def list_tasks(session: AsyncSession, query: TaskQuery, user_id: int) -> dict[str, Any]:
    """分页列出当前投手自己的任务。剧名筛选依赖短剧表，表不在就给空页。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    present = await present_tables(session)
    name = (query.series_name or "").strip()
    if name and "manhua_series" not in present:
        return page_data([], 0, params)
    rows, total = await page_tasks(
        session,
        task_filters(query, user_id),
        series_present="manhua_series" in present,
        offset=params.offset,
        limit=params.page_size,
    )
    if not rows:
        return page_data([], total, params)
    task_ids = [row.id for row, _template, _book in rows]
    accounts, links, videos, titles, batches = await _children(session, task_ids, present)
    items = [_page_item(head, accounts, links, videos, titles, batches) for head in rows]
    return page_data(items, total, params)


async def get_task(session: AsyncSession, task_id: int, user_id: int) -> dict[str, Any]:
    """取当前投手自己的一条任务。别人的按不存在。"""
    present = await present_tables(session)
    found = await get_task_row(session, task_id, user_id, series_present="manhua_series" in present)
    if found is None:
        raise ApiError(404, "投放任务不存在")
    accounts, links, videos, titles, batches = await _children(session, [found[0].id], present)
    return _page_item(found, accounts, links, videos, titles, batches)
