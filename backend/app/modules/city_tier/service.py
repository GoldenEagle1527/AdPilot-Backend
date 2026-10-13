"""读出已入库的城市分级。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.city_tier.catalog import TIER_ORDER
from app.modules.city_tier.model import OceanCityTier


def group_city_tiers(rows: list[OceanCityTier]) -> dict[str, Any]:
    """按一线到五线分组。组内保持名单顺序。"""
    buckets: dict[str, list[dict[str, str]]] = {tier: [] for tier in TIER_ORDER}
    ordered = sorted(rows, key=lambda row: int(row.sort_order))
    for row in ordered:
        if row.tier not in buckets:
            continue
        buckets[row.tier].append({"ocean_code": row.ocean_code, "name": row.name})
    return {"items": [{"tier": tier, "cities": buckets[tier]} for tier in TIER_ORDER]}


async def list_city_tiers(session: AsyncSession) -> dict[str, Any]:
    """未删除的城市分级。"""
    rows = list(
        await session.scalars(select(OceanCityTier).where(OceanCityTier.is_deleted == 0))
    )
    return group_city_tiers(rows)
