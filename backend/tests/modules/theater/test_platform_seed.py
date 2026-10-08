"""启动时只在平台表为空时写入番茄和鸥溪。不连脚本里写死的库。"""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from typing import Any

from scripts.seed_theater_platforms import _ROWS, ensure_theater_platforms

BACKEND = Path(__file__).resolve().parents[3]


class SeedSession:
    """只记下计数和插入。"""

    def __init__(self, count: int) -> None:
        self.count = count
        self.statements: list[Any] = []

    async def scalar(self, statement: Any) -> int:
        """返回预置行数。"""
        self.statements.append(statement)
        return self.count

    async def execute(self, statement: Any) -> None:
        """记下插入。"""
        self.statements.append(statement)


class PlatformSeedTests(unittest.TestCase):
    def test_rows_are_fanqie_and_ouxi(self) -> None:
        """种子就是番茄 1 和鸥溪 22。"""
        self.assertEqual(_ROWS[0]["id"], 1)
        self.assertEqual(_ROWS[0]["name"], "番茄")
        self.assertEqual(_ROWS[1]["id"], 22)
        self.assertEqual(_ROWS[1]["name"], "鸥溪")

    def test_empty_table_inserts_and_existing_rows_are_left_alone(self) -> None:
        """没有行才插入。已经有平台就不改。"""
        empty = SeedSession(0)
        asyncio.run(ensure_theater_platforms(empty))
        self.assertEqual(len(empty.statements), 2)
        filled = SeedSession(2)
        asyncio.run(ensure_theater_platforms(filled))
        self.assertEqual(len(filled.statements), 1)

    def test_startup_seeds_platforms_only_with_the_ocean_mock(self) -> None:
        """平台种子跟巨量种子一起，只从 mock 启动走进去。"""
        text = (BACKEND / "main.py").read_text(encoding="utf-8")
        self.assertIn("if settings.oceanengine.mock:", text)
        self.assertIn("ensure_theater_platforms", text)
        self.assertNotIn("fake_catalog", text)
        self.assertNotIn("9101", text)
