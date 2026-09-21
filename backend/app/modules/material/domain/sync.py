from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_engine
from app.modules.material.domain.changdu import (
    PAGE_GAP_SECONDS,
    PAGE_SIZE,
    AwemeSeriesRecord,
    ChangduAwemeClient,
    SeriesPageClient,
    sync_window,
)
from app.modules.material.domain.models import ManhuaSeries

logger = logging.getLogger(__name__)

_SYNC_TASK: asyncio.Task[None] | None = None


def credentials_ready(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool(cfg.changdu.distributor_id.strip() and cfg.changdu.secret_key.strip())


async def upsert_records(session: AsyncSession, records: list[AwemeSeriesRecord], collected_at: datetime) -> int:
    if not records:
        return 0
    rows = [
        {
            "thumb_url": item.thumb_url,
            "book_id": item.book_id,
            "playlet_id": item.playlet_id,
            "book_name": item.book_name,
            "episode_amount": item.episode_amount,
            "gender": item.gender,
            "category_text": item.category_text,
            "publish_status": item.publish_status,
            "publish_time": item.publish_time,
            "estimate_publish_time": item.estimate_publish_time,
            "permission_status": item.permission_status,
            "create_time": item.create_time,
            "douyin_nick_name": item.douyin_nick_name,
            "single_price": item.single_price,
            "abstract": item.abstract,
            "delivery_status": item.delivery_status,
            "collected_at": collected_at,
        }
        for item in records
    ]
    stmt = insert(ManhuaSeries).values(rows)
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        constraint="uq_manhua_series_playlet_book",
        set_={
            "thumb_url": excluded.thumb_url,
            "book_id": excluded.book_id,
            "episode_amount": excluded.episode_amount,
            "gender": excluded.gender,
            "category_text": excluded.category_text,
            "publish_status": excluded.publish_status,
            "publish_time": excluded.publish_time,
            "estimate_publish_time": excluded.estimate_publish_time,
            "permission_status": excluded.permission_status,
            "create_time": excluded.create_time,
            "douyin_nick_name": excluded.douyin_nick_name,
            "single_price": excluded.single_price,
            "abstract": excluded.abstract,
            "delivery_status": excluded.delivery_status,
            "collected_at": excluded.collected_at,
        },
    )
    await session.execute(stmt)
    return len(rows)


async def pull_window(
    client: SeriesPageClient,
    session: AsyncSession,
    *,
    start_time: str,
    end_time: str,
    collected_at: datetime | None = None,
    page_gap_seconds: float = PAGE_GAP_SECONDS,
) -> int:
    now = collected_at or datetime.now(timezone.utc)
    page_index = 0
    written = 0
    while True:
        total, records = await client.fetch_page(
            start_time=start_time,
            end_time=end_time,
            page_index=page_index,
            page_size=PAGE_SIZE,
        )
        written += await upsert_records(session, records, now)
        if not records or (page_index + 1) * PAGE_SIZE >= total:
            break
        page_index += 1
        await asyncio.sleep(page_gap_seconds)
    return written


async def sync_once(settings: Settings | None = None, client: SeriesPageClient | None = None) -> int:
    cfg = settings or get_settings()
    if not credentials_ready(cfg):
        logger.warning("常读 distributor_id/secret_key 未配置，跳过同步")
        return 0
    actor = client or ChangduAwemeClient(cfg.changdu)
    start_time, end_time = sync_window()
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        written = await pull_window(actor, session, start_time=start_time, end_time=end_time)
        await session.commit()
    logger.info("常读短剧同步完成 window=%s~%s rows=%s", start_time, end_time, written)
    return written


async def _loop() -> None:
    interval = max(60, get_settings().changdu.sync_interval_seconds)
    while True:
        try:
            await sync_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("常读短剧同步失败")
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise


def start_sync() -> asyncio.Task[None]:
    global _SYNC_TASK
    if _SYNC_TASK is None or _SYNC_TASK.done():
        _SYNC_TASK = asyncio.create_task(_loop(), name="changdu-manhua-sync")
    return _SYNC_TASK


async def stop_sync() -> None:
    global _SYNC_TASK
    if _SYNC_TASK is None:
        return
    _SYNC_TASK.cancel()
    try:
        await _SYNC_TASK
    except asyncio.CancelledError:
        pass
    _SYNC_TASK = None
