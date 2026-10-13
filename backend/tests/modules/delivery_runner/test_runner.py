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
            patch("app.modules.delivery_runner.loop.run_due_drafts", new=AsyncMock(return_value=0)),
            patch("app.modules.delivery_runner.loop.run_due_robots", new=AsyncMock(side_effect=_robot)),
            patch("app.modules.delivery_runner.loop.run_due_native", new=AsyncMock(return_value=0)),
        ):
            result = asyncio.run(run_due_rules(object(), now=NOW))
        self.assertEqual(seen, [NOW, NOW])
        self.assertEqual(result, {"standard": 1, "draft": 0, "robot": 2, "native": 0})


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
        self.assertEqual(body.promotion_links[0].recharge_template_name, "")

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
                recovery_min=Decimal("0.2"),
                recovery_max=Decimal("0.4"),
            )
        )
        self.assertFalse(
            snapshots_satisfy(
                rows,
                cost_min=Decimal("500"),
                cost_max=Decimal("600"),
                recovery_min=Decimal("0.2"),
                recovery_max=Decimal("0.4"),
            )
        )

    def test_robot_without_videos_leaves_a_failed_task(self) -> None:
        """没视频时建一条失败任务，不带视频，不提交。执行记录的原因和任务上同一句。"""
        from app.modules.account.model import AdvertiserAccount, DouyinAccount
        from app.modules.material.model import ManhuaSeries
        from app.modules.standard_delivery.model import DeliveryTemplate
        from app.modules.uni_native_task.model import (
            UniNativeTask,
            UniNativeTaskAccount,
            UniNativeTaskLink,
            UniNativeTaskVideo,
        )
        from app.modules.uni_robot.model import UniRobotRule

        template = DeliveryTemplate(
            name="全域甲",
            delivery_mode="uni",
            charge_mode="IAA",
            subject_id=7,
            bid_panels=[],
            project_budget=Decimal("100.00"),
            roi_coefficient=Decimal("1.200"),
        )
        template.id = 11
        template.is_deleted = 0
        rule = UniRobotRule(name="机器人甲", rule_kind="promotion_link", template_id=11, max_videos_per_series=200)
        rule.id = 5
        rule.platform_id = 2
        rule.pitcher_user_id = 3
        series = ManhuaSeries(book_name="甲壳虫")
        series.id = 8
        douyin = DouyinAccount(aweme_id="aweme-u", name="全域号", delivery_mode="uni", enabled=True)
        douyin.id = 4
        account = AdvertiserAccount(
            organization_id=1, oe_app_id=1, advertiser_id=90001, name="户", sync_status="active", pitcher_user_id=3
        )
        account.id = 31

        class Session:
            def __init__(self) -> None:
                self.added: list[object] = []
                self.commits = 0

            async def get(self, _model, _pk):
                return template

            def add(self, row) -> None:
                self.added.append(row)

            async def flush(self) -> None:
                for row in self.added:
                    if getattr(row, "id", None) is None:
                        row.id = 70

            async def execute(self, _statement):
                return None

            async def commit(self) -> None:
                self.commits += 1

        session = Session()
        create = AsyncMock()
        submit = AsyncMock()
        record = AsyncMock()
        with (
            patch(
                "app.modules.delivery_runner.robot._promotion_series",
                new=AsyncMock(return_value=[(series, "https://iaa.example/a")]),
            ),
            patch(
                "app.modules.delivery_runner.robot._pitcher_pair",
                new=AsyncMock(return_value=(3, douyin, account)),
            ),
            patch("app.modules.delivery_runner.robot._videos", new=AsyncMock(return_value=[])),
            patch("app.modules.delivery_runner.robot.record_run", new=record),
            patch("app.modules.uni_native_task.service.create_task", new=create),
            patch("app.modules.uni_native_task.submit.submit_task", new=submit),
        ):
            from app.modules.delivery_runner.robot import execute_robot_rule

            asyncio.run(execute_robot_rule(session, rule, NOW))
        create.assert_not_awaited()
        submit.assert_not_awaited()
        tasks = [row for row in session.added if isinstance(row, UniNativeTask)]
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.failure_reason, "这部剧没有视频素材")
        self.assertFalse(task.materials_uploaded)
        self.assertEqual((task.series_id, task.template_id, task.pitcher_user_id), (8, 11, 3))
        self.assertFalse(any(isinstance(row, UniNativeTaskVideo) for row in session.added))
        stored_links = [row for row in session.added if isinstance(row, UniNativeTaskLink)]
        self.assertEqual(
            [(row.charge_mode, row.link_text, row.recharge_template_name) for row in stored_links],
            [("IAA", "https://iaa.example/a", "")],
        )
        self.assertEqual(len([row for row in session.added if isinstance(row, UniNativeTaskAccount)]), 1)
        failures = record.await_args.kwargs["failures"]
        self.assertEqual([item.reason for item in failures], ["这部剧没有视频素材"])
        self.assertEqual(record.await_args.kwargs["status"], "failed")

    def test_robot_submits_once_without_requiring_template_douyin(self) -> None:
        """有视频时只创建一次再提交一次，不要求抖音号已经挂到模板上。"""
        from app.modules.account.model import AdvertiserAccount, DouyinAccount
        from app.modules.material.model import ManhuaSeries
        from app.modules.standard_delivery.model import DeliveryTemplate
        from app.modules.uni_robot.model import UniRobotRule

        template = DeliveryTemplate(
            name="全域甲",
            delivery_mode="uni",
            charge_mode="IAA",
            subject_id=7,
            bid_panels=[],
            project_budget=Decimal("100.00"),
            roi_coefficient=Decimal("1.200"),
        )
        template.id = 11
        template.is_deleted = 0
        rule = UniRobotRule(name="机器人甲", rule_kind="promotion_link", template_id=11, max_videos_per_series=200)
        rule.id = 5
        rule.platform_id = 2
        rule.pitcher_user_id = 3
        series = ManhuaSeries(book_name="甲壳虫")
        series.id = 8
        douyin = DouyinAccount(aweme_id="aweme-u", name="全域号", delivery_mode="uni", enabled=True)
        douyin.id = 4
        account = AdvertiserAccount(
            organization_id=1, oe_app_id=1, advertiser_id=90001, name="户", sync_status="active", pitcher_user_id=3
        )
        account.id = 31
        create = AsyncMock(return_value={"id": "41"})
        submit = AsyncMock()
        record = AsyncMock()

        class Session:
            async def get(self, _model, _pk):
                return template

            async def commit(self) -> None:
                return None

        with (
            patch(
                "app.modules.delivery_runner.robot._promotion_series",
                new=AsyncMock(return_value=[(series, "https://iaa.example/a")]),
            ),
            patch(
                "app.modules.delivery_runner.robot._pitcher_pair",
                new=AsyncMock(return_value=(3, douyin, account)),
            ),
            patch("app.modules.delivery_runner.robot._videos", new=AsyncMock(return_value=[15])),
            patch("app.modules.delivery_runner.robot.record_run", new=record),
            patch("app.modules.uni_native_task.service.create_task", new=create),
            patch("app.modules.uni_native_task.submit.submit_task", new=submit),
        ):
            from app.modules.delivery_runner.robot import execute_robot_rule

            asyncio.run(execute_robot_rule(Session(), rule, NOW))
        create.assert_awaited_once()
        submit.assert_awaited_once()
        self.assertFalse(create.await_args.kwargs.get("require_template_assignment", False))
        self.assertEqual(submit.await_args.args[1], 41)
        self.assertEqual(record.await_args.kwargs["status"], "success")

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
        self.assertNotIn("require_template_assignment=True", robot)
        self.assertIn("record_run", robot)
        self.assertNotIn("album_url", robot)
        self.assertIn("_due_rules_loop", main)
        self.assertIn("asyncio.sleep", main)
