"""线上目录：模板打全域模板表，平台没有来源时失败关闭。"""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from typing import Any

from app.core.envelope import ApiError
from app.modules.uni_robot.port import UniRobotCatalog
from app.modules.uni_template.catalog import DatabaseUniRobotCatalog

BACKEND = Path(__file__).resolve().parents[3]


class FakeResult:
    """假 execute 结果。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None


class RecordingSession:
    """只记录语句。预置结果按次序吐出。"""

    def __init__(self, results: list[list[Any]]) -> None:
        self.results = list(results)
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> FakeResult:
        """记下 SQL，再返回下一份预置结果。"""
        self.statements.append(statement)
        rows = self.results.pop(0) if self.results else []
        return FakeResult(rows)


class CatalogTests(unittest.TestCase):
    def test_catalog_satisfies_the_port(self) -> None:
        """线上实现长得像目录端口。"""
        self.assertIsInstance(DatabaseUniRobotCatalog(RecordingSession([])), UniRobotCatalog)

    def test_template_hit_reads_the_uni_table(self) -> None:
        """命中时交回原来的模板 id，SQL 只查未删除的全域行。"""
        session = RecordingSession([[8]])
        got = asyncio.run(DatabaseUniRobotCatalog(session).require_template(8))
        self.assertEqual(got, 8)
        sql = str(session.statements[0].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("delivery_template.delivery_mode = 'uni'", sql)
        self.assertIn("delivery_template.is_deleted = 0", sql)
        self.assertIn("delivery_template.id = 8", sql)
        self.assertNotIn("theater_platforms", sql)

    def test_missing_template_is_rejected(self) -> None:
        """表里没有这条全域模板时 400。"""
        session = RecordingSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(DatabaseUniRobotCatalog(session).require_template(8))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "全域模板不存在")

    def test_existing_platform_is_returned(self) -> None:
        """未删除的剧场平台交回原来的 id。"""
        session = RecordingSession([[1]])
        got = asyncio.run(DatabaseUniRobotCatalog(session).require_platform(1))
        self.assertEqual(got, 1)
        sql = str(session.statements[0].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("theater_platforms.id = 1", sql)
        self.assertIn("theater_platforms.is_deleted = 0", sql)

    def test_unknown_platform_is_rejected(self) -> None:
        """表里没有这条就 400。生产代码不单列测试用的平台号。"""
        session = RecordingSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(DatabaseUniRobotCatalog(session).require_platform(9101))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "剧场平台不存在")
        sql = str(session.statements[0].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("theater_platforms", sql)
        self.assertIn("is_deleted = 0", sql)

    def test_source_does_not_embed_fake_platforms(self) -> None:
        """应用代码不写假平台，也不写死测试目录里的平台号。"""
        text = (BACKEND / "app" / "modules" / "uni_template" / "catalog.py").read_text(encoding="utf-8")
        self.assertNotIn("fake_catalog", text)
        self.assertNotIn("9101", text)
        self.assertNotIn("9102", text)
