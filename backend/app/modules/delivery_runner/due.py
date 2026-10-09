"""到点判断。测试传入时钟，不在这里睡觉。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.times import BEIJING


def as_beijing(value: datetime) -> datetime:
    """无时区按北京时间。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=BEIJING)
    return value.astimezone(BEIJING)


def standard_is_due(
    *,
    is_enabled: bool,
    schedule_start: datetime | None,
    ran_at: datetime | None,
    now: datetime,
) -> bool:
    """开启、还没跑过，并且没有预约或预约时间已到。"""
    if not is_enabled or ran_at is not None:
        return False
    clock = as_beijing(now)
    if schedule_start is None:
        return True
    return clock >= as_beijing(schedule_start)


def robot_is_due(
    *,
    is_enabled: bool,
    schedule_hour: int,
    schedule_minute: int,
    ran_today: bool,
    now: datetime,
) -> bool:
    """开启、今天还没跑，并且现在已经到了保存的时分。不要求结束时间。"""
    if not is_enabled or ran_today:
        return False
    clock = as_beijing(now)
    slot = clock.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
    return clock >= slot


def span_day(stat_span: str, now: datetime) -> date:
    """today 是北京今天，yesterday 是昨天。"""
    today = as_beijing(now).date()
    if stat_span == "yesterday":
        return today - timedelta(days=1)
    return today


def publish_on_day(publish_time: str, day: date) -> bool:
    """上架原串的前 10 位是这一天。"""
    return str(publish_time or "")[:10] == day.isoformat()


def snapshots_satisfy(
    rows: list[tuple[Decimal, Decimal]],
    *,
    cost_min: Decimal | None,
    cost_max: Decimal | None,
    recovery_min: Decimal | None,
    recovery_max: Decimal | None,
) -> bool:
    """已有快照里至少一行同时落在消耗和回收区间。

    回收率在规则上是百分比，80 表示 80%。快照 ROI 是比值，0.3 表示 30%。
    某一侧没填就不当成限制。
    """
    if cost_min is None and recovery_min is None:
        return True
    for cost, roi in rows:
        if cost_min is not None and cost_max is not None and not cost_min <= cost <= cost_max:
            continue
        if recovery_min is not None and recovery_max is not None:
            percent = roi * Decimal(100)
            if not recovery_min <= percent <= recovery_max:
                continue
        return True
    return False


def series_block_reason(
    *,
    videos: list[int],
    titles: list[int],
    accounts: list[int],
    playlet_id: int,
    publish_ok: bool,
    snapshot_ok: bool,
) -> str | None:
    """不能生成草稿时的一句话。能生成则返回 None。不发明巨量视频号。"""
    if not publish_ok:
        return "上架时间不在规则范围内"
    if not snapshot_ok:
        return "报表快照不在消耗或回收区间"
    if playlet_id <= 0:
        return "短剧没有专辑 id"
    if not accounts:
        return "没有已分配的广告账户"
    if not videos:
        return "这部剧没有视频素材"
    if not titles:
        return "没有可用标题"
    return None


def album_url_for_playlet(playlet_id: int) -> str:
    """短剧专辑链接。不是剧场推广链。"""
    return f"https://www.douyin.com/playlet/{playlet_id}"
