"""巨量广告账户列表。效果数从素材小时表加总，余额再向巨量查一次。"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.modules.account.model import (
    AdvertiserAccount,
    DeliverySubject,
    OeMaterialReport,
    OeProject,
    OePromotion,
)
from app.modules.ocean_ads.schema import AccountQuery
from app.modules.oceanengine.client import OceanEngineError
from app.modules.oceanengine.runtime import _access_token, get_ocean_client
from app.modules.system_admin.domain.models import UserTag, UserTagLink
from app.modules.system_admin.domain.scope import DataScope, owner_match, resolve_data_scope

_PITCHER_TAG = "短剧投手"
_BALANCE_BATCH = 50
_MONEY = Decimal("0.01")
_TWO = Decimal("0.01")


def _money(value: Decimal) -> str:
    """金额保留两位小数。"""
    return format(value.quantize(_MONEY), "f")


def _rate(numerator: Decimal, denominator: Decimal) -> str:
    """分子除分母，保留两位，四舍五入。分母是 0 时产品要求直接展示 0。不乘 1000。"""
    if denominator == 0:
        return "0.00"
    return format((numerator / denominator).quantize(_TWO, rounding=ROUND_HALF_UP), "f")


def effect_numbers(
    cost: Decimal,
    today: Decimal,
    total: Decimal,
    shows: int,
    clicks: int,
    converts: int,
    actives: int,
) -> dict[str, Any]:
    """比率按产品确认：千次费用不乘 1000，转化率按百分数，其余是分子除分母。"""
    show_dec = Decimal(shows)
    click_dec = Decimal(clicks)
    convert_dec = Decimal(converts)
    active_dec = Decimal(actives)
    return {
        "stat_cost": _money(cost),
        "revenue_today": _money(today),
        "revenue_total": _money(total),
        "revenue_today_rate": _rate(today, cost),
        "revenue_total_rate": _rate(total, cost),
        "show_cnt": shows,
        "cpm": _rate(cost, show_dec),
        "click_cnt": clicks,
        "ctr": _rate(click_dec, show_dec),
        "cpc": _rate(cost, click_dec),
        "convert_cnt": converts,
        "convert_cost": _rate(cost, convert_dec),
        "convert_rate": _rate(convert_dec * 100, click_dec),
        "active": actives,
        "recycle_amount": _money(total),
        "active_arpu": _rate(total, active_dec),
        "active_cost": _rate(cost, active_dec),
    }


def _display_name(name: str, local_name: str | None) -> str:
    """中台展示名优先，空则用巨量账户名。"""
    local = (local_name or "").strip()
    return local or name


async def _require_pitcher(session: AsyncSession, user_id: int) -> None:
    """下拉来源是打了短剧投手标签的用户。没这个标签就拒绝。"""
    found = await session.scalar(
        select(UserTagLink.user_id)
        .join(UserTag, UserTag.id == UserTagLink.tag_id)
        .where(UserTagLink.user_id == user_id, UserTag.name == _PITCHER_TAG)
    )
    if found is None:
        raise ApiError(400, "投手不存在")


def _account_filters(query: AccountQuery, user_id: int, scope: DataScope) -> list[ColumnElement[bool]]:
    """当前登录人能看的户，再叠加页签、账户和投手。"""
    filters: list[ColumnElement[bool]] = [
        AdvertiserAccount.is_deleted == 0,
        AdvertiserAccount.sync_status == "active",
        owner_match(AdvertiserAccount.pitcher_user_id, user_id, scope),
    ]
    if query.delivery_kind is not None or query.charge_mode is not None:
        filters.append(_matches_kind(query))
    if query.account_id is not None:
        filters.append(AdvertiserAccount.advertiser_id == query.account_id)
    if query.pitcher_user_id is not None:
        filters.append(AdvertiserAccount.pitcher_user_id == query.pitcher_user_id)
    name = (query.account_name or "").strip()
    if name:
        pattern = f"%{name.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%"
        filters.append(
            or_(
                AdvertiserAccount.name.ilike(pattern, escape="\\"),
                AdvertiserAccount.local_name.ilike(pattern, escape="\\"),
            )
        )
    return filters


def _matches_kind(query: AccountQuery) -> ColumnElement[bool]:
    """3.5.1：按广告到 oe_promotion，取广告所属项目挂的主体。主体上才有 standard/uni 和 IAA/IAP。"""
    conditions = [
        OePromotion.advertiser_id == AdvertiserAccount.advertiser_id,
        OePromotion.is_deleted == 0,
        OeProject.ocean_project_id == OePromotion.ocean_project_id,
        OeProject.is_deleted == 0,
        OeProject.subject_id == DeliverySubject.id,
        DeliverySubject.is_deleted == 0,
    ]
    if query.delivery_kind is not None:
        conditions.append(DeliverySubject.delivery_mode == query.delivery_kind)
    if query.charge_mode is not None:
        conditions.append(DeliverySubject.charge_mode == query.charge_mode)
    return select(OePromotion.id).where(*conditions).exists()


def _report_filters(query: AccountQuery) -> list[ColumnElement[bool]]:
    """同一页签下，把日期范围内的小时行加总。日期取时间字符串的前 10 位。"""
    day_text = func.substr(OeMaterialReport.stat_time_hour, 1, 10)
    filters: list[ColumnElement[bool]] = [
        OePromotion.is_deleted == 0,
        OeProject.is_deleted == 0,
        DeliverySubject.is_deleted == 0,
    ]
    if query.delivery_kind is not None:
        filters.append(DeliverySubject.delivery_mode == query.delivery_kind)
    if query.charge_mode is not None:
        filters.append(DeliverySubject.charge_mode == query.charge_mode)
    if query.date_start is not None and query.date_end is not None:
        filters.append(day_text >= query.date_start.isoformat())
        filters.append(day_text <= query.date_end.isoformat())
    return filters


def metrics_statement(advertiser_ids: list[int], query: AccountQuery) -> Select:
    """素材行用账户 id 加广告 id 对上 oe_promotion，再经广告所属项目取主体。对不上广告表的行不算。"""
    return (
        select(
            OeMaterialReport.advertiser_id,
            func.coalesce(func.sum(OeMaterialReport.stat_cost), 0),
            func.coalesce(func.sum(OeMaterialReport.attribution_billing_game_in_app_ltv_1day), 0),
            func.coalesce(func.sum(OeMaterialReport.stat_pay_amount), 0),
            func.coalesce(func.sum(OeMaterialReport.show_cnt), 0),
            func.coalesce(func.sum(OeMaterialReport.click_cnt), 0),
        )
        .join(
            OePromotion,
            and_(
                OePromotion.advertiser_id == OeMaterialReport.advertiser_id,
                OePromotion.promotion_id == OeMaterialReport.cdp_promotion_id,
            ),
        )
        .join(OeProject, OeProject.ocean_project_id == OePromotion.ocean_project_id)
        .join(DeliverySubject, OeProject.subject_id == DeliverySubject.id)
        .where(OeMaterialReport.advertiser_id.in_(advertiser_ids), *_report_filters(query))
        .group_by(OeMaterialReport.advertiser_id)
    )


async def _metrics(
    session: AsyncSession, advertiser_ids: list[int], query: AccountQuery
) -> dict[int, Any]:
    """按账户加总。没有报表行的账户不在结果里。"""
    if not advertiser_ids:
        return {}
    rows = await session.execute(metrics_statement(advertiser_ids, query))
    return {int(advertiser_id): row for advertiser_id, *row in rows.all()}


def _item(account: AdvertiserAccount, metric: Any, balance: Decimal | None) -> dict[str, Any]:
    """一行。余额只用这次向巨量查到的数，查不到就空。"""
    cost = Decimal(metric[0]) if metric is not None else Decimal(0)
    today = Decimal(metric[1]) if metric is not None else Decimal(0)
    total = Decimal(metric[2]) if metric is not None else Decimal(0)
    shows = int(metric[3]) if metric is not None else 0
    clicks = int(metric[4]) if metric is not None else 0
    show_dec = Decimal(shows)
    click_dec = Decimal(clicks)
    return {
        "account_id": int(account.advertiser_id),
        "account_name": _display_name(account.name, account.local_name),
        "balance": None if balance is None else _money(balance),
        "stat_cost": _money(cost),
        "revenue_today": _money(today),
        "revenue_total": _money(total),
        "revenue_today_rate": _rate(today, cost),
        "revenue_total_rate": _rate(total, cost),
        "show_cnt": shows,
        "cpm": _rate(cost, show_dec),
        "click_cnt": clicks,
        "ctr": _rate(click_dec, show_dec),
        "cpc": _rate(cost, click_dec),
    }


def _sort_key(row: dict[str, Any], name: str) -> tuple:
    """空比率排在后面。数字按大小排。"""
    value = row[name]
    if value is None:
        return (1, Decimal(0))
    if name in ("show_cnt", "click_cnt", "account_id"):
        return (0, int(value))
    return (0, Decimal(value))


def _balance_amount(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return None


async def _live_balances(session: AsyncSession, advertiser_ids: list[int]) -> dict[int, Decimal]:
    """3.5.2：打开页面后批量查余额。account_type=AD，一次最多 50 个。失败的户不在结果里。"""
    if not advertiser_ids:
        return {}
    try:
        client = get_ocean_client()
        token = await _access_token(session)
    except (ApiError, OceanEngineError):
        return {}
    found: dict[int, Decimal] = {}
    for start in range(0, len(advertiser_ids), _BALANCE_BATCH):
        chunk = advertiser_ids[start : start + _BALANCE_BATCH]
        try:
            body = await client.account_fund_get(token, chunk)
        except (ApiError, OceanEngineError):
            continue
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict):
            continue
        for item in data.get("list") or []:
            if not isinstance(item, dict) or item.get("account_id") is None:
                continue
            amount = _balance_amount(item.get("valid_balance"))
            if amount is None:
                continue
            found[int(item["account_id"])] = amount
    return found


async def list_accounts(
    session: AsyncSession, query: AccountQuery, principal: dict[str, Any]
) -> dict[str, Any]:
    """账户页。传入的 account_id 必须落在当前登录人的数据范围内，否则这一页是空的。"""
    if query.pitcher_user_id is not None:
        await _require_pitcher(session, query.pitcher_user_id)
    scope = await resolve_data_scope(session, principal)
    user_id = int(principal["id"])
    accounts = list(
        await session.scalars(select(AdvertiserAccount).where(*_account_filters(query, user_id, scope)))
    )
    advertiser_ids = [int(row.advertiser_id) for row in accounts]
    metrics = await _metrics(session, advertiser_ids, query)
    balances = await _live_balances(session, advertiser_ids)
    rows = []
    for account in accounts:
        advertiser_id = int(account.advertiser_id)
        rows.append(_item(account, metrics.get(advertiser_id), balances.get(advertiser_id)))
    rows.sort(key=lambda row: _sort_key(row, query.sort_by), reverse=query.sort_order == "desc")
    params = PageParams(page=query.page, page_size=query.page_size)
    page_rows = rows[params.offset : params.offset + params.page_size]
    return page_data(page_rows, len(rows), params)
