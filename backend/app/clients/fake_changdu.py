"""常读假客户端。只在 oceanengine.mock 为真时由 changdu_factory 选用。业务模块不要 import。"""

from __future__ import annotations

from typing import Any


def _item(promotion_id: int, media_config_type: int) -> dict[str, Any]:
    """一条本地推广链。付费墙 2 是付费，3 是免费。"""
    return {
        "promotion_info": {
            "promotion_id": promotion_id,
            "promotion_url": f"https://mock.local/p/{promotion_id}",
            "create_time": "2026-10-10 12:00:00",
        },
        "book_info": {
            "book_id": promotion_id,
            "book_name": "mock",
            "publish_time": "2026-10-10 08:00:00",
        },
        "delivery": {"recharge_template_name": "中额" if media_config_type == 2 else "IAA"},
        "media_config": {"media_config_type": media_config_type},
        "package": {"app_key": "mock"},
    }


class FakeChangduClient:
    """按 book_id 返回付费、免费各一条。不发 HTTP。"""

    async def list_promotions(self, book_id: int, *, ts: int | None = None) -> list[dict[str, Any]]:
        """推广链 id 由 book_id 推出来，同一本书每次一样。"""
        base = int(book_id) * 10
        return [_item(base + 2, 2), _item(base + 3, 3)]
