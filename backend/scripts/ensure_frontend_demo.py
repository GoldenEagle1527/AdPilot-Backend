"""手动补前端演示数据。启动不会 import，也不会自动执行。

在 backend/ 下：python scripts/ensure_frontend_demo.py
按应用配置连库，调用联合 mock。联合 mock 自己提交。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session, init_engine
from app.modules.joint_mock import ensure_joint_mock


async def ensure_frontend_demo(session: AsyncSession) -> None:
    """写入联合 mock。"""
    await ensure_joint_mock(session)


async def _main() -> None:
    init_engine(get_settings())
    try:
        async for session in get_session():
            await ensure_frontend_demo(session)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_main())
