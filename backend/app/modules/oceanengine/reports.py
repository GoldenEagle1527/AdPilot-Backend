"""自定义报表同步与快照读取。"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.times import beijing_now
from app.modules.account.model import AdvertiserAccount, OeReportSnapshot
from app.modules.oceanengine.runtime import (
    _PAGE_SIZE,
    _access_token,
    _app_for_live,
    _page_count,
    get_ocean_client,
)


async def list_reports(session: AsyncSession) -> list[dict[str, Any]]:
    """报表不分页。关闭 mock 时先拉当天自定义报表再读快照。"""
    if not get_settings().oceanengine.mock:
        await _sync_reports(session)
    return await _report_rows(session)


def _report_metric(raw: dict[str, Any], name: str) -> Any:
    metrics = raw.get("metrics")
    if isinstance(metrics, dict) and name in metrics:
        return metrics.get(name)
    return raw.get(name)


def _report_promotion_id(raw: dict[str, Any]) -> int | None:
    dimensions = raw.get("dimensions")
    if isinstance(dimensions, dict):
        value = dimensions.get("cdp_promotion_id") or dimensions.get("promotion_id")
        if value is not None and str(value).isdigit():
            return int(value)
    value = raw.get("promotion_id")
    if value is None:
        return None
    return int(value)


async def _sync_reports(session: AsyncSession) -> None:
    client = get_ocean_client()
    app = await _app_for_live(session)
    token = await _access_token(session, app)
    advertiser_ids = (
        await session.scalars(
            select(AdvertiserAccount.advertiser_id).where(
                AdvertiserAccount.oe_app_id == app.id,
                AdvertiserAccount.is_deleted == 0,
            )
        )
    ).all()
    now = beijing_now()
    day = now.strftime("%Y-%m-%d")
    rows: list[tuple[dict[str, Any], int]] = []
    for advertiser_id in advertiser_ids:
        page = 1
        while page < 10_000:
            body = await client.custom_report(
                token,
                {
                    "advertiser_id": int(advertiser_id),
                    "dimensions": json.dumps(["cdp_promotion_id"]),
                    "metrics": json.dumps(["stat_cost", "attribution_micro_game_0d_roi"]),
                    "filters": json.dumps([]),
                    "start_time": f"{day} 00:00:00",
                    "end_time": f"{day} 23:59:59",
                    "order_by": json.dumps([{"field": "stat_cost", "type": "DESC"}]),
                    "page": page,
                    "page_size": _PAGE_SIZE,
                },
            )
            data = body.get("data") or {}
            batch = data.get("rows") or data.get("list") or []
            if not isinstance(batch, list) or not batch:
                break
            for raw in batch:
                if isinstance(raw, dict):
                    rows.append((raw, int(advertiser_id)))
            if page >= _page_count(data, len(batch)):
                break
            page += 1
    for raw, advertiser_id in rows:
        promotion_id = _report_promotion_id(raw)
        if promotion_id is None:
            continue
        if raw.get("advertiser_id") is not None:
            advertiser_id = int(raw["advertiser_id"])
        stat_cost = Decimal(str(_report_metric(raw, "stat_cost") or 0)).quantize(Decimal("0.01"))
        roi = Decimal(str(_report_metric(raw, "attribution_micro_game_0d_roi") or 0)).quantize(
            Decimal("0.001")
        )
        found = await session.scalar(
            select(OeReportSnapshot).where(
                OeReportSnapshot.advertiser_id == advertiser_id,
                OeReportSnapshot.promotion_id == promotion_id,
            )
        )
        if found is None:
            session.add(
                OeReportSnapshot(
                    advertiser_id=advertiser_id,
                    promotion_id=promotion_id,
                    stat_cost=stat_cost,
                    attribution_micro_game_0d_roi=roi,
                    synced_at=now,
                    raw_payload=raw,
                )
            )
            continue
        found.stat_cost = stat_cost
        found.attribution_micro_game_0d_roi = roi
        found.synced_at = now
        found.raw_payload = raw
        found.is_deleted = 0
        found.deleted_at = None
    await session.flush()


async def _report_rows(session: AsyncSession) -> list[dict[str, Any]]:
    rows = await session.execute(
        select(
            OeReportSnapshot.promotion_id,
            OeReportSnapshot.stat_cost,
            OeReportSnapshot.attribution_micro_game_0d_roi,
            OeReportSnapshot.advertiser_id,
        )
        .where(OeReportSnapshot.is_deleted == 0)
        .order_by(OeReportSnapshot.promotion_id)
    )
    return [
        {
            "promotion_id": int(promotion_id),
            "stat_cost": float(stat_cost),
            "attribution_micro_game_0d_roi": float(roi),
            "advertiser_id": int(advertiser_id),
        }
        for promotion_id, stat_cost, roi, advertiser_id in rows.all()
    ]
