"""漫剧标准投放：模板、任务草稿、自动规则的保存和筛选。

不创建巨量项目或单元。抖音号只认已启用的标准号，不按投手过滤。
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_iso, beijing_now
from app.modules.account.model import AdvertiserAccount, DeliverySubject, DouyinAccount, ProductLibrary
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.standard_delivery.crud import (
    accounts_by_drafts,
    get_draft_row,
    get_library_by_no,
    get_rule_row,
    get_series,
    get_series_by_ids,
    get_standard_douyin,
    get_subject,
    get_template_row,
    library_assigned,
    own_titles,
    owned_advertisers,
    page_drafts,
    page_rules,
    page_templates,
    replace_rule_series,
    replace_task_links,
    rule_has_series,
    rule_name_taken,
    SeriesBrief,
    series_by_rules,
    template_in_use,
    template_name_taken,
    titles_by_drafts,
    videos_by_drafts,
    visible_videos,
)
from app.modules.standard_delivery.model import (
    GOAL_BY_CHARGE,
    ChargeMode,
    DeliveryAutoRule,
    DeliveryTaskDraft,
    DeliveryTemplate,
    TemplateMode,
)
from app.modules.standard_delivery.schema import (
    DraftQuery,
    DraftWrite,
    RuleQuery,
    RuleWrite,
    TemplateQuery,
    TemplateUpdate,
    TemplateWrite,
)

_PANEL_SPLIT = re.compile(r"[,，、;；]+")
T = TypeVar("T")


def panel_tokens(raw: str | None) -> list[str]:
    """把主体上的出价面板拆成可多选的项。分隔符是逗号、顿号、分号。"""
    if raw is None or not raw.strip():
        return []
    seen: list[str] = []
    for part in _PANEL_SPLIT.split(raw.strip()):
        item = part.strip()
        if item and item not in seen:
            seen.append(item)
    return seen


def require_subject_for_template(subject: DeliverySubject, charge_mode: str) -> None:
    """模板只能挂标准投放、且收费模式相同的主体。"""
    if subject.delivery_mode != "standard":
        raise ApiError(400, "主体不是标准投放")
    if subject.charge_mode != charge_mode:
        raise ApiError(400, "主体收费模式与模板不一致")


def require_panels(charge_mode: str, selected: list[str], subject_panel: str | None) -> None:
    """付费至少选一条。选出的每一条都得在主体的出价面板里。"""
    if charge_mode == ChargeMode.IAP and not selected:
        raise ApiError(400, "付费模板至少选一个出价面板")
    if not selected:
        return
    tokens = panel_tokens(subject_panel)
    if not tokens:
        raise ApiError(400, "主体没有出价面板")
    missing = [item for item in selected if item not in tokens]
    if missing:
        raise ApiError(400, f"出价面板不在该主体上：{missing[0]}")


def _like(raw: str) -> str:
    """ILIKE 片段，% 和 _ 按字面量匹配。"""
    escaped = raw.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _money(value: Decimal) -> str:
    """金额保留两位小数。"""
    return format(value.quantize(Decimal("0.01")), "f")


def _roi(value: Decimal) -> str:
    """回收率保留四位小数。"""
    return format(value.quantize(Decimal("0.0001")), "f")


def _roi_goal(value: Decimal | None) -> str | None:
    """标准模板的 ROI 目标保留三位小数。空就空。"""
    if value is None:
        return None
    return format(value.quantize(Decimal("0.001")), "f")


def _day(value: date | None) -> str | None:
    """日期收成 yyyy-MM-dd。"""
    if value is None:
        return None
    return value.isoformat()


def _order(rows: list[T], wanted: list[int], key) -> list[T]:
    """按请求里的 id 顺序重排。缺一条就返回空列表，调用方再报错。"""
    found = {key(row): row for row in rows}
    if any(item not in found for item in wanted):
        return []
    return [found[item] for item in wanted]


def template_item(row: DeliveryTemplate, subject_name: str) -> dict[str, Any]:
    """把模板行收成出参。"""
    return {
        "id": str(row.id),
        "name": row.name,
        "charge_mode": row.charge_mode,
        "subject_id": str(row.subject_id),
        "subject_name": subject_name,
        "bid_panels": list(row.bid_panels or []),
        "ads_per_account": row.ads_per_account,
        "ocean_delivery_mode": row.ocean_delivery_mode,
        "bid_type": row.bid_type,
        "schedule_type": row.schedule_type,
        "schedule_start_date": _day(row.schedule_start_date),
        "schedule_end_date": _day(row.schedule_end_date),
        "schedule_time": row.schedule_time,
        "ad_source": row.ad_source,
        "product_name": row.product_name,
        "selling_points": list(row.selling_points or []),
        "call_to_action_buttons": list(row.call_to_action_buttons or []),
        "roi_goal": _roi_goal(row.roi_goal),
        "videos_per_ad": row.videos_per_ad,
        "titles_per_ad": row.titles_per_ad,
        "placement": row.placement,
        "district": row.district,
        "city_codes": [int(code) for code in (row.city_codes or [])],
        "gender": row.gender or "none",
        "age_bands": [str(band) for band in (row.age_bands or [])],
        "project_budget": None if row.project_budget is None else _money(row.project_budget),
        "library_kind": row.library_kind,
        "product_select": row.product_select,
        "material_boost": bool(row.material_boost),
        "promotion_operation": row.promotion_operation,
        "douyin_account_id": None if row.douyin_account_id is None else str(row.douyin_account_id),
        "product_image_id": row.product_image_id,
        "title_select_mode": row.standard_title_select_mode,
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def _apply_standard_template(row: DeliveryTemplate, body: TemplateWrite | TemplateUpdate) -> None:
    """把标准提交字段写上，并清空全域列。标准行不用 roi_coefficient。"""
    row.ocean_delivery_mode = body.ocean_delivery_mode
    row.bid_type = body.bid_type
    row.schedule_type = body.schedule_type
    row.schedule_start_date = body.schedule_start_date
    row.schedule_end_date = body.schedule_end_date
    row.schedule_time = body.schedule_time
    row.ad_source = body.ad_source
    row.product_name = body.product_name
    row.selling_points = list(body.selling_points)
    row.call_to_action_buttons = list(body.call_to_action_buttons)
    row.roi_goal = body.roi_goal
    row.videos_per_ad = body.videos_per_ad
    row.titles_per_ad = body.titles_per_ad
    row.project_budget = body.project_budget
    row.placement = None if body.placement is None else str(body.placement)
    row.district = None if body.district is None else str(body.district)
    row.city_codes = list(body.city_codes) or None
    row.gender = body.gender.value
    row.age_bands = [band.value for band in body.age_bands] or None
    row.product_library_id = None
    row.library_kind = None if body.library_kind is None else str(body.library_kind)
    row.product_select = None if body.product_select is None else str(body.product_select)
    row.material_boost = bool(body.material_boost)
    row.promotion_operation = None if body.promotion_operation is None else str(body.promotion_operation)
    row.douyin_account_id = body.douyin_account_id
    row.product_image_id = body.product_image_id
    row.standard_title_select_mode = None if body.title_select_mode is None else str(body.title_select_mode)
    row.roi_coefficient = None
    row.aigc_dynamic_creative = None
    row.title_select_mode = None


def template_filters(query: TemplateQuery) -> list[ColumnElement[bool]]:
    """标准模板列表：未删除，只要标准投放，收费模式精确，名称模糊，主体精确。"""
    filters: list[ColumnElement[bool]] = [
        DeliveryTemplate.is_deleted == 0,
        DeliveryTemplate.delivery_mode == TemplateMode.STANDARD,
        DeliveryTemplate.charge_mode == query.charge_mode,
    ]
    name = (query.name or "").strip()
    if name:
        filters.append(DeliveryTemplate.name.ilike(_like(name), escape="\\"))
    if query.subject_id is not None:
        filters.append(DeliveryTemplate.subject_id == query.subject_id)
    return filters


async def list_templates(session: AsyncSession, query: TemplateQuery) -> dict[str, Any]:
    """分页列出未删除的模板。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_templates(
        session, template_filters(query), offset=params.offset, limit=params.page_size
    )
    return page_data([template_item(row, subject.name) for row, subject in rows], total, params)


