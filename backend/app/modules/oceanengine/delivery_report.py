"""报表页要读的小时快照：标准投放广告（BASIC_DATA）和全域项目（UNI_PROJECT_DATA）。

跟素材报表同一个每小时任务、同一套令牌。报表 GET 只读这两张表，不调巨量。
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.times import BEIJING, beijing_now
from app.modules.account.model import OeDeliveryReport, OeUniProjectReport
from app.modules.oceanengine.client import OceanEngineClient, OceanEngineError
from app.modules.oceanengine.material_report import (
    _auth_rejected,
    _count,
    _dimension,
    _load_pairs,
    _metric,
    _money,
    _ocean_id,
    _page_count,
    _refresh_report_tokens,
    _text,
)

logger = logging.getLogger(__name__)

_PAGE_SIZE = 100
_MAX_PAGES = 500
_LOOKBACK_DAYS = 8
_REQUEST_PAUSE_SECONDS = 0.2

BASIC_TOPIC = "BASIC_DATA"
BASIC_DIMENSIONS = [
    "stat_time_hour",
    "cdp_project_id",
    "cdp_project_name",
    "cdp_promotion_id",
    "cdp_promotion_name",
]
BASIC_MONEY = (
    "stat_cost",
    "stat_pay_amount",
    "attribution_game_in_app_ltv_1day",
    "attribution_game_in_app_ltv_8days",
    "attribution_micro_game_0d_ltv",
    "attribution_micro_game_7d_ltv",
)
BASIC_COUNTS = ("show_cnt", "click_cnt", "convert_cnt", "active")

UNI_TOPIC = "UNI_PROJECT_DATA"
UNI_DIMENSIONS = ["stat_time_hour", "cdp_project_id", "cdp_project_name"]
UNI_MONEY = (
    "all_stat_cost_trend",
    "all_stat_total_cost_trend",
    "all_gmv_trend",
    "all_billing_gmv_0day_trend",
    "all_billing_gmv_24h_trend",
    "all_billing_gmv_3days_trend",
    "all_income_trend",
    "all_income_0day_trend",
    "all_pay_amount_income_trend",
    "all_micro_game_income_trend",
)
UNI_RATIOS = ("all_roi_trend", "all_roi_24h_trend", "all_roi_0day_trend", "all_roi_3days_trend")
UNI_COUNTS = ("all_show_cnt_trend", "all_click_cnt_trend")


def pull_days(now: datetime) -> list[date]:
    """北京时间今天往前 8 个自然日，含今天。巨量只给近 8 天的小时粒度。"""
    end = now.astimezone(BEIJING).date()
    return [end - timedelta(days=offset) for offset in range(_LOOKBACK_DAYS - 1, -1, -1)]


def basic_row(raw: dict[str, Any], advertiser_id: int, synced_at: datetime) -> dict[str, Any] | None:
    """BASIC_DATA 一行收成表字段。缺小时、项目或广告 id 的丢掉。"""
    hour = _text(_dimension(raw, "stat_time_hour"))
    project_id = _ocean_id(_dimension(raw, "cdp_project_id"))
    promotion_id = _ocean_id(_dimension(raw, "cdp_promotion_id"))
    if not hour or project_id is None or promotion_id is None:
        return None
    row: dict[str, Any] = {
        "advertiser_id": int(advertiser_id),
        "stat_time_hour": hour[:64],
        "cdp_project_id": project_id,
        "cdp_project_name": _text(_dimension(raw, "cdp_project_name")),
        "cdp_promotion_id": promotion_id,
        "cdp_promotion_name": _text(_dimension(raw, "cdp_promotion_name")),
        "synced_at": synced_at,
        "created_date": synced_at,
        "updated_date": synced_at,
    }
    for name in BASIC_MONEY:
        row[name] = _money(_metric(raw, name))
    for name in BASIC_COUNTS:
        row[name] = _count(_metric(raw, name))
    return row


def uni_row(raw: dict[str, Any], advertiser_id: int, synced_at: datetime) -> dict[str, Any] | None:
    """UNI_PROJECT_DATA 一行收成表字段。缺小时或项目 id 的丢掉。"""
    hour = _text(_dimension(raw, "stat_time_hour"))
    project_id = _ocean_id(_dimension(raw, "cdp_project_id"))
    if not hour or project_id is None:
        return None
    row: dict[str, Any] = {
        "advertiser_id": int(advertiser_id),
        "stat_time_hour": hour[:64],
        "cdp_project_id": project_id,
        "cdp_project_name": _text(_dimension(raw, "cdp_project_name")),
        "synced_at": synced_at,
        "created_date": synced_at,
        "updated_date": synced_at,
    }
    for name in UNI_MONEY:
        row[name] = _money(_metric(raw, name))
    for name in UNI_RATIOS:
        row[name] = _ratio(_metric(raw, name))
    for name in UNI_COUNTS:
        row[name] = _count(_metric(raw, name))
    return row


def report_params(
    advertiser_id: int,
    topic: str,
    day: date,
    page: int,
    dimensions: list[str],
    metrics: list[str],
) -> dict[str, Any]:
    """一天一页的自定义报表请求参数。"""
    return {
        "advertiser_id": int(advertiser_id),
        "data_topic": topic,
        "dimensions": json.dumps(dimensions, ensure_ascii=False),
        "metrics": json.dumps(metrics, ensure_ascii=False),
        "filters": json.dumps([]),
        "start_time": f"{day.isoformat()} 00:00:00",
        "end_time": f"{day.isoformat()} 23:59:59",
        "order_by": json.dumps([{"field": metrics[0], "type": "DESC"}], ensure_ascii=False),
        "page": page,
        "page_size": _PAGE_SIZE,
    }


async def run_hourly_delivery_report(session: AsyncSession) -> int:
    """关闭 mock 时每小时调用。先续期，再拉近 8 天广告和全域项目小时数据。mock 时不打开放平台。"""
    if get_settings().oceanengine.mock:
        logger.info("投放报表跳过：mock")
        return 0
    await _refresh_report_tokens(session)
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60) as http:
        client = OceanEngineClient(settings.oceanengine, client=http)
        pairs = await _load_pairs(session)
        if not pairs:
            logger.info("投放报表跳过：没有可用访问令牌")
            await _rebuild(session)
            return 0
        written = 0
        for advertiser_id, token in pairs:
            written += await _pull_topic(
                session, client, advertiser_id, token, BASIC_TOPIC, BASIC_DIMENSIONS,
                [*BASIC_MONEY, *BASIC_COUNTS], basic_row, _upsert_basic,
            )
            written += await _pull_topic(
                session, client, advertiser_id, token, UNI_TOPIC, UNI_DIMENSIONS,
                [*UNI_MONEY, *UNI_RATIOS, *UNI_COUNTS], uni_row, _upsert_uni,
            )
        await _rebuild(session)
        return written


async def _rebuild(session: AsyncSession) -> None:
    """原始小时数落库之后，刷成列表直接读的日表。"""
    from app.modules.report.refresh import rebuild_serving

    await rebuild_serving(session, pull_days(beijing_now()))


async def _pull_topic(
    session: AsyncSession,
    client: OceanEngineClient,
    advertiser_id: int,
    token: str,
    topic: str,
    dimensions: list[str],
    metrics: list[str],
    to_row: Any,
    upsert: Any,
) -> int:
    written = 0
    for day in pull_days(beijing_now()):
        page = 1
        while page <= _MAX_PAGES:
            try:
                body = await client.custom_report(
                    token, report_params(advertiser_id, topic, day, page, dimensions, metrics)
                )
            except OceanEngineError as exc:
                message = str(exc)
                logger.info("投放报表读取失败 topic=%s advertiser=%s day=%s %s", topic, advertiser_id, day, message)
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
                for item in [to_row(raw, advertiser_id, synced_at)]
                if item is not None
            ]
            if rows:
                await upsert(session, rows)
                await session.commit()
                written += len(rows)
            if page >= _page_count(data, len(batch)):
                break
            page += 1
            await asyncio.sleep(_REQUEST_PAUSE_SECONDS)
        await asyncio.sleep(_REQUEST_PAUSE_SECONDS)
    return written


async def _upsert_basic(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    stmt = pg_insert(OeDeliveryReport).values(rows)
    excluded = stmt.excluded
    updates: dict[str, Any] = {
        "cdp_project_name": excluded.cdp_project_name,
        "cdp_promotion_name": excluded.cdp_promotion_name,
        "synced_at": excluded.synced_at,
        "updated_date": excluded.updated_date,
        "is_deleted": 0,
        "deleted_at": None,
    }
    for name in (*BASIC_MONEY, *BASIC_COUNTS):
        updates[name] = getattr(excluded, name)
    await session.execute(stmt.on_conflict_do_update(constraint="uq_oe_delivery_report_grain", set_=updates))


async def _upsert_uni(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    stmt = pg_insert(OeUniProjectReport).values(rows)
    excluded = stmt.excluded
    updates: dict[str, Any] = {
        "cdp_project_name": excluded.cdp_project_name,
        "synced_at": excluded.synced_at,
        "updated_date": excluded.updated_date,
        "is_deleted": 0,
        "deleted_at": None,
    }
    for name in (*UNI_MONEY, *UNI_RATIOS, *UNI_COUNTS):
        updates[name] = getattr(excluded, name)
    await session.execute(stmt.on_conflict_do_update(constraint="uq_oe_uni_project_report_grain", set_=updates))


def _ratio(value: Any) -> Decimal:
    text = _text(value)
    if text is None:
        return Decimal("0.0000")
    try:
        return Decimal(text.rstrip("%")).quantize(Decimal("0.0001"))
    except InvalidOperation:
        return Decimal("0.0000")
