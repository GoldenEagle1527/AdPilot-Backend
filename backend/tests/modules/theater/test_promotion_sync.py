"""到点短剧建自动任务、领取到点任务、单条任务状态流转；常读推广链收成推广链表字段并按页签过滤。"""

from __future__ import annotations

import asyncio
import unittest
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from sqlalchemy.dialects import postgresql

from app.clients.changdu import ChangduError
from app.core.times import BEIJING
from app.modules.material.model import ManhuaSeries
from app.modules.theater.changdu import matches_tab, promotion_fields
from app.modules.theater.crud import claim_due_tasks, create_due_auto_tasks
from app.modules.theater.model import TheaterPromotionTask
from app.tasks import promotion_tasks


def promotion(promotion_id: int, media_config_type: int) -> dict[str, Any]:
    """拼一条常读形态的推广链。"""
    return {
        "promotion_info": {
            "promotion_id": promotion_id,
            "promotion_url": f"https://x/{promotion_id}",
            "create_time": "2026-09-22 09:43:00",
        },
        "book_info": {"book_id": 8, "book_name": "甲剧", "publish_time": "2026-09-20 10:00:00"},
        "delivery": {"recharge_template_name": "中额"},
        "media_config": {"media_config_type": media_config_type},
        "package": {"app_key": "ak"},
    }


