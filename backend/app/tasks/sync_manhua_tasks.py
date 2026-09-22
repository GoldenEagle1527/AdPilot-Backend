"""常读短剧列表定时拉取。"""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.modules.material.crud import latest_create_time
from app.modules.material.service import ChangduClient, save_aweme_series
from app.notify.changdu import ChangduNotify
from app.notify.dingtalk import DingTalkWebhook
from app.tasks.celery_app import celery_app

_PAGE_INDEX = 0
_PAGE_SIZE = 100
_LOCK_KEY = "adpilot:material:aweme-series-sync"
_LOCK_SECONDS = 30
# 按常读创建时间降序
_SORT_FIELD_CREATE_TIME = 8
_SORT_TYPE_DESC = 1


async def pull_since_latest() -> int:
    """按库里最晚的常读创建时间拉 100 条。空库不带时间。锁被占用时跳过。"""
    settings = get_settings()
    redis = Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        password=settings.redis.password or None,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    locked = False
    engine = None
    try:
        locked = bool(await redis.set(_LOCK_KEY, "1", nx=True, ex=_LOCK_SECONDS))
        if not locked:
            return 0
        client = ChangduClient(
            settings.changdu,
            notify=ChangduNotify(DingTalkWebhook(settings.dingtalk.webhook)),
        )
        engine = create_async_engine(
            settings.async_database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            connect_args={"timeout": 3},
        )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            watermark = await latest_create_time(session)
            page = await client.list_aweme_series(
                page_index=_PAGE_INDEX,
                page_size=_PAGE_SIZE,
                sort_field=_SORT_FIELD_CREATE_TIME,
                sort_type=_SORT_TYPE_DESC,
                start_time=watermark or None,
            )
            inserted = await save_aweme_series(session, page.data)
            await session.commit()
        return inserted
    finally:
        if engine is not None:
            await engine.dispose()
        if locked:
            await redis.delete(_LOCK_KEY)
        await redis.aclose()


@celery_app.task
def sync_aweme_series() -> None:
    """按库里最晚的常读创建时间拉 100 条。专辑 ID 和剧名已在表里的跳过，只插入新的。"""
    asyncio.run(pull_since_latest())
