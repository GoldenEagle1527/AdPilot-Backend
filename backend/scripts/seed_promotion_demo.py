"""在 backend/ 下执行：
ADPILOT_ALLOW_REMOTE=1 python scripts/seed_promotion_demo.py

往脚本里写死的库插入推广链同步任务和推广链演示数据，挂到已有 manhua_series。
演示短剧用 book_id 9100000001–9100000004（先跑 seed_manhua_series.py）。
已有同 promotion_id 的推广链、或同 series 且 reason 以「演示·」开头的任务则跳过。
"""

from __future__ import annotations

import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session, init_engine
from app.core.times import beijing_now
from app.modules.material.model import ManhuaSeries
from app.modules.theater.model import (
    PromotionLinkSource,
    PromotionTaskSource,
    PromotionTaskStatus,
    TheaterApp,
    TheaterPromotionLink,
    TheaterPromotionTask,
)

_POSTGRES = {
    "host": "192.168.111.40",
    "port": 5432,
    "database": "ad_pilot",
    "user": "root",
    "password": "ocsaas123456",
}

# 与 seed_manhua_series.py 演示短剧对齐
_DEMO_BOOK_IDS = (9100000001, 9100000002, 9100000003, 9100000004)
_DEMO_REASON_PREFIX = "演示·"
# 演示推广链 ID 段，避免和真实常读 ID 撞
_DEMO_PROMOTION_IDS = (9200000001, 9200000002, 9200000003, 9200000004, 9200000005)


def _bind_database() -> None:
    """固定连到脚本里的库，不跟 deployment yaml 的 postgres 走。"""
    settings = get_settings()
    postgres = settings.postgres.model_copy(update=_POSTGRES)
    init_engine(settings.model_copy(update={"postgres": postgres}))


async def _demo_series(session) -> dict[int, ManhuaSeries]:
    """按演示 book_id 取短剧，缺哪条就报错。"""
    result = await session.execute(
        select(ManhuaSeries).where(
            ManhuaSeries.book_id.in_(_DEMO_BOOK_IDS),
            ManhuaSeries.is_deleted == 0,
        )
    )
    by_book = {row.book_id: row for row in result.scalars().all()}
    missing = [bid for bid in _DEMO_BOOK_IDS if bid not in by_book]
    if missing:
        raise RuntimeError(
            f"缺演示短剧 book_id={missing}，先跑：ADPILOT_ALLOW_REMOTE=1 python scripts/seed_manhua_series.py"
        )
    return by_book


