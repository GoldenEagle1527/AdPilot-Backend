"""在 backend/ 下执行：python scripts/seed_manhua_series.py

按 deployment/dev.yaml（不设 ADPILOT_ENV 时即 dev）往漫剧表插入演示行。
同一演示 book_id 已有未删除行则跳过，可重复执行。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session, init_engine
from app.core.times import beijing_now, parse_beijing_stamp
from app.modules.material.model import ManhuaSeries

# 固定 book_id，重复执行时按这列跳过。名称都以「演示」开头。
_ROWS: tuple[dict[str, object], ...] = (
    {
        "book_id": 9100000001,
        "playlet_id": 9100000001,
        "book_name": "演示·玄幻逆袭",
        "tab_text": "IAA",
        "category_text": "玄幻脑洞,逆袭",
        "single_price": "0",
        "episode_amount": 80,
        "gender": 1,
        "publish_status": 2,
        "publish_time": "2026-10-09 10:00:00",
        "estimate_publish_time": "2026-10-09 10:00:00",
        "permission_status": 1,
        "create_time": "2026-10-01 09:00:00",
        "delivery_status": True,
        "abstract": "演示数据：免费投放，页签为 IAA。",
        "thumb_url": "https://example.com/cover/xuanhuan.jpg",
    },
    {
        "book_id": 9100000002,
        "playlet_id": 9100000002,
        "book_name": "演示·都市神医",
        "tab_text": "IAP",
        "category_text": "都市,神医",
        "single_price": "9.9",
        "episode_amount": 60,
        "gender": 1,
        "publish_status": 2,
        "publish_time": "2026-09-01 09:00:00",
        "estimate_publish_time": "2026-09-01 09:00:00",
        "permission_status": 1,
        "create_time": "2026-08-20 09:00:00",
        "delivery_status": True,
        "abstract": "演示数据：收费投放，页签为 IAP。",
        "thumb_url": "https://example.com/cover/dushi.jpg",
    },
    {
        "book_id": 9100000003,
        "playlet_id": 9100000003,
        "book_name": "演示·甜宠日常",
        "tab_text": "IAA",
        "category_text": "甜宠,日常",
        "single_price": "0",
        "episode_amount": 40,
        "gender": 2,
        "publish_status": 1,
        "publish_time": "2026-10-08 18:30:00",
        "estimate_publish_time": "2026-10-08 18:30:00",
        "permission_status": 1,
        "create_time": "2026-09-01 09:00:00",
        "delivery_status": False,
        "abstract": "演示数据：未发布，页签为 IAA。",
        "thumb_url": "https://example.com/cover/tianchong.jpg",
    },
    {
        "book_id": 9100000004,
        "playlet_id": 9100000004,
        "book_name": "演示·悬疑反转",
        "tab_text": "IAP",
        "category_text": "悬疑,反转",
        "single_price": "1",
        "episode_amount": 24,
        "gender": 0,
        "publish_status": 3,
        "publish_time": "2026-09-15 12:00:00",
        "estimate_publish_time": "2026-09-15 12:00:00",
        "permission_status": 0,
        "create_time": "2026-09-01 09:00:00",
        "delivery_status": False,
        "abstract": "演示数据：已下架，页签为 IAP。",
        "thumb_url": "https://example.com/cover/xuanyi.jpg",
    },
    {
        "book_id": 9100000005,
        "playlet_id": 9100000005,
        "book_name": "演示·古言权谋",
        "tab_text": "IAP",
        "category_text": "古言,权谋",
        "single_price": "6.6",
        "episode_amount": 72,
        "gender": 2,
        "publish_status": 2,
        "publish_time": "2026-10-02 08:00:00",
        "estimate_publish_time": "2026-10-02 08:00:00",
        "permission_status": 1,
        "create_time": "2026-09-20 08:00:00",
        "delivery_status": True,
        "abstract": "演示数据：收费投放，页签为 IAP。",
        "thumb_url": "https://example.com/cover/guyan.jpg",
    },
    {
        "book_id": 9100000006,
        "playlet_id": 9100000006,
        "book_name": "演示·科幻末世",
        "tab_text": "IAA",
        "category_text": "科幻,末世",
        "single_price": "0",
        "episode_amount": 36,
        "gender": 1,
        "publish_status": 2,
        "publish_time": "2026-10-05 20:00:00",
        "estimate_publish_time": "2026-10-05 20:00:00",
        "permission_status": 1,
        "create_time": "2026-09-28 20:00:00",
        "delivery_status": True,
        "abstract": "演示数据：免费投放，页签为 IAA。",
        "thumb_url": "https://example.com/cover/kehuan.jpg",
    },
)


def _series(spec: dict[str, object], collected_at) -> ManhuaSeries:
    """把一条演示规格收成漫剧行。预估可投时间写成带时区的时间。"""
    estimate = spec["estimate_publish_time"]
    return ManhuaSeries(
        thumb_url=str(spec["thumb_url"]),
        book_id=int(spec["book_id"]),
        playlet_id=int(spec["playlet_id"]),
        book_name=str(spec["book_name"]),
        episode_amount=int(spec["episode_amount"]),
        gender=int(spec["gender"]),
        category_text=str(spec["category_text"]),
        tab_text=str(spec["tab_text"]),
        publish_status=int(spec["publish_status"]),
        publish_time=str(spec["publish_time"]),
        estimate_publish_time=parse_beijing_stamp(str(estimate)),
        permission_status=int(spec["permission_status"]),
        create_time=str(spec["create_time"]),
        douyin_nick_name="演示剧场",
        single_price=str(spec["single_price"]),
        abstract=str(spec["abstract"]),
        delivery_status=bool(spec["delivery_status"]),
        promotion_triggered=False,
        collected_at=collected_at,
    )


async def load_demo() -> None:
    """写入演示短剧。已有同一 book_id 的未删除行则跳过。"""
    book_ids = [int(row["book_id"]) for row in _ROWS]
    async for session in get_session():
        found = await session.scalars(
            select(ManhuaSeries.book_id).where(
                ManhuaSeries.book_id.in_(book_ids),
                ManhuaSeries.is_deleted == 0,
            )
        )
        existing = set(found.all())
        now = beijing_now()
        inserted = 0
        for spec in _ROWS:
            if int(spec["book_id"]) in existing:
                continue
            session.add(_series(spec, now))
            inserted += 1
        await session.commit()
        print(f"漫剧演示数据：新插入 {inserted} 条（已存在的 book_id 已跳过，本次跳过 {len(existing)} 条）")
        return


def main() -> None:
    """命令行入口：连开发库并写入演示行。"""

    async def _run() -> None:
        init_engine(get_settings())
        try:
            await load_demo()
        finally:
            await dispose_engine()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
