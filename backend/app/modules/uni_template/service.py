"""全域模板的保存、列表，以及投手自己的抖音号分配。

模板全员可见。分配只改当前投手的行。不创建全域投放任务。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_iso, beijing_now
from app.modules.account.model import DeliverySubject, DouyinAccount
from app.modules.standard_delivery.crud import get_subject
from app.modules.standard_delivery.model import DeliveryTemplate, TemplateMode
from app.modules.uni_template.crud import (
    douyin_by_ids,
    get_uni_template_row,
    page_uni_templates,
    pitcher_douyin_links,
    pitcher_owned_ids,
    replace_pitcher_douyin,
    uni_name_taken,
    DouyinLink,
)
from app.modules.uni_template.schema import DouyinAssignWrite, TemplateQuery, TemplateWrite


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


def douyin_item(row: DouyinAccount) -> dict[str, Any]:
    """把抖音号收成出参。"""
    return {"id": str(row.id), "aweme_id": row.aweme_id, "name": row.name}


def template_item(
    row: DeliveryTemplate, subject_name: str, accounts: list[dict[str, Any]]
) -> dict[str, Any]:
    """把全域模板收成出参。抖音号由调用方按当前投手准备。"""
    budget = row.project_budget if row.project_budget is not None else Decimal("0")
    roi = row.roi_coefficient if row.roi_coefficient is not None else Decimal("0")
    return {
        "id": str(row.id),
        "name": row.name,
        "subject_id": str(row.subject_id),
        "subject_name": subject_name,
        "charge_mode": row.charge_mode,
        "project_budget": _money(budget),
        "roi_coefficient": _roi(roi),
        "aigc_dynamic_creative": bool(row.aigc_dynamic_creative),
        "title_select_mode": row.title_select_mode or "",
        "douyin_accounts": accounts,
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def _group(links: list[DouyinLink]) -> dict[int, list[dict[str, Any]]]:
    """按模板 id 归并当前投手的抖音号，保留查询顺序。"""
    grouped: dict[int, list[dict[str, Any]]] = {}
    for template_id, account in links:
        grouped.setdefault(template_id, []).append(douyin_item(account))
    return grouped


def template_filters(query: TemplateQuery) -> list[ColumnElement[bool]]:
    """全域模板列表：未删除，只要全域，名称模糊，主体和变现模式精确。不按投手过滤。"""
    filters: list[ColumnElement[bool]] = [
        DeliveryTemplate.is_deleted == 0,
        DeliveryTemplate.delivery_mode == TemplateMode.UNI,
    ]
    name = (query.name or "").strip()
    if name:
        filters.append(DeliveryTemplate.name.ilike(_like(name), escape="\\"))
    if query.subject_id is not None:
        filters.append(DeliveryTemplate.subject_id == query.subject_id)
    if query.charge_mode is not None:
        filters.append(DeliveryTemplate.charge_mode == query.charge_mode)
    return filters


def _clear_standard_only(row: DeliveryTemplate) -> None:
    """全域行不写标准提交列。这些列和 delivery_mode 不是一回事。"""
    row.ocean_delivery_mode = None
    row.bid_type = None
    row.schedule_type = None
    row.schedule_start_date = None
    row.schedule_end_date = None
    row.schedule_time = None
    row.ad_source = None
    row.product_name = None
    row.selling_points = []
    row.call_to_action_buttons = []
    row.roi_goal = None
    row.videos_per_ad = None
    row.titles_per_ad = None
    row.placement = None
    row.district = None
    row.city_codes = None
    row.product_library_id = None
    row.library_kind = None
    row.product_select = None
    row.material_boost = None
    row.promotion_operation = None
    row.douyin_account_id = None
    row.product_image_id = None
    row.standard_title_select_mode = None


def require_uni_subject(subject: DeliverySubject, charge_mode: str) -> None:
    """模板只能挂全域投放、且变现模式相同的主体。"""
    if subject.delivery_mode != TemplateMode.UNI:
        raise ApiError(400, "主体不是全域投放")
    if subject.charge_mode != charge_mode:
        raise ApiError(400, "主体收费模式与模板不一致")


async def _require_subject(session: AsyncSession, subject_id: int, charge_mode: str) -> DeliverySubject:
    """主体须存在，且是同变现模式的全域主体。"""
    subject = await get_subject(session, subject_id)
    if subject is None:
        raise ApiError(404, "主体不存在")
    require_uni_subject(subject, charge_mode)
    return subject


async def list_templates(session: AsyncSession, query: TemplateQuery, user_id: int) -> dict[str, Any]:
    """分页列出未删除的全域模板，并带上当前投手自己的抖音号。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_uni_templates(
        session, template_filters(query), offset=params.offset, limit=params.page_size
    )
    links = await pitcher_douyin_links(session, [row.id for row, _subject in rows], user_id)
    grouped = _group(links)
    items = [template_item(row, subject.name, grouped.get(row.id, [])) for row, subject in rows]
    return page_data(items, total, params)