async def _first_app_id(session) -> int | None:
    """随便挂一个未删有效应用；没有就空着。"""
    result = await session.execute(
        select(TheaterApp.id)
        .where(TheaterApp.is_deleted == 0, TheaterApp.is_valid.is_(True))
        .order_by(TheaterApp.id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _task_exists(session, series_id: int, reason: str) -> bool:
    result = await session.execute(
        select(TheaterPromotionTask.id)
        .where(
            TheaterPromotionTask.series_id == series_id,
            TheaterPromotionTask.reason == reason,
            TheaterPromotionTask.is_deleted == 0,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def load_demo() -> None:
    """写入演示任务和推广链，挂到演示短剧。"""
    now = beijing_now()
    async for session in get_session():
        series = await _demo_series(session)
        app_id = await _first_app_id(session)
        s1, s2, s3, s4 = (series[bid] for bid in _DEMO_BOOK_IDS)

        task_specs = [
            # 玄幻：自动成功，带两条接口链
            {
                "series": s1,
                "source": PromotionTaskSource.AUTO,
                "status": PromotionTaskStatus.SUCCESS,
                "reason": f"{_DEMO_REASON_PREFIX}自动同步成功",
                "execute_at": now - timedelta(hours=2),
                "finished_at": now - timedelta(hours=1),
                "retry_count": 0,
                "links": [
                    {
                        "promotion_id": _DEMO_PROMOTION_IDS[0],
                        "promotion_url": "https://example.com/promo/xuanhuan-iaa",
                        "recharge_template_name": "IAA",
                        "media_config_type": 3,
                        "source": PromotionLinkSource.API,
                        "package_app_key": "demo_fanqie_iaa",
                    },
                    {
                        "promotion_id": _DEMO_PROMOTION_IDS[1],
                        "promotion_url": "https://example.com/promo/xuanhuan-mid",
                        "recharge_template_name": "中额",
                        "media_config_type": 2,
                        "source": PromotionLinkSource.API,
                        "package_app_key": "demo_fanqie_iap",
                    },
                ],
            },
            # 都市：手动成功 + 一条接口链；另挂一条人工链（无 task）
            {
                "series": s2,
                "source": PromotionTaskSource.MANUAL,
                "status": PromotionTaskStatus.SUCCESS,
                "reason": f"{_DEMO_REASON_PREFIX}批量采集成功",
                "execute_at": now - timedelta(days=1),
                "finished_at": now - timedelta(hours=20),
                "retry_count": 1,
                "links": [
                    {
                        "promotion_id": _DEMO_PROMOTION_IDS[2],
                        "promotion_url": "https://example.com/promo/dushi-iap",
                        "recharge_template_name": "小额",
                        "media_config_type": 2,
                        "source": PromotionLinkSource.API,
                        "package_app_key": "demo_fanqie_iap",
                    },
                ],
                "manual_link": {
                    "promotion_id": None,
                    "promotion_url": "https://example.com/promo/dushi-manual",
                    "recharge_template_name": "超小额",
                    "media_config_type": 2,
                    "source": PromotionLinkSource.MANUAL,
                    "package_app_key": "",
                },
            },
            # 甜宠：待执行，尚无链
            {
                "series": s3,
                "source": PromotionTaskSource.AUTO,
                "status": PromotionTaskStatus.PENDING,
                "reason": f"{_DEMO_REASON_PREFIX}未到执行时间",
                "execute_at": now + timedelta(hours=6),
                "finished_at": None,
                "retry_count": 0,
                "links": [],
            },
            # 悬疑：失败；排队中另挂一条 queued 任务样式用 queued 状态
            {
                "series": s4,
                "source": PromotionTaskSource.AUTO,
                "status": PromotionTaskStatus.FAILED,
                "reason": f"{_DEMO_REASON_PREFIX}常读无符合推广链",
                "execute_at": now - timedelta(hours=3),
                "finished_at": now - timedelta(hours=2, minutes=50),
                "retry_count": 5,
                "links": [],
            },
            {
                "series": s4,
                "source": PromotionTaskSource.MANUAL,
                "status": PromotionTaskStatus.QUEUED,
                "reason": f"{_DEMO_REASON_PREFIX}排队待爬虫",
                "execute_at": now - timedelta(minutes=10),
                "finished_at": None,
                "retry_count": 0,
                "links": [
                    {
                        "promotion_id": _DEMO_PROMOTION_IDS[3],
                        "promotion_url": "https://example.com/promo/xuanyi-retry",
                        "recharge_template_name": "超超小额",
                        "media_config_type": 2,
                        "source": PromotionLinkSource.API,
                        "package_app_key": "demo_fanqie_iap",
                    },
                ],
            },
            # 玄幻再挂一条 running，覆盖状态
            {
                "series": s1,
                "source": PromotionTaskSource.MANUAL,
                "status": PromotionTaskStatus.RUNNING,
                "reason": f"{_DEMO_REASON_PREFIX}爬虫处理中",
                "execute_at": now - timedelta(minutes=5),
                "finished_at": None,
                "retry_count": 2,
                "links": [],
            },
        ]

        tasks_added = 0
        links_added = 0
        for spec in task_specs:
            row = spec["series"]
            if await _task_exists(session, row.id, spec["reason"]):
                continue
            task = TheaterPromotionTask(
                series_id=row.id,
                collector_id=None,
                source=spec["source"],
                status=spec["status"],
                reason=spec["reason"],
                execute_at=spec["execute_at"],
                finished_at=spec["finished_at"],
                retry_count=spec["retry_count"],
            )
            session.add(task)
            await session.flush()
            tasks_added += 1

            for link in spec["links"]:
                result = await session.execute(
                    insert(TheaterPromotionLink)
                    .values(
                        theater_app_id=app_id,
                        series_id=row.id,
                        task_id=task.id,
                        source=link["source"],
                        promotion_id=link["promotion_id"],
                        promotion_url=link["promotion_url"],
                        recharge_template_name=link["recharge_template_name"],
                        media_config_type=link["media_config_type"],
                        publish_time=row.estimate_publish_time,
                        promotion_create_time=now - timedelta(hours=1),
                        package_app_key=link["package_app_key"],
                        is_enabled=True,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["promotion_id"],
                        index_where=TheaterPromotionLink.promotion_id.is_not(None),
                    )
                    .returning(TheaterPromotionLink.id)
                )
                if result.scalar_one_or_none() is not None:
                    links_added += 1

            manual = spec.get("manual_link")
            if manual is not None:
                # 人工链无 promotion_id，按 URL 去重
                exists = await session.execute(
                    select(TheaterPromotionLink.id)
                    .where(
                        TheaterPromotionLink.series_id == row.id,
                        TheaterPromotionLink.promotion_url == manual["promotion_url"],
                        TheaterPromotionLink.is_deleted == 0,
                    )
                    .limit(1)
                )
                if exists.scalar_one_or_none() is None:
                    session.add(
                        TheaterPromotionLink(
                            theater_app_id=app_id,
                            series_id=row.id,
                            task_id=None,
                            source=manual["source"],
                            promotion_id=manual["promotion_id"],
                            promotion_url=manual["promotion_url"],
                            recharge_template_name=manual["recharge_template_name"],
                            media_config_type=manual["media_config_type"],
                            publish_time=row.estimate_publish_time,
                            promotion_create_time=now,
                            package_app_key=manual["package_app_key"],
                            is_enabled=True,
                        )
                    )
                    links_added += 1

        # 再补一条仅挂短剧、无任务的演示链（覆盖列表里 task 为空）
        orphan_url = "https://example.com/promo/orphan-manual"
        orphan = await session.execute(
            select(TheaterPromotionLink.id)
            .where(
                TheaterPromotionLink.promotion_url == orphan_url,
                TheaterPromotionLink.is_deleted == 0,
            )
            .limit(1)
        )
        if orphan.scalar_one_or_none() is None:
            session.add(
                TheaterPromotionLink(
                    theater_app_id=app_id,
                    series_id=s2.id,
                    task_id=None,
                    source=PromotionLinkSource.MANUAL,
                    promotion_id=_DEMO_PROMOTION_IDS[4],
                    promotion_url=orphan_url,
                    recharge_template_name="中额",
                    media_config_type=2,
                    publish_time=s2.estimate_publish_time,
                    promotion_create_time=now,
                    package_app_key="demo_orphan",
                    is_enabled=False,
                )
            )
            links_added += 1

        await session.commit()
        print(
            f"推广演示数据：新插入任务 {tasks_added} 条、推广链 {links_added} 条"
            f"（theater_app_id={app_id}；已存在的已跳过）"
        )


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
