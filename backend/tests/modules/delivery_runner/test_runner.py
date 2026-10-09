"""到点判断用传入的时钟。不睡一天，也不在执行器里发明巨量视频号。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.core.times import BEIJING
from app.modules.delivery_runner.due import (
    album_url_for_playlet,
    publish_on_day,
    robot_is_due,
    series_block_reason,
    snapshots_satisfy,
    span_day,
    standard_is_due,
)
from app.modules.delivery_runner.loop import run_due_rules
from app.modules.delivery_runner.robot import uni_task_body

ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 10, 9, 9, 0, tzinfo=BEIJING)


class ClockTests(unittest.TestCase):
    def test_immediate_runs_once_and_future_schedule_waits(self) -> None:
        """没有预约且还没跑过就是到点。预约未到不算到点。跑过一次就不再到点。"""
        self.assertTrue(
            standard_is_due(is_enabled=True, schedule_start=None, ran_at=None, now=NOW)
        )
        self.assertFalse(
            standard_is_due(is_enabled=False, schedule_start=None, ran_at=None, now=NOW)
        )
        self.assertFalse(
            standard_is_due(is_enabled=True, schedule_start=None, ran_at=NOW, now=NOW)
        )
        later = datetime(2026, 10, 9, 11, 0, tzinfo=BEIJING)
        earlier = datetime(2026, 10, 9, 8, 0, tzinfo=BEIJING)
        self.assertFalse(
            standard_is_due(is_enabled=True, schedule_start=later, ran_at=None, now=NOW)
        )
        self.assertTrue(
            standard_is_due(is_enabled=True, schedule_start=earlier, ran_at=None, now=NOW)
        )
        self.assertFalse(
            standard_is_due(is_enabled=True, schedule_start=earlier, ran_at=NOW, now=NOW)
        )

    def test_robot_uses_the_saved_minute_without_sleeping(self) -> None:
        """没到时分不算到点。到了且今天没跑过才算。关掉的不跑。"""
        before = datetime(2026, 10, 9, 8, 59, tzinfo=BEIJING)
        self.assertFalse(
            robot_is_due(
                is_enabled=True, schedule_hour=9, schedule_minute=0, ran_today=False, now=before
            )
        )
        self.assertTrue(
            robot_is_due(
                is_enabled=True, schedule_hour=9, schedule_minute=0, ran_today=False, now=NOW
            )
        )
        self.assertFalse(
            robot_is_due(
                is_enabled=True, schedule_hour=9, schedule_minute=0, ran_today=True, now=NOW
            )
        )
        self.assertFalse(
            robot_is_due(
                is_enabled=False, schedule_hour=9, schedule_minute=0, ran_today=False, now=NOW
            )
        )

    def test_due_runner_receives_the_test_clock(self) -> None:
        """调度函数把调用方给的时间交下去，不另取当前时间。"""
        seen: list[datetime] = []

        async def _standard(_session, now: datetime) -> int:
            seen.append(now)
            return 1

        async def _robot(_session, now: datetime) -> int:
            seen.append(now)
            return 2

        with (
            patch("app.modules.delivery_runner.loop.run_due_standard", new=AsyncMock(side_effect=_standard)),
            patch("app.modules.delivery_runner.loop.run_due_robots", new=AsyncMock(side_effect=_robot)),
        ):
            result = asyncio.run(run_due_rules(object(), now=NOW))
        self.assertEqual(seen, [NOW, NOW])
        self.assertEqual(result, {"standard": 1, "robot": 2})


class SelectionTests(unittest.TestCase):
    def test_missing_videos_is_a_series_failure(self) -> None:
        """没有视频就记下失败原因，不往下提交。"""
        reason = series_block_reason(
            videos=[],
            titles=[1],
            accounts=[9],
            playlet_id=88,
            publish_ok=True,
            snapshot_ok=True,
        )
        self.assertEqual(reason, "这部剧没有视频素材")
        ready = series_block_reason(
            videos=[3],
            titles=[1],
            accounts=[9],
            playlet_id=88,
            publish_ok=True,
            snapshot_ok=True,
        )
        self.assertIsNone(ready)

    def test_album_url_comes_from_playlet_not_a_promotion_link(self) -> None:
        """标准专辑链接用专辑 id。剧场推广链只当端原生任务的 IAA 文本。"""
        album = album_url_for_playlet(88)
        promotion = "https://theater.example/iaa"
        self.assertEqual(album, "https://www.douyin.com/playlet/88")
        self.assertNotEqual(album, promotion)
        body = uni_task_body(
            template_id=1,
            series_id=2,
            douyin_id=3,
            advertiser_id=4,
            promotion_url=promotion,
            video_ids=[5],
        )
        self.assertNotIn("album_url", body.model_dump())
        self.assertEqual(body.promotion_links[0].charge_mode, "IAA")
        self.assertEqual(body.promotion_links[0].link_text, promotion)

    def test_drama_day_and_snapshot_range(self) -> None:
        """当天、昨天按北京日期。快照对不上区间就选不中。"""
        self.assertEqual(span_day("today", NOW).isoformat(), "2026-10-09")
        self.assertEqual(span_day("yesterday", NOW).isoformat(), "2026-10-08")
        self.assertTrue(publish_on_day("2026-10-09 01:02:03", span_day("today", NOW)))
        self.assertFalse(publish_on_day("2026-10-08 01:02:03", span_day("today", NOW)))
        rows = [(Decimal("120.00"), Decimal("0.300")), (Decimal("10.00"), Decimal("1.200"))]
        self.assertTrue(
            snapshots_satisfy(
                rows,
                cost_min=Decimal("100"),
                cost_max=Decimal("200"),
                recovery_min=Decimal("20"),
                recovery_max=Decimal("40"),
            )
        )
        self.assertFalse(
            snapshots_satisfy(
                rows,
                cost_min=Decimal("500"),
                cost_max=Decimal("600"),
                recovery_min=Decimal("20"),
                recovery_max=Decimal("40"),
            )
        )

    def test_runner_uses_submit_and_record_run_not_a_fake_import(self) -> None:
        """执行器走现有提交和 record_run，不从测试假模块或假客户端类进业务。"""
        standard = (ROOT / "app" / "modules" / "delivery_runner" / "standard.py").read_text(encoding="utf-8")
        robot = (ROOT / "app" / "modules" / "delivery_runner" / "robot.py").read_text(encoding="utf-8")
        loop = (ROOT / "app" / "modules" / "delivery_runner" / "loop.py").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        for text in (standard, robot, loop):
            self.assertNotIn("tests.fakes", text)
            self.assertNotIn("FakeOceanEngineClient", text)
            self.assertNotIn("api.oceanengine.com", text)
            self.assertNotIn("upload_video", text)
        self.assertIn("submit_draft", standard)
        self.assertIn("submit_task", robot)
        self.assertIn("record_run", robot)
        self.assertNotIn("album_url", robot)
        self.assertIn("_due_rules_loop", main)
        self.assertIn("asyncio.sleep", main)
