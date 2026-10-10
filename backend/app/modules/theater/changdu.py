"""常读推广链收成推广链表字段，并按短剧页签过滤。拉取在 app.clients.changdu。"""

from __future__ import annotations

from typing import Any

from app.core.times import parse_beijing_stamp
from app.modules.theater.model import DeliveryMode

# 剧库 tab_text 对常读 media_config.media_config_type：2 付费短剧、3 免费短剧
MEDIA_CONFIG_TYPES = {DeliveryMode.IAP: 2, DeliveryMode.IAA: 3}
DELIVERY_MODE_BY_MEDIA = {2: DeliveryMode.IAP, 3: DeliveryMode.IAA}


def matches_tab(item: dict[str, Any], tab_text: str) -> bool:
    """推广链付费墙类型和短剧页签一致：IAP 要 2，IAA 要 3。"""
    media_config = item.get("media_config") or {}
    return media_config.get("media_config_type") == MEDIA_CONFIG_TYPES.get(tab_text)


def link_matches(item: dict[str, Any], *, charge_filter: str | None, tab_text: str) -> bool:
    """手动采集按所选付费类型过滤。全部接受付费 2 和免费 3；没选则跟短剧页签。"""
    if charge_filter == "all":
        media = (item.get("media_config") or {}).get("media_config_type")
        return media in (2, 3)
    if charge_filter in MEDIA_CONFIG_TYPES:
        return matches_tab(item, charge_filter)
    return matches_tab(item, tab_text)


def promotion_fields(item: dict[str, Any]) -> dict[str, Any]:
    """把常读一条推广链收成推广链表字段。剧场、短剧、任务由调用方补。"""
    info = item.get("promotion_info") or {}     
    delivery = item.get("delivery") or {}
    book = item.get("book_info") or {}
    media_config = item.get("media_config") or {}
    package = item.get("package") or {}
    return {
        "promotion_id": int(info["promotion_id"]),
        "promotion_url": info.get("promotion_url") or "",
        "recharge_template_name": delivery.get("recharge_template_name") or "",
        "media_config_type": int(media_config.get("media_config_type") or 0),
        "publish_time": parse_beijing_stamp(book.get("publish_time")),
        "promotion_create_time": parse_beijing_stamp(info.get("create_time")),
        "package_app_key": package.get("app_key") or "",
    }