def _require_mode(charge_mode: str, allowed: set[str]) -> None:
    """没有对应免费或付费菜单时拒绝。"""
    if charge_mode not in allowed:
        raise ApiError(403, "已登录但无对应菜单或组件")


async def get_template(session: AsyncSession, template_id: int, allowed: set[str]) -> dict[str, Any]:
    """取一条模板。收费模式不在授权菜单里则拒绝。"""
    found = await get_template_row(session, template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    row, subject = found
    _require_mode(row.charge_mode, allowed)
    return template_item(row, subject.name)


async def _require_template_links(session: AsyncSession, body: TemplateWrite | TemplateUpdate) -> None:
    """标准抖音号要真实存在。商品库类型只记 video 或 novel，不查某一行商品库。"""
    if body.douyin_account_id is None:
        return
    douyin = await get_standard_douyin(session, body.douyin_account_id)
    if douyin is None:
        raise ApiError(400, "抖音号不是已启用的标准号")


async def create_template(session: AsyncSession, body: TemplateWrite, allowed: set[str]) -> dict[str, Any]:
    """校验主体和出价面板后新增模板。"""
    _require_mode(body.charge_mode, allowed)
    subject = await get_subject(session, body.subject_id)
    if subject is None:
        raise ApiError(404, "主体不存在")
    require_subject_for_template(subject, body.charge_mode)
    require_panels(body.charge_mode, list(body.bid_panels), subject.bid_panel)
    if await template_name_taken(session, body.charge_mode, body.name, None):
        raise ApiError(409, "模板名称已存在")
    await _require_template_links(session, body)
    row = DeliveryTemplate(
        name=body.name,
        delivery_mode=TemplateMode.STANDARD,
        charge_mode=body.charge_mode,
        subject_id=subject.id,
        bid_panels=list(body.bid_panels),
        ads_per_account=body.ads_per_account,
    )
    _apply_standard_template(row, body)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return template_item(row, subject.name)


async def update_template(
    session: AsyncSession, template_id: int, body: TemplateUpdate, allowed: set[str]
) -> dict[str, Any]:
    """改名称、主体、出价面板和每账户广告条数。收费模式不动。"""
    found = await get_template_row(session, template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    row, _current = found
    _require_mode(row.charge_mode, allowed)
    subject = await get_subject(session, body.subject_id)
    if subject is None:
        raise ApiError(404, "主体不存在")
    require_subject_for_template(subject, row.charge_mode)
    require_panels(row.charge_mode, list(body.bid_panels), subject.bid_panel)
    if await template_name_taken(session, row.charge_mode, body.name, row.id):
        raise ApiError(409, "模板名称已存在")
    await _require_template_links(session, body)
    row.name = body.name
    row.subject_id = subject.id
    row.bid_panels = list(body.bid_panels)
    row.ads_per_account = body.ads_per_account
    _apply_standard_template(row, body)
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    return template_item(row, subject.name)


async def delete_template(session: AsyncSession, template_id: int, allowed: set[str]) -> dict[str, Any]:
    """软删模板。还有草稿或规则在用就拒绝。"""
    found = await get_template_row(session, template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    row, _subject = found
    _require_mode(row.charge_mode, allowed)
    if await template_in_use(session, row.id):
        raise ApiError(409, "模板已被投放草稿或自动规则使用")
    row.mark_deleted()
    await session.commit()
    return {"id": str(row.id), "deleted": True}


def _account_name(row: AdvertiserAccount) -> str:
    """有中台名用中台名，否则用巨量账户名。"""
    local = (row.local_name or "").strip()
    return local or row.name


def draft_item(
    row: DeliveryTaskDraft,
    template: DeliveryTemplate,
    subject: DeliverySubject,
    douyin: DouyinAccount | None,
    series: SeriesBrief,
    library: ProductLibrary | None,
    accounts: list[AdvertiserAccount],
    videos: list[MaterialVideo],
    titles: list[MaterialTitle],
) -> dict[str, Any]:
    """把草稿和它的账户、视频、标题收成出参。"""
    return {
        "id": str(row.id),
        "charge_mode": row.charge_mode,
        "template_id": str(template.id),
        "template_name": template.name,
        "subject_id": str(subject.id),
        "subject_name": subject.name,
        "bid_panels": list(template.bid_panels or []),
        "ads_per_account": template.ads_per_account,
        "pitcher_user_id": str(row.pitcher_user_id),
        "schedule_start": None if row.schedule_start is None else beijing_iso(row.schedule_start),
        "schedule_end": None if row.schedule_end is None else beijing_iso(row.schedule_end),
        "douyin_account_id": None if douyin is None else str(douyin.id),
        "aweme_id": None if douyin is None else douyin.aweme_id,
        "douyin_name": None if douyin is None else douyin.name,
        "series_id": str(series.id),
        "book_name": series.book_name,
        "accounts": [
            {
                "advertiser_account_id": str(account.id),
                "advertiser_id": int(account.advertiser_id),
                "name": _account_name(account),
            }
            for account in accounts
        ],
        "videos": [{"id": str(video.id), "name": video.name} for video in videos],
        "titles": [{"id": str(title.id), "title": title.title} for title in titles],
        "placement": row.placement,
        "project_budget": None if row.project_budget is None else _money(row.project_budget),
        "ad_budget": _money(row.ad_budget),
        "optimize_goal": row.optimize_goal,
        "product_library_id": None if library is None else str(library.id),
        "library_no": None if library is None else int(library.library_no),
        "library_name": None if library is None else library.name,
        "album_url": row.album_url,
        "project_operation": row.project_operation,
        "promotion_operation": row.promotion_operation,
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def draft_filters(query: DraftQuery, user_id: int) -> list[ColumnElement[bool]]:
    """草稿列表：只看当前投手，收费模式精确，其余筛选项有值才加上。"""
    filters: list[ColumnElement[bool]] = [
        DeliveryTaskDraft.is_deleted == 0,
        DeliveryTaskDraft.pitcher_user_id == user_id,
        DeliveryTaskDraft.charge_mode == query.charge_mode,
    ]
    if query.template_id is not None:
        filters.append(DeliveryTaskDraft.template_id == query.template_id)
    if query.subject_id is not None:
        filters.append(DeliveryTemplate.subject_id == query.subject_id)
    if query.series_id is not None:
        filters.append(DeliveryTaskDraft.series_id == query.series_id)
    if query.douyin_account_id is not None:
        filters.append(DeliveryTaskDraft.douyin_account_id == query.douyin_account_id)
    if query.library_no is not None:
        filters.append(ProductLibrary.library_no == query.library_no)
    if query.placement is not None:
        filters.append(DeliveryTaskDraft.placement == query.placement)
    if query.optimize_goal is not None:
        filters.append(DeliveryTaskDraft.optimize_goal == query.optimize_goal)
    if query.scheduled is True:
        filters.append(DeliveryTaskDraft.schedule_start.is_not(None))
    elif query.scheduled is False:
        filters.append(DeliveryTaskDraft.schedule_start.is_(None))
    return filters


async def _draft_page(session: AsyncSession, rows: list[Any]) -> list[dict[str, Any]]:
    """给一页草稿补上账户、视频、标题。"""
    draft_ids = [row.id for row, *_rest in rows]
    accounts = await accounts_by_drafts(session, draft_ids)
    videos = await videos_by_drafts(session, draft_ids)
    titles = await titles_by_drafts(session, draft_ids)
    return [
        draft_item(
            draft,
            template,
            subject,
            douyin,
            series,
            library,
            accounts.get(draft.id, []),
            videos.get(draft.id, []),
            titles.get(draft.id, []),
        )
        for draft, template, subject, douyin, series, library in rows
    ]


async def list_drafts(session: AsyncSession, query: DraftQuery, user_id: int) -> dict[str, Any]:
    """分页列出当前投手自己的草稿。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_drafts(
        session, draft_filters(query, user_id), offset=params.offset, limit=params.page_size
    )
    return page_data(await _draft_page(session, rows), total, params)


async def get_draft(
    session: AsyncSession, draft_id: int, user_id: int, allowed: set[str]
) -> dict[str, Any]:
    """取当前投手自己的一条草稿。别人的按不存在。"""
    found = await get_draft_row(session, draft_id, user_id)
    if found is None:
        raise ApiError(404, "投放草稿不存在")
    _require_mode(found[0].charge_mode, allowed)
    items = await _draft_page(session, [found])
    return items[0]


def _require_goal(charge_mode: str, optimize_goal: str) -> None:
    """优化目标必须和收费模式锁死的那一个相同。"""
    expected = GOAL_BY_CHARGE[ChargeMode(charge_mode)]
    if optimize_goal != expected:
        raise ApiError(400, "优化目标与模板收费模式不一致")


async def _library_for_user(session: AsyncSession, library_no: int, user_id: int) -> ProductLibrary:
    """商品库须存在。标准库还要分给当前投手，兜底库全员可用。"""
    library = await get_library_by_no(session, library_no)
    if library is None:
        raise ApiError(404, "商品库不存在")
    if library.library_role == "fallback":
        return library
    if library.library_role == "standard" and await library_assigned(session, library.id, user_id):
        return library
    raise ApiError(400, "商品库未分配给当前投手")


async def _draft_refs(
    session: AsyncSession, body: DraftWrite, user_id: int, allowed: set[str]
) -> tuple[
    DeliveryTemplate,
    DeliverySubject,
    DouyinAccount | None,
    SeriesBrief,
    list[AdvertiserAccount],
    list[MaterialVideo],
    list[MaterialTitle],
    ProductLibrary | None,
]:
    """把草稿要挂的现成数据一次核完。抖音号不看投手分配。留空的字段确认提交时用模板。"""
    found = await get_template_row(session, body.template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    template, subject = found
    _require_mode(template.charge_mode, allowed)
    _require_goal(template.charge_mode, body.optimize_goal)
    douyin: DouyinAccount | None = None
    if body.douyin_account_id is not None:
        douyin = await get_standard_douyin(session, body.douyin_account_id)
        if douyin is None:
            raise ApiError(400, "抖音号不是已启用的标准号")
    series = await get_series(session, body.series_id)
    if series is None:
        raise ApiError(404, "短剧不存在")
    accounts = _order(
        await owned_advertisers(session, list(body.advertiser_ids), user_id),
        list(body.advertiser_ids),
        lambda row: int(row.advertiser_id),
    )
    if not accounts:
        raise ApiError(400, "账户不存在、未分配给当前投手或已失效")
    videos = _order(
        await visible_videos(session, list(body.video_ids), series.id, user_id),
        list(body.video_ids),
        lambda row: row.id,
    )
    if not videos:
        raise ApiError(400, "视频不存在、不属于该短剧或当前账号不可见")
    titles = _order(
        await own_titles(session, list(body.title_ids), user_id),
        list(body.title_ids),
        lambda row: row.id,
    )
    if not titles:
        raise ApiError(400, "标题不存在或不属于当前账号")
    library: ProductLibrary | None = None
    if body.library_no is not None:
        library = await _library_for_user(session, body.library_no, user_id)
    return template, subject, douyin, series, accounts, videos, titles, library


def _fill_draft(
    row: DeliveryTaskDraft,
    template: DeliveryTemplate,
    body: DraftWrite,
    douyin: DouyinAccount | None,
    series: SeriesBrief,
    library: ProductLibrary | None,
    user_id: int,
) -> None:
    """把校验过的字段写到草稿行上。一个抖音号，不写成列表。留空表示用模板。"""
    row.template_id = template.id
    row.charge_mode = template.charge_mode
    row.pitcher_user_id = user_id
    row.schedule_start = body.schedule_start
    row.schedule_end = body.schedule_end
    row.douyin_account_id = None if douyin is None else douyin.id
    row.series_id = series.id
    row.placement = None if body.placement is None else str(body.placement)
    row.project_budget = body.project_budget
    row.ad_budget = body.ad_budget
    row.optimize_goal = body.optimize_goal
    row.product_library_id = None if library is None else library.id
    row.album_url = body.album_url
    row.project_operation = body.project_operation
    row.promotion_operation = body.promotion_operation


async def create_draft(
    session: AsyncSession, body: DraftWrite, user_id: int, allowed: set[str]
) -> dict[str, Any]:
    """新增一条草稿。多个账户共用同一个抖音号。"""
    template, subject, douyin, series, accounts, videos, titles, library = await _draft_refs(
        session, body, user_id, allowed
    )
    row = DeliveryTaskDraft(
        template_id=template.id,
        charge_mode=template.charge_mode,
        pitcher_user_id=user_id,
        douyin_account_id=None if douyin is None else douyin.id,
        series_id=series.id,
        placement=None if body.placement is None else str(body.placement),
        project_budget=body.project_budget,
        ad_budget=body.ad_budget,
        optimize_goal=body.optimize_goal,
        product_library_id=None if library is None else library.id,
        schedule_start=body.schedule_start,
        schedule_end=body.schedule_end,
        album_url=body.album_url,
        project_operation=body.project_operation,
        promotion_operation=body.promotion_operation,
    )
    session.add(row)
    await session.flush()
    await replace_task_links(session, row.id, accounts, videos, titles)
    await session.commit()
    await session.refresh(row)
    return draft_item(row, template, subject, douyin, series, library, accounts, videos, titles)


async def update_draft(
    session: AsyncSession, draft_id: int, body: DraftWrite, user_id: int, allowed: set[str]
) -> dict[str, Any]:
    """整表保存自己的草稿。收费模式必须和原来的模板一致。"""
    found = await get_draft_row(session, draft_id, user_id)
    if found is None:
        raise ApiError(404, "投放草稿不存在")
    current, *_rest = found
    _require_mode(current.charge_mode, allowed)
    template, subject, douyin, series, accounts, videos, titles, library = await _draft_refs(
        session, body, user_id, allowed
    )
    if template.charge_mode != current.charge_mode:
        raise ApiError(400, "模板收费模式与草稿不一致")
    _fill_draft(current, template, body, douyin, series, library, user_id)
    current.updated_date = beijing_now()
    await replace_task_links(session, current.id, accounts, videos, titles)
    await session.commit()
    await session.refresh(current)
    return draft_item(current, template, subject, douyin, series, library, accounts, videos, titles)


async def delete_draft(
    session: AsyncSession, draft_id: int, user_id: int, allowed: set[str]
) -> dict[str, Any]:
    """软删自己的草稿。"""
    found = await get_draft_row(session, draft_id, user_id)
    if found is None:
        raise ApiError(404, "投放草稿不存在")
    row, *_rest = found
    _require_mode(row.charge_mode, allowed)
    row.mark_deleted()
    await session.commit()
    return {"id": str(row.id), "deleted": True}


def rule_item(
    row: DeliveryAutoRule,
    template: DeliveryTemplate,
    series_rows: list[SeriesBrief],
) -> dict[str, Any]:
    """把规则收成出参。"""
    return {
        "id": str(row.id),
        "name": row.name,
        "charge_mode": row.charge_mode,
        "template_id": str(template.id),
        "template_name": template.name,
        "ads_per_account": template.ads_per_account,
        "pitcher_user_id": str(row.pitcher_user_id),
        "accounts_per_series": row.accounts_per_series,
        "max_videos_per_series": row.max_videos_per_series,
        "schedule_start": None if row.schedule_start is None else beijing_iso(row.schedule_start),
        "schedule_end": None if row.schedule_end is None else beijing_iso(row.schedule_end),
        "cost_min": None if row.cost_min is None else _money(row.cost_min),
        "cost_max": None if row.cost_max is None else _money(row.cost_max),
        "roi_min": None if row.roi_min is None else _roi(row.roi_min),
        "roi_max": None if row.roi_max is None else _roi(row.roi_max),
        "publish_start": None if row.publish_start is None else row.publish_start.isoformat(),
        "publish_end": None if row.publish_end is None else row.publish_end.isoformat(),
        "no_bid_only": row.no_bid_only,
        "series": [{"id": str(series.id), "book_name": series.book_name} for series in series_rows],
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def rule_filters(query: RuleQuery, user_id: int) -> list[ColumnElement[bool]]:
    """规则列表：只看当前投手，收费模式精确。"""
    filters: list[ColumnElement[bool]] = [
        DeliveryAutoRule.is_deleted == 0,
        DeliveryAutoRule.pitcher_user_id == user_id,
        DeliveryAutoRule.charge_mode == query.charge_mode,
    ]
    name = (query.name or "").strip()
    if name:
        filters.append(DeliveryAutoRule.name.ilike(_like(name), escape="\\"))
    if query.template_id is not None:
        filters.append(DeliveryAutoRule.template_id == query.template_id)
    if query.series_id is not None:
        filters.append(rule_has_series(query.series_id))
    if query.no_bid_only is not None:
        filters.append(DeliveryAutoRule.no_bid_only.is_(query.no_bid_only))
    if query.scheduled is True:
        filters.append(DeliveryAutoRule.schedule_start.is_not(None))
    elif query.scheduled is False:
        filters.append(DeliveryAutoRule.schedule_start.is_(None))
    return filters


async def _rule_page(session: AsyncSession, rows: list[Any]) -> list[dict[str, Any]]:
    """给一页规则补上短剧。"""
    rule_ids = [row.id for row, _template in rows]
    series = await series_by_rules(session, rule_ids)
    return [rule_item(row, template, series.get(row.id, [])) for row, template in rows]


async def list_rules(session: AsyncSession, query: RuleQuery, user_id: int) -> dict[str, Any]:
    """分页列出当前投手自己的自动规则。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_rules(
        session, rule_filters(query, user_id), offset=params.offset, limit=params.page_size
    )
    return page_data(await _rule_page(session, rows), total, params)


async def get_rule(session: AsyncSession, rule_id: int, user_id: int, allowed: set[str]) -> dict[str, Any]:
    """取当前投手自己的一条规则。"""
    found = await get_rule_row(session, rule_id, user_id)
    if found is None:
        raise ApiError(404, "自动规则不存在")
    _require_mode(found[0].charge_mode, allowed)
    items = await _rule_page(session, [found])
    return items[0]


async def _rule_refs(
    session: AsyncSession, body: RuleWrite, allowed: set[str]
) -> tuple[DeliveryTemplate, list[SeriesBrief]]:
    """规则要挂的模板和短剧。模板的收费模式须在授权菜单里。"""
    found = await get_template_row(session, body.template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    template, _subject = found
    _require_mode(template.charge_mode, allowed)
    series_rows = _order(
        await get_series_by_ids(session, list(body.series_ids)),
        list(body.series_ids),
        lambda row: row.id,
    )
    if not series_rows:
        raise ApiError(404, "短剧不存在")
    return template, series_rows


def _fill_rule(row: DeliveryAutoRule, template: DeliveryTemplate, body: RuleWrite, user_id: int) -> None:
    """把校验过的字段写到规则行上。"""
    row.name = body.name
    row.charge_mode = template.charge_mode
    row.template_id = template.id
    row.pitcher_user_id = user_id
    row.accounts_per_series = body.accounts_per_series
    row.max_videos_per_series = body.max_videos_per_series
    row.schedule_start = body.schedule_start
    row.schedule_end = body.schedule_end
    row.cost_min = body.cost_min
    row.cost_max = body.cost_max
    row.roi_min = body.roi_min
    row.roi_max = body.roi_max
    row.publish_start = body.publish_start
    row.publish_end = body.publish_end
    row.no_bid_only = body.no_bid_only


async def create_rule(session: AsyncSession, body: RuleWrite, user_id: int, allowed: set[str]) -> dict[str, Any]:
    """新增一条自动规则。只保存，不执行。"""
    template, series_rows = await _rule_refs(session, body, allowed)
    if await rule_name_taken(session, user_id, template.charge_mode, body.name, None):
        raise ApiError(409, "规则名称已存在")
    row = DeliveryAutoRule(
        name=body.name,
        charge_mode=template.charge_mode,
        template_id=template.id,
        pitcher_user_id=user_id,
        accounts_per_series=body.accounts_per_series,
        max_videos_per_series=body.max_videos_per_series,
        schedule_start=body.schedule_start,
        schedule_end=body.schedule_end,
        cost_min=body.cost_min,
        cost_max=body.cost_max,
        roi_min=body.roi_min,
        roi_max=body.roi_max,
        publish_start=body.publish_start,
        publish_end=body.publish_end,
        no_bid_only=body.no_bid_only,
    )
    session.add(row)
    await session.flush()
    await replace_rule_series(session, row.id, series_rows)
    await session.commit()
    await session.refresh(row)
    return rule_item(row, template, series_rows)


async def update_rule(
    session: AsyncSession, rule_id: int, body: RuleWrite, user_id: int, allowed: set[str]
) -> dict[str, Any]:
    """整表保存自己的规则。收费模式必须和原来的一致。"""
    found = await get_rule_row(session, rule_id, user_id)
    if found is None:
        raise ApiError(404, "自动规则不存在")
    current, _template = found
    _require_mode(current.charge_mode, allowed)
    template, series_rows = await _rule_refs(session, body, allowed)
    if template.charge_mode != current.charge_mode:
        raise ApiError(400, "模板收费模式与规则不一致")
    if await rule_name_taken(session, user_id, template.charge_mode, body.name, current.id):
        raise ApiError(409, "规则名称已存在")
    _fill_rule(current, template, body, user_id)
    current.updated_date = beijing_now()
    await replace_rule_series(session, current.id, series_rows)
    await session.commit()
    await session.refresh(current)
    return rule_item(current, template, series_rows)


async def delete_rule(
    session: AsyncSession, rule_id: int, user_id: int, allowed: set[str]
) -> dict[str, Any]:
    """软删自己的规则。"""
    found = await get_rule_row(session, rule_id, user_id)
    if found is None:
        raise ApiError(404, "自动规则不存在")
    row, _template = found
    _require_mode(row.charge_mode, allowed)
    row.mark_deleted()
    await session.commit()
    return {"id": str(row.id), "deleted": True}
