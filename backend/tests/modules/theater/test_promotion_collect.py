"""手动批量采集只写本地任务，请求处理里不调常读。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from pydantic import ValidationError

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.material.model import ManhuaSeries
from app.modules.theater.schema import PromotionCollectCreate
from app.modules.theater.service import create_manual_promotion_task


def _series(**kwargs: object) -> ManhuaSeries:
    """内存里的一部短剧。"""
    row = ManhuaSeries(
        book_id=kwargs.get("book_id", 88),
        book_name=kwargs.get("book_name", "甲剧"),
        tab_text="IAP",
    )
    row.id = 8
    row.is_deleted = 0
    return row


def _session(series: ManhuaSeries | None) -> MagicMock:
    """查询返回这部剧；提交和刷新什么也不做，刷新时补上主键。"""
    session = MagicMock()
    found = MagicMock()
    found.scalar_one_or_none.return_value = series
    session.execute = AsyncMock(return_value=found)

    async def refresh(row: object) -> None:
        row.id = 15  # type: ignore[attr-defined]

    session.refresh = refresh
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


class CollectSchemaTests(unittest.TestCase):
    def test_charge_defaults_to_all_and_time_needs_seconds(self) -> None:
        """付费类型缺省是全部；执行时间必须到秒。"""
        body = PromotionCollectCreate(series_id=8, execute_at="2099-01-01 00:00:00")
        self.assertEqual(body.charge_type, "all")
        self.assertEqual(body.execute_at, datetime(2099, 1, 1, tzinfo=BEIJING))
        with self.assertRaises(ValidationError):
            PromotionCollectCreate(series_id=8, execute_at="2099-01-01", charge_type="paid")
        with self.assertRaises(ValidationError):
            PromotionCollectCreate(series_id=8, execute_at="2099-01-01 00:00:00", charge_type="iap")


class CollectWriteTests(unittest.TestCase):
    def test_writes_manual_task_and_does_not_touch_a_client(self) -> None:
        """选免费时记下 IAA，采集人是当前用户，状态停在初始。"""
        session = _session(_series())
        body = PromotionCollectCreate(series_id=8, execute_at="2099-01-01 08:30:00", charge_type="free")
        data = asyncio.run(create_manual_promotion_task(session, body, {"id": "3", "nickname": "短剧投手"}))
        row = session.add.call_args.args[0]
        self.assertEqual(row.source, "manual")
        self.assertEqual(row.status, "pending")
        self.assertEqual(row.charge_filter, "IAA")
        self.assertEqual(row.collector_id, 3)
        self.assertEqual(row.series_id, 8)
        self.assertEqual(data["collector_name"], "短剧投手")
        self.assertEqual(data["charge_type"], "free")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["execute_at"], "2099-01-01T08:30:00+08:00")
        session.commit.assert_awaited()

    def test_missing_series_and_missing_book_id(self) -> None:
        """剧不在或没有 book_id 时不建任务。"""
        body = PromotionCollectCreate(series_id=8, execute_at="2099-01-01 08:30:00")
        missing = _session(None)
        with self.assertRaises(ApiError) as none:
            asyncio.run(create_manual_promotion_task(missing, body, {"id": "3", "nickname": "短剧投手"}))
        self.assertEqual(none.exception.status_code, 404)
        missing.add.assert_not_called()
        empty = _session(_series(book_id=0))
        with self.assertRaises(ApiError) as no_book:
            asyncio.run(create_manual_promotion_task(empty, body, {"id": "3", "nickname": "短剧投手"}))
        self.assertEqual(no_book.exception.status_code, 400)
        empty.add.assert_not_called()


class MockIsolationTests(unittest.TestCase):
    def test_request_modules_do_not_call_changdu(self) -> None:
        """剧场请求处理不引用常读客户端，也不按 mock 开关分叉。"""
        root = Path(__file__).resolve().parents[3] / "app" / "modules" / "theater"
        banned = ("ChangduClient", "fake_changdu", "promotion_client", "httpx", "oceanengine.mock")
        for path in root.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for word in banned:
                self.assertNotIn(word, text, f"{path.name} 含 {word}")
