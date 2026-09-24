"""在 backend/ 下执行：python scripts/seed_manhua_series.py

往脚本里写死的库插入漫剧演示数据。已有同一专辑 ID 和剧名则跳过。
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session, init_engine
from app.core.times import BEIJING
from app.modules.material.service import save_aweme_series

_STAMP = "%Y-%m-%d %H:%M:%S"
_POSTGRES = {
    "host": "192.168.111.40",
    "port": 5432,
    "database": "ad_pilot",
    "user": "root",
    "password": "ocsaas123456",
}


def _bind_database() -> None:
    """固定连到脚本里的库，不跟 deployment yaml 的 postgres 走。"""
    settings = get_settings()
    postgres = settings.postgres.model_copy(update=_POSTGRES)
    init_engine(settings.model_copy(update={"postgres": postgres}))


def _rows(now: datetime) -> list[dict]:
    """拼四条常读形态的演示短剧，覆盖 IAA/IAP、已发布和当天上架。"""
    today = now.strftime(_STAMP)
    earlier = "2026-09-01 09:00:00"
    return [
        {
            "thumb_url": "https://example.com/cover/xuanhuan.jpg",
            "book_id": 9100000001,
            "playlet_id": 9100000001,
            "book_name": "演示·玄幻逆袭",
            "episode_amount": 80,
            "gender": 1,
            "category_text": "玄幻脑洞,逆袭",
            "publish_status": 2,
            "publish_time": today,
            "estimate_publish_time": today,
            "permission_status": 1,
            "create_time": today,
            "douyin_nick_name": "演示剧场",
            "single_price": "0",
            "abstract": "演示数据：免费投放，页签为 IAA。",
            "delivery_status": True,
        },
        {
            "thumb_url": "https://example.com/cover/dushi.jpg",
            "book_id": 9100000002,
            "playlet_id": 9100000002,
            "book_name": "演示·都市神医",
            "episode_amount": 60,
            "gender": 1,
            "category_text": "都市,神医",
            "publish_status": 2,
            "publish_time": earlier,
            "estimate_publish_time": earlier,
            "permission_status": 1,
            "create_time": earlier,
            "douyin_nick_name": "演示剧场",
            "single_price": "9.9",
            "abstract": "演示数据：收费投放，页签为 IAP。",
            "delivery_status": True,
        },
        {
            "thumb_url": "https://example.com/cover/tianchong.jpg",
            "book_id": 9100000003,
            "playlet_id": 9100000003,
            "book_name": "演示·甜宠日常",
            "episode_amount": 40,
            "gender": 2,
            "category_text": "甜宠,日常",
            "publish_status": 1,
            "publish_time": "",
            "estimate_publish_time": today,
            "permission_status": 1,
            "create_time": earlier,
            "douyin_nick_name": "演示剧场",
            "single_price": "",
            "abstract": "演示数据：未发布，页签为 IAA。",
            "delivery_status": False,
        },
        {
            "thumb_url": "https://example.com/cover/xuanyi.jpg",
            "book_id": 9100000004,
            "playlet_id": 9100000004,
            "book_name": "演示·悬疑反转",
            "episode_amount": 24,
            "gender": 0,
            "category_text": "悬疑,反转",
            "publish_status": 3,
            "publish_time": earlier,
            "estimate_publish_time": earlier,
            "permission_status": 0,
            "create_time": earlier,
            "douyin_nick_name": "演示剧场",
            "single_price": "1",
            "abstract": "演示数据：已下架，页签为 IAP。",
            "delivery_status": False,
        },
    ]


async def load_demo() -> None:
    """把演示短剧写入脚本指定库的漫剧表。"""
    async for session in get_session():
        inserted = await save_aweme_series(session, _rows(datetime.now(BEIJING)))
        await session.commit()
        print(f"漫剧演示数据：新插入 {inserted} 条（已存在的专辑和剧名已跳过）")


def main() -> None:
    """命令行入口：连上脚本里的库并写入演示行。"""

    async def _run() -> None:
        try:
            _bind_database()
            await load_demo()
        finally:
            await dispose_engine()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
