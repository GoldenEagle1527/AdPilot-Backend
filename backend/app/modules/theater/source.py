"""三方剧场自己的推广链样本。

采集到点后从这里按 book_id 取付费、免费各一条，再写入推广链表。
样本可以是假数据。这里不发番茄、常读或巨量 HTTP。
"""

from __future__ import annotations

from typing import Any


def _item(promotion_id: int, media_config_type: int) -> dict[str, Any]:
    """一条剧场样本。付费墙 2 是付费，3 是免费。"""
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


def promotions_for_book(book_id: int) -> list[dict[str, Any]]:
    """按 book_id 给出付费、免费各一条。同一本书每次一样。"""
    base = int(book_id) * 10
    return [_item(base + 2, 2), _item(base + 3, 3)]
