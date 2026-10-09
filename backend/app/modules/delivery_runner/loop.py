"""main.py 约每分钟调用一次。时钟可由测试传入。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.times import beijing_now
from app.modules.delivery_runner.due import as_beijing
from app.modules.delivery_runner.robot import run_due_robots
from app.modules.delivery_runner.standard import run_due_standard


async def run_due_rules(session: AsyncSession, now: datetime | None = None) -> dict[str, int]:
    """执行到点的标准自动规则和漫剧机器人规则。"""
    clock = as_beijing(now or beijing_now())
    standard = await run_due_standard(session, clock)
    robot = await run_due_robots(session, clock)
    return {"standard": standard, "robot": robot}
