"""推广链同步任务列表：入参约束、只看三种状态的过滤、出参回填。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from app.core.times import BEIJING
from app.modules.material.model import ManhuaSeries
from app.modules.theater.model import TheaterPromotionTask
from app.modules.theater.schema import PromotionTaskQuery
from app.modules.theater.service import list_promotion_tasks, promotion_task_filters


def make_task(**kwargs) -> TheaterPromotionTask:
    """造一条内存里的任务行。"""
    row = TheaterPromotionTask(
        series_id=8,
        collector_id=kwargs.get("collector_id"),
        source="auto",
        status=kwargs.get("status", "success"),
        reason=kwargs.get("reason", ""),
        execute_at=datetime(2026, 9, 28, 10, 0, 0, 500000, tzinfo=BEIJING),
        finished_at=kwargs.get("finished_at"),
        retry_count=0,
    )
    row.id = 3
    return row


def make_series() -> ManhuaSeries:
    """造一条内存里的短剧行。"""
    return ManhuaSeries(book_name="甲剧", tab_text="IAP", category_text="玄幻,逆袭")


class QueryTests(unittest.TestCase):
    def test_hidden_statuses_are_rejected(self) -> None:
        """没到点和排队中不对外，传进来直接拒。"""
        for status in ("pending", "queued", "done"):
            with self.assertRaises(ValidationError):
                PromotionTaskQuery(status=status)

    def test_time_needs_seconds_and_order(self) -> None:
        """执行时间只收 YYYY-MM-DD HH:MM:SS，止早于起拒绝。"""
        with self.assertRaises(ValidationError):
            PromotionTaskQuery(execute_at_from="2026-09-28")
        with self.assertRaises(ValidationError):
            PromotionTaskQuery(execute_at_from="2026-09-28 10:00:00", execute_at_to="2026-09-28 09:59:59")
        query = PromotionTaskQuery(execute_at_from="2026-09-28 10:00:00", execute_at_to="2026-09-28 10:00:00")
        self.assertEqual(query.execute_at_from, datetime(2026, 9, 28, 10, tzinfo=BEIJING))


class FilterTests(unittest.TestCase):
    def _sql(self, query: PromotionTaskQuery) -> str:
        """把过滤条件编译成带字面量的 SQL 串，便于断言。"""
        return " AND ".join(
            str(item.compile(compile_kwargs={"literal_binds": True})) for item in promotion_task_filters(query)
        )

    def test_default_only_shows_started_tasks(self) -> None:
        """不传筛选也只看爬虫处理中、成功、失败。"""
        self.assertEqual(
            self._sql(PromotionTaskQuery()),
            "theater_promotion_tasks.is_deleted = 0 AND "
            "theater_promotion_tasks.status IN ('running', 'success', 'failed')",
        )

    def test_name_is_escaped_and_status_narrows(self) -> None:
        """剧名转义 % 和 _ 后模糊匹配短剧名；状态再收窄。"""
        sql = self._sql(PromotionTaskQuery(book_name=" 50%_剧 ", status="failed"))
        self.assertIn("theater_promotion_tasks.status = 'failed'", sql)
        self.assertIn("lower(manhua_series.book_name) LIKE lower('%50\\%\\_剧%')", sql)


class ListTests(unittest.TestCase):
    def test_items_fill_series_and_system_collector(self) -> None:
        """剧名、付费类型、短剧类型取短剧；没有采集人显示系统，有则用昵称；时间到秒。"""
        finished = datetime(2026, 9, 28, 10, 0, 40, tzinfo=BEIJING)
        rows = [
            (make_task(), make_series(), None),
            (make_task(collector_id=9, status="failed", reason="book not found", finished_at=finished), make_series(), "小王"),
        ]
        with patch("app.modules.theater.service.page_promotion_tasks", new=AsyncMock(return_value=(rows, 2))):
            data = asyncio.run(list_promotion_tasks(None, PromotionTaskQuery()))
        auto, manual = data["list"]
        self.assertEqual(data["total"], 2)
        self.assertEqual(auto["collector_name"], "系统")
        self.assertEqual(auto["book_name"], "甲剧")
        self.assertEqual(auto["tab_text"], "IAP")
        self.assertEqual(auto["category_text"], "玄幻,逆袭")
        self.assertEqual(auto["execute_at"], "2026-09-28T10:00:00+08:00")
        self.assertIsNone(auto["finished_at"])
        self.assertEqual(manual["collector_name"], "小王")
        self.assertEqual(manual["reason"], "book not found")
        self.assertEqual(manual["finished_at"], "2026-09-28T10:00:40+08:00")


if __name__ == "__main__":
    unittest.main()
