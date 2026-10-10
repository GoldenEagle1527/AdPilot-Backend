"""近 30 天素材报表。只 GET 自定义报表，不走启动时装上的客户端。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.times import BEIJING, beijing_now
from app.modules.account.model import AdvertiserAccount, OeMaterialReport, OeToken
from app.modules.oceanengine.client import OceanEngineClient, OceanEngineError

logger = logging.getLogger(__name__)

_PAGE_SIZE = 100
_MAX_PAGES = 500
_LOOKBACK_DAYS = 30
_HOUR_WINDOW_DAYS = 8
_OCEAN_ID_MIN = 10**15
_REQUEST_PAUSE_SECONDS = 0.2
_DATA_TOPIC = "MATERIAL_DATA"
_DETAIL_DIMENSIONS = [
    "material_id",
    "ad_platform_material_name",
    "cdp_promotion_id",
    "cdp_promotion_name",
    "cdp_project_id",
    "cdp_project_name",
]
_ID_DETAIL_DIMENSIONS = ["material_id", "cdp_promotion_id", "cdp_project_id"]
_METRICS = [
    "stat_cost",
    "attribution_billing_game_in_app_ltv_1day",
    "stat_pay_amount",
    "show_cnt",
    "click_cnt",
    "convert_cnt",
    "active",
    "game_addiction",
]
_CORE_METRICS = [name for name in _METRICS if name != "game_addiction"]
_MONEY = ("stat_cost", "attribution_billing_game_in_app_ltv_1day", "stat_pay_amount")
_COUNTS = ("show_cnt", "click_cnt", "convert_cnt", "active", "game_addiction")


def dimensions_for(day: date, today: date, *, names: bool = True) -> list[str]:
    """近 8 天含今天用小时。更早的日期巨量不给素材小时，改用天。"""
    grain = "stat_time_hour" if 0 <= (today - day).days < _HOUR_WINDOW_DAYS else "stat_time_day"
    details = _DETAIL_DIMENSIONS if names else _ID_DETAIL_DIMENSIONS
    return [grain, *details]


def report_days(now: datetime) -> list[date]:
    """北京时间今天往前 30 个自然日，含今天。"""
    end = now.astimezone(BEIJING).date()
    start = end - timedelta(days=_LOOKBACK_DAYS - 1)
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def usable_access_token(token: str | None, expire_at: datetime | None, now: datetime) -> str | None:
    """空令牌、假令牌、已过期令牌都不能拿去读报表。不续期。"""
    text = (token or "").strip()
    if not text or text.startswith("mock-"):
        return None
    if expire_at is not None and expire_at <= now:
        return None
    return text


def pair_report_reads(
    advertisers: list[tuple[int, int]],
    tokens: dict[int, str],
) -> list[tuple[int, str]]:
    """广告主优先用自己应用的令牌。只有一把可用令牌时，才给没有令牌的真实广告主兜底。"""
    live = list(dict.fromkeys(tokens.values()))
    fallback = live[0] if len(live) == 1 else None
    pairs: list[tuple[int, str]] = []
    for advertiser_id, oe_app_id in advertisers:
        token = tokens.get(oe_app_id)
        if token is None and fallback is not None and int(advertiser_id) >= _OCEAN_ID_MIN:
            token = fallback
        if token is None:
            continue
        pairs.append((int(advertiser_id), token))
    return pairs


def row_from_report(raw: dict[str, Any], advertiser_id: int, synced_at: datetime) -> dict[str, Any] | None:
    """把自定义报表的一行收成表字段。缺主键维度的行丢掉。"""
    hour = _text(_dimension(raw, "stat_time_hour")) or _text(_dimension(raw, "stat_time_day"))
    material_id = _ocean_id(_dimension(raw, "material_id"))
    promotion_id = _ocean_id(_dimension(raw, "cdp_promotion_id") or _dimension(raw, "promotion_id"))
    project_id = _ocean_id(_dimension(raw, "cdp_project_id") or _dimension(raw, "project_id"))
    if not hour or material_id is None or promotion_id is None or project_id is None:
        return None
    return {
        "advertiser_id": int(advertiser_id),
        "stat_time_hour": hour[:64],
        "material_id": material_id,
        "ad_platform_material_name": _text(_dimension(raw, "ad_platform_material_name")),
        "cdp_promotion_id": promotion_id,
        "cdp_promotion_name": _text(_dimension(raw, "cdp_promotion_name")),
        "cdp_project_id": project_id,
        "cdp_project_name": _text(_dimension(raw, "cdp_project_name")),
        "stat_cost": _money(_metric(raw, "stat_cost")),
        "attribution_billing_game_in_app_ltv_1day": _money(
            _metric(raw, "attribution_billing_game_in_app_ltv_1day")
        ),
        "stat_pay_amount": _money(_metric(raw, "stat_pay_amount")),
        "show_cnt": _count(_metric(raw, "show_cnt")),
        "click_cnt": _count(_metric(raw, "click_cnt")),
        "convert_cnt": _count(_metric(raw, "convert_cnt")),
        "active": _count(_metric(raw, "active")),
        "game_addiction": _count(_metric(raw, "game_addiction")),
        "synced_at": synced_at,
        "created_date": synced_at,
        "updated_date": synced_at,
    }


async def pull_material_report_30d(session: AsyncSession) -> int:
    """用真客户端拉近 30 天。没有可用令牌、回包为空、或客户端不是真读客户端时不写行。"""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60) as http:
        client = OceanEngineClient(settings.oceanengine, client=http)
        if type(client).__name__ != "OceanEngineClient":
            logger.info("素材报表跳过：不是真读客户端")
            return 0
        pairs = await _load_pairs(session)
        if not pairs:
            logger.info("素材报表跳过：没有可用访问令牌")
            return 0
        written = 0
        for advertiser_id, token in pairs:
            written += await _pull_advertiser(session, client, advertiser_id, token)
        return written


async def _load_pairs(session: AsyncSession) -> list[tuple[int, str]]:
    now = beijing_now()
    token_rows = (
        await session.execute(
            select(OeToken.oe_app_id, OeToken.access_token, OeToken.access_expire_at).where(
                OeToken.is_deleted == 0
            )
        )
    ).all()
    tokens: dict[int, str] = {}
    for oe_app_id, access_token, expire_at in token_rows:
        usable = usable_access_token(access_token, expire_at, now)
        if usable is not None:
            tokens[int(oe_app_id)] = usable
    advertisers = (
        await session.execute(
            select(AdvertiserAccount.advertiser_id, AdvertiserAccount.oe_app_id).where(
                AdvertiserAccount.is_deleted == 0
            )
        )
    ).all()
    return pair_report_reads([(int(advertiser_id), int(oe_app_id)) for advertiser_id, oe_app_id in advertisers], tokens)


async def _pull_advertiser(
    session: AsyncSession,
    client: OceanEngineClient,
    advertiser_id: int,
    token: str,
) -> int:
    written = 0
    metrics = list(_METRICS)
    use_names = True
    today = beijing_now().astimezone(BEIJING).date()
    for day in report_days(beijing_now()):
        page = 1
        while page <= _MAX_PAGES:
            dimensions = dimensions_for(day, today, names=use_names)
            try:
                body = await client.custom_report(
                    token,
                    _params(advertiser_id, day, page, dimensions, metrics),
                )
            except OceanEngineError as exc:
                message = str(exc)
                if page == 1 and use_names and _shape_rejected(message):
                    use_names = False
                    metrics = list(_CORE_METRICS)
                    logger.info("素材报表改用 id 维度后重试 advertiser=%s day=%s", advertiser_id, day)
                    continue
                logger.info("素材报表读取失败 advertiser=%s day=%s %s", advertiser_id, day, message)
                if _auth_rejected(message):
                    return written
                break
            data = body.get("data") or {}
            batch = data.get("rows") or data.get("list") or []
            if not isinstance(batch, list) or not batch:
                break
            synced_at = beijing_now()
            rows = [
                item
                for raw in batch
                if isinstance(raw, dict)
                for item in [row_from_report(raw, advertiser_id, synced_at)]
                if item is not None
            ]
            if rows:
                await _upsert(session, rows)
                await session.commit()
                written += len(rows)
            if page >= _page_count(data, len(batch)):
                break
            page += 1
            await asyncio.sleep(_REQUEST_PAUSE_SECONDS)
        await asyncio.sleep(_REQUEST_PAUSE_SECONDS)
    return written


def _params(
    advertiser_id: int,
    day: date,
    page: int,
    dimensions: list[str],
    metrics: list[str],
) -> dict[str, Any]:
    return {
        "advertiser_id": int(advertiser_id),
        "data_topic": _DATA_TOPIC,
        "dimensions": json.dumps(dimensions, ensure_ascii=False),
        "metrics": json.dumps(metrics, ensure_ascii=False),
        "filters": json.dumps([]),
        "start_time": f"{day.isoformat()} 00:00:00",
        "end_time": f"{day.isoformat()} 23:59:59",
        "order_by": json.dumps([{"field": "stat_cost", "type": "DESC"}], ensure_ascii=False),
        "page": page,
        "page_size": _PAGE_SIZE,
    }


def _shape_rejected(message: str) -> bool:
    return any(word in message for word in ("维度", "指标", "不支持", "data_topic"))


def _auth_rejected(message: str) -> bool:
    return any(word in message for word in ("access_token", "权限", "40102", "40105", "未登录"))


def _page_count(data: dict[str, Any], batch_size: int) -> int:
    page_info = data.get("page_info") or {}
    total = page_info.get("total_page")
    if total is not None:
        return max(int(total), 1)
    if batch_size < _PAGE_SIZE:
        return 1
    return _MAX_PAGES


async def _upsert(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    stmt = pg_insert(OeMaterialReport).values(rows)
    excluded = stmt.excluded
    updates = {
        "ad_platform_material_name": excluded.ad_platform_material_name,
        "cdp_promotion_name": excluded.cdp_promotion_name,
        "cdp_project_name": excluded.cdp_project_name,
        "synced_at": excluded.synced_at,
        "updated_date": excluded.updated_date,
        "is_deleted": 0,
        "deleted_at": None,
    }
    for name in (*_MONEY, *_COUNTS):
        updates[name] = getattr(excluded, name)
    stmt = stmt.on_conflict_do_update(constraint="uq_oe_material_report_grain", set_=updates)
    await session.execute(stmt)


def _dimension(raw: dict[str, Any], name: str) -> Any:
    dimensions = raw.get("dimensions")
    if isinstance(dimensions, dict) and name in dimensions:
        return dimensions.get(name)
    return raw.get(name)


def _metric(raw: dict[str, Any], name: str) -> Any:
    metrics = raw.get("metrics")
    if isinstance(metrics, dict) and name in metrics:
        return metrics.get(name)
    return raw.get(name)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    return text


def _ocean_id(value: Any) -> int | None:
    text = _text(value)
    if text is None or not text.isdigit():
        return None
    return int(text)


def _money(value: Any) -> Decimal:
    text = _text(value)
    if text is None:
        return Decimal("0.00")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def _count(value: Any) -> int:
    text = _text(value)
    if text is None:
        return 0
    try:
        return int(Decimal(text))
    except InvalidOperation:
        return 0
