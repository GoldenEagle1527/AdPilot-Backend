"""在 backend/ 下执行：python scripts/seed_theater_platforms.py

按应用配置连库，调用联合 mock。联合 mock 自己提交。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session, init_engine
from app.modules.joint_mock import ensure_joint_mock

_ROWS = [
    {"id": 1, "name": "番茄", "code": "1011", "sort_order": 1},
    {"id": 22, "name": "鸥溪", "code": "4504", "sort_order": 2},
]


def main() -> None:
    """命令行入口：按应用配置连库并写入联合 mock。"""

    async def _run() -> None:
        try:
            init_engine(get_settings())
            async for session in get_session():
                await ensure_joint_mock(session)
        finally:
            await dispose_engine()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