async def get_template(session: AsyncSession, template_id: int, user_id: int) -> dict[str, Any]:
    """取一条全域模板。别人的抖音号不出现。"""
    found = await get_uni_template_row(session, template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    row, subject = found
    links = await pitcher_douyin_links(session, [row.id], user_id)
    return template_item(row, subject.name, _group(links).get(row.id, []))


async def create_template(session: AsyncSession, body: TemplateWrite) -> dict[str, Any]:
    """校验主体后新增全域模板。新建时还没有抖音号分配。"""
    subject = await _require_subject(session, body.subject_id, body.charge_mode)
    if await uni_name_taken(session, body.charge_mode, body.name, None):
        raise ApiError(409, "模板名称已存在")
    row = DeliveryTemplate(
        name=body.name,
        delivery_mode=TemplateMode.UNI,
        charge_mode=body.charge_mode,
        subject_id=subject.id,
        bid_panels=[],
        ads_per_account=None,
        project_budget=body.project_budget,
        roi_coefficient=body.roi_coefficient,
        aigc_dynamic_creative=body.aigc_dynamic_creative,
        title_select_mode=body.title_select_mode,
    )
    _clear_standard_only(row)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return template_item(row, subject.name, [])


async def update_template(
    session: AsyncSession, template_id: int, body: TemplateWrite, user_id: int
) -> dict[str, Any]:
    """整表保存。不改当前投手或其他投手的抖音号分配。"""
    found = await get_uni_template_row(session, template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    row, _current = found
    subject = await _require_subject(session, body.subject_id, body.charge_mode)
    if await uni_name_taken(session, body.charge_mode, body.name, row.id):
        raise ApiError(409, "模板名称已存在")
    row.name = body.name
    row.charge_mode = body.charge_mode
    row.subject_id = subject.id
    row.project_budget = body.project_budget
    row.roi_coefficient = body.roi_coefficient
    row.aigc_dynamic_creative = body.aigc_dynamic_creative
    row.title_select_mode = body.title_select_mode
    row.bid_panels = []
    row.ads_per_account = None
    _clear_standard_only(row)
    row.updated_date = beijing_now()
    await session.commit()
    await session.refresh(row)
    links = await pitcher_douyin_links(session, [row.id], user_id)
    return template_item(row, subject.name, _group(links).get(row.id, []))


async def delete_template(session: AsyncSession, template_id: int) -> dict[str, Any]:
    """软删全域模板。标准模板 id 视为不存在。"""
    found = await get_uni_template_row(session, template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    row, _subject = found
    row.mark_deleted()
    await session.commit()
    return {"id": str(row.id), "deleted": True}


async def _require_own_uni_accounts(
    session: AsyncSession, account_ids: list[int], user_id: int
) -> list[DouyinAccount]:
    """这批号都须未删除、是全域，且已分给当前投手。顺序跟请求一致。"""
    if not account_ids:
        return []
    found = {row.id: row for row in await douyin_by_ids(session, account_ids)}
    if any(item not in found for item in account_ids):
        raise ApiError(404, "抖音号不存在")
    if any(found[item].delivery_mode != "uni" for item in account_ids):
        raise ApiError(400, "只能分配全域抖音号")
    owned = await pitcher_owned_ids(session, account_ids, user_id)
    if any(item not in owned for item in account_ids):
        raise ApiError(400, "抖音号未分配给当前投手")
    return [found[item] for item in account_ids]


async def assign_douyin(
    session: AsyncSession, template_id: int, body: DouyinAssignWrite, user_id: int
) -> dict[str, Any]:
    """替换当前投手在这条全域模板上的抖音号。空列表表示清空。"""
    found = await get_uni_template_row(session, template_id)
    if found is None:
        raise ApiError(404, "模板不存在")
    accounts = await _require_own_uni_accounts(session, list(body.douyin_account_ids), user_id)
    await replace_pitcher_douyin(session, template_id, user_id, [row.id for row in accounts])
    await session.commit()
    return {"template_id": str(template_id), "douyin_accounts": [douyin_item(row) for row in accounts]}
