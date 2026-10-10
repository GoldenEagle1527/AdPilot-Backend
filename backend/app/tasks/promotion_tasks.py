"""番茄推广链同步：每分钟给到预估投放时间的短剧建自动任务；每分钟执行到点任务，调常读拉推广链落库。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.clients.changdu_factory import promotion_client
from app.core.config import get_settings
from app.core.times import beijing_now
from app.modules.theater.changdu import link_matches, promotion_fields
from app.modules.theater.crud import (
    claim_due_tasks,
    create_due_auto_tasks,
    get_task_with_series,
    insert_missing_links,
)
from app.modules.theater.model import PromotionTaskStatus
from app.notify.changdu import ChangduNotify
from app.notify.dingtalk import DingTalkWebhook
from app.tasks.celery_app import celery_app

# 最多调用次数，第 5 次仍失败即失败
MAX_ATTEMPTS = 5
# 无符合的推广链原因
NO_MATCH_REASON = "常读无符合的推广链"
# 一次执行同时调常读的任务共用的数据库连接数
POOL_SIZE = 5
# 每分钟最多领多少条，要在 60 秒软超时内跑完、不撞常读 30 次/秒限频；没领到的下一分钟接着领
BATCH_SIZE = 20


@asynccontextmanager
async def session_factory(pool_size: int = 1) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """每次 asyncio.run 都是新事件循环，全局 engine 不能跨循环复用，这里自建 engine，用完即关。"""
    engine = create_async_engine(
        get_settings().async_database_url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=0,
        connect_args={"timeout": 3},
    )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def create_due_tasks() -> int:
    """建到点短剧的自动任务并提交。返回建了几条。"""
    async with session_factory() as factory, factory() as session:
        series_ids = await create_due_auto_tasks(session, beijing_now())
        await session.commit()
    return len(series_ids)


async def fetch_one(factory: async_sessionmaker[AsyncSession], task_id: int) -> None:
    """执行一条已改成爬虫处理中的任务。

    有符合页签的推广链成功，否则失败并写原因。任何一步出错都记一次失败：不满 5 次改回初始，下一轮再捞；
    第 5 次失败即失败，写完成时间并推钉钉。
    """
    async with factory() as session:
        row = await get_task_with_series(session, task_id)
        if row is None:
            return
        task, series = row
        # 回滚会让对象过期，异步下再读属性会报错，出错分支要用的值先取出来
        failures, book_id, book_name, tab_text = task.retry_count + 1, series.book_id, series.book_name, series.tab_text
        charge_filter = task.charge_filter
        # 结束读事务、把连接还回池，调常读期间不占连接
        await session.commit()
        try:
            items = await promotion_client().list_promotions(book_id)
            links = [
                {**promotion_fields(item), "series_id": series.id, "task_id": task_id}
                for item in items
                if link_matches(item, charge_filter=charge_filter, tab_text=tab_text)
            ]
            await insert_missing_links(session, links)
            task.status, task.reason = (
                (PromotionTaskStatus.SUCCESS, "") if links else (PromotionTaskStatus.FAILED, NO_MATCH_REASON)
            )
            task.finished_at = beijing_now()
            await session.commit()
        except Exception as exc:  # noqa: BLE001 任何失败都要落原因，否则任务永远停在爬虫处理中
            await session.rollback()
            final = failures >= MAX_ATTEMPTS
            task.status = PromotionTaskStatus.FAILED if final else PromotionTaskStatus.PENDING
            task.reason = (str(exc) or type(exc).__name__)[:1024]
            task.retry_count = failures
            task.finished_at = beijing_now() if final else None
            await session.commit()
            if final:
                webhook = DingTalkWebhook(get_settings().dingtalk.webhook)
                await ChangduNotify(webhook).promotion_failed(book_name, book_id, task.reason)


async def run_due() -> int:
    """领取到执行时间的初始任务（改成爬虫处理中），同时执行。返回领了几条。"""
    async with session_factory(POOL_SIZE) as factory:
        async with factory() as session:
            # 领取任务
            task_ids = await claim_due_tasks(session, beijing_now(), BATCH_SIZE)
            await session.commit()
        await asyncio.gather(*(fetch_one(factory, task_id) for task_id in task_ids))
    return len(task_ids)


@celery_app.task
def create_promotion_tasks() -> int:
    """每分钟：预估投放时间已到、没触发过的短剧各建一条自动任务（初始状态）。"""
    return asyncio.run(create_due_tasks())


@celery_app.task
def run_promotion_tasks() -> int:
    """每分钟：到执行时间的初始任务改成爬虫处理中，调常读拉推广链落库；失败改回初始等下一分钟，最多调 5 次。"""
    # ponytail: 执行中 worker 被杀或整批超过 60 秒软超时，已领的任务会停在爬虫处理中不再被捞。真遇到再把久停的 running 改回初始。
    return asyncio.run(run_due())