def captured_sql(fn: Any, *args: Any) -> tuple[Any, str, MagicMock]:
    """用假会话跑一个 crud，返回 (结果, 实际执行的 SQL, 假会话)。"""
    session = MagicMock()
    executed: list[Any] = []

    async def execute(statement: Any) -> Any:
        executed.append(statement)
        result = MagicMock()
        result.scalars.return_value.all.return_value = [5, 6]
        return result

    session.execute = execute
    value = asyncio.run(fn(session, *args))
    sql = str(executed[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    return value, sql, session


class CreateDueTasksTests(unittest.TestCase):
    def test_marks_due_series_and_adds_pending_tasks(self) -> None:
        """只挑没触发、未删除、预估投放时间已到的短剧，原子打标并返回 id，每部建一条初始自动任务。"""
        now = datetime(2026, 9, 29, 10, tzinfo=BEIJING)
        ids, sql, session = captured_sql(create_due_auto_tasks, now)
        self.assertEqual(ids, [5, 6])
        self.assertIn("SET promotion_triggered=true", sql)
        self.assertIn("manhua_series.promotion_triggered = false", sql)
        self.assertIn("manhua_series.is_deleted = 0", sql)
        self.assertIn("manhua_series.estimate_publish_time <= '2026-09-29 10:00:00+08:00'", sql)
        self.assertIn("RETURNING manhua_series.id", sql)
        tasks = list(session.add_all.call_args.args[0])
        self.assertEqual([(t.series_id, t.execute_at) for t in tasks], [(5, now), (6, now)])


class ClaimDueTasksTests(unittest.TestCase):
    def test_moves_oldest_due_pending_to_running_in_batch(self) -> None:
        """按执行时间先后领最多 limit 条未删除、到点的初始任务，跳过被别人锁住的，改成爬虫处理中并返回 id。"""
        now = datetime(2026, 9, 29, 10, tzinfo=BEIJING)
        ids, sql, _ = captured_sql(claim_due_tasks, now, 20)
        self.assertEqual(ids, [5, 6])
        self.assertIn("SET status='running'", sql)
        self.assertIn("theater_promotion_tasks.status = 'pending'", sql)
        self.assertIn("theater_promotion_tasks.is_deleted = 0", sql)
        self.assertIn("theater_promotion_tasks.execute_at <= '2026-09-29 10:00:00+08:00'", sql)
        self.assertIn("ORDER BY theater_promotion_tasks.execute_at, theater_promotion_tasks.id", sql)
        self.assertIn("LIMIT 20 FOR UPDATE SKIP LOCKED", sql)
        self.assertIn("RETURNING theater_promotion_tasks.id", sql)


class FakeSession:
    """提交、回滚都什么也不做。"""

    async def commit(self) -> None:
        """提交。"""

    async def rollback(self) -> None:
        """回滚。"""


class FetchOneTests(unittest.TestCase):
    def _run(self, *, tab: str = "IAP", failures: int = 0, items: Any = None, error: Exception | None = None):
        """用假会话、假常读、假钉钉跑一条已失败 failures 次的任务，返回 (任务行, 插入的推广链, 钉钉通知 mock)。"""
        task = TheaterPromotionTask(series_id=8, status="running", reason="", retry_count=failures)
        task.id = 3
        series = ManhuaSeries(book_id=88, book_name="甲剧", tab_text=tab)
        series.id = 8
        inserted: list[dict[str, Any]] = []

        @asynccontextmanager
        async def factory():
            yield FakeSession()

        async def insert(_session: Any, links: list[dict[str, Any]]) -> int:
            inserted.extend(links)
            return len(links)

        client = MagicMock()
        client.return_value.list_promotions = AsyncMock(side_effect=error, return_value=items or [])
        notify = MagicMock()
        notify.return_value.promotion_failed = AsyncMock()
        with (
            patch.object(promotion_tasks, "get_task_with_series", AsyncMock(return_value=(task, series))),
            patch.object(promotion_tasks, "ChangduClient", client),
            patch.object(promotion_tasks, "ChangduNotify", notify),
            patch.object(promotion_tasks, "insert_missing_links", insert),
        ):
            asyncio.run(promotion_tasks.fetch_one(factory, 3))
        return task, inserted, notify.return_value.promotion_failed

    def test_matched_links_succeed(self) -> None:
        """只落和页签一致的推广链，带上短剧和任务 id，任务成功并写完成时间。"""
        task, inserted, notified = self._run(items=[promotion(1, 2), promotion(2, 3)])
        self.assertEqual((task.status, task.reason), ("success", ""))
        self.assertIsNotNone(task.finished_at)
        self.assertEqual([link["promotion_id"] for link in inserted], [1])
        self.assertEqual((inserted[0]["series_id"], inserted[0]["task_id"]), (8, 3))
        notified.assert_not_called()

    def test_no_matched_link_fails_without_notify(self) -> None:
        """常读有返回但没有符合页签的推广链，任务失败写原因；不是调用失败，不推钉钉。"""
        task, inserted, notified = self._run(tab="IAA", items=[promotion(1, 2)])
        self.assertEqual((task.status, task.reason), ("failed", "常读无符合的推广链"))
        self.assertEqual(inserted, [])
        notified.assert_not_called()

    def test_error_goes_back_to_pending_until_fifth_failure(self) -> None:
        """出错不满 5 次：改回初始、次数加 1、写原因、不推钉钉；第 5 次失败：失败、写完成时间、推一条钉钉。"""
        task, _, notified = self._run(failures=0, error=ChangduError("book not found"))
        self.assertEqual(
            (task.status, task.reason, task.retry_count, task.finished_at), ("pending", "book not found", 1, None)
        )
        notified.assert_not_called()
        task, _, notified = self._run(failures=4, error=httpx.ConnectTimeout("timeout"))
        self.assertEqual((task.status, task.reason, task.retry_count), ("failed", "timeout", 5))
        self.assertIsNotNone(task.finished_at)
        notified.assert_awaited_once_with("甲剧", 88, "timeout")


class MappingTests(unittest.TestCase):
    def test_fields_and_tab_filter(self) -> None:
        """常读字段收进推广链表；IAP 只要付费 2，IAA 只要免费 3。"""
        fields = promotion_fields(promotion(7, 2))
        self.assertEqual(fields["promotion_id"], 7)
        self.assertEqual(fields["promotion_url"], "https://x/7")
        self.assertEqual(fields["recharge_template_name"], "中额")
        self.assertEqual(fields["media_config_type"], 2)
        self.assertEqual(fields["publish_time"], datetime(2026, 9, 20, 10, tzinfo=BEIJING))
        self.assertEqual(fields["promotion_create_time"], datetime(2026, 9, 22, 9, 43, tzinfo=BEIJING))
        self.assertEqual(fields["package_app_key"], "ak")
        self.assertTrue(matches_tab(promotion(1, 2), "IAP"))
        self.assertFalse(matches_tab(promotion(1, 3), "IAP"))
        self.assertTrue(matches_tab(promotion(1, 3), "IAA"))


class InsertMissingLinksTests(unittest.TestCase):
    def test_locks_series_skips_dupes_and_binds_app_by_mode(self) -> None:
        """落链前锁短剧；已有 id/URL/档位跳过；按 media_config_type 挂 IAA/IAP 应用。"""
        from app.modules.theater.crud import insert_missing_links
        from app.modules.theater.model import TheaterApp

        session = MagicMock()
        calls: list[Any] = []
        iaa = TheaterApp(name="免费", delivery_mode="IAA")
        iaa.id = 11
        iap = TheaterApp(name="付费", delivery_mode="IAP")
        iap.id = 22

        async def execute(statement: Any) -> Any:
            calls.append(statement)
            result = MagicMock()
            sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
            if "FOR UPDATE" in sql:
                return result
            if "promotion_id" in sql and "IN" in sql.upper():
                result.scalars.return_value.all.return_value = [1]
                return result
            result.all.return_value = [
                (8, "https://x/1", "IAA"),
                (8, "https://x/2", "中额"),
                (8, "https://old", "超小额"),
            ]
            return result

        session.execute = execute
        session.add_all = MagicMock()
        links = [
            {"promotion_id": 1, "series_id": 8, "promotion_url": "https://x/1", "recharge_template_name": "IAA", "media_config_type": 3},
            {"promotion_id": 2, "series_id": 8, "promotion_url": "https://x/2", "recharge_template_name": "中额", "media_config_type": 2},
            {"promotion_id": 3, "series_id": 8, "promotion_url": "https://x/3", "recharge_template_name": "小额", "media_config_type": 2},
            {"promotion_id": 4, "series_id": 8, "promotion_url": "https://x/4", "recharge_template_name": "超小额", "media_config_type": 2},
        ]
        with patch(
            "app.modules.theater.crud.first_app_by_delivery_mode",
            new=AsyncMock(side_effect=lambda _s, mode: iaa if mode == "IAA" else iap),
        ):
            added = asyncio.run(insert_missing_links(session, links))
        lock_sql = str(calls[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("FOR UPDATE", lock_sql)
        self.assertEqual(added, 1)
        fresh = list(session.add_all.call_args.args[0])
        self.assertEqual(len(fresh), 1)
        self.assertEqual((fresh[0].promotion_id, fresh[0].theater_app_id), (3, 22))


if __name__ == "__main__":
    unittest.main()
