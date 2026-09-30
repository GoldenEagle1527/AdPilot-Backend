"""全域漫剧机器人规则的入参、保存和开关。目录用测试里的假平台、假模板。"""

from __future__ import annotations

import ast
import asyncio
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import CheckConstraint

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.uni_robot.crud import name_taken_stmt
from app.modules.uni_robot.model import RuleKind, UniRobotRule
from app.modules.uni_robot.port import UniRobotCatalog
from app.modules.uni_robot.schema import DramaRuleWrite, LinkRuleWrite
from app.modules.uni_robot.service import create_drama_rule, create_link_rule, set_rule_enabled
from tests.modules.uni_robot.fake_catalog import FAKE_PLATFORMS, FAKE_TEMPLATES, FakeUniRobotCatalog

CREATED = datetime(2026, 9, 30, 9, 30, tzinfo=BEIJING)
BACKEND = Path(__file__).resolve().parents[3]


class FakeResult:
    """假 execute 结果。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None


class FakeSession:
    """假会话：execute 按顺序吐预置结果。"""

    def __init__(self, results: list[list[Any]] | None = None) -> None:
        self.results = list(results or [])
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。用尽后给空结果。"""
        rows = self.results.pop(0) if self.results else []
        return FakeResult(rows)

    def add(self, row: Any) -> None:
        """记下待插入行。"""
        self.added.append(row)

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1

    async def refresh(self, row: Any) -> None:
        """补上库里才有的主键和时间。"""
        row.id = row.id or 40
        row.created_date = row.created_date or CREATED
        row.updated_date = CREATED


def link_body(**kwargs: Any) -> LinkRuleWrite:
    """一份合法的按推广链接入参。模板和平台都来自假目录。"""
    data: dict[str, Any] = {
        "name": " 按链接 ",
        "template_id": FAKE_TEMPLATES[0].id,
        "platform_id": FAKE_PLATFORMS[0].id,
        "schedule_hour": 9,
        "schedule_minute": 30,
    }
    data.update(kwargs)
    return LinkRuleWrite(**data)


def drama_body(**kwargs: Any) -> DramaRuleWrite:
    """一份合法的按剧条件入参。"""
    data: dict[str, Any] = {
        "name": " 按剧 ",
        "template_id": FAKE_TEMPLATES[1].id,
        "platform_id": FAKE_PLATFORMS[1].id,
        "schedule_hour": 18,
        "schedule_minute": 5,
        "is_enabled": True,
        "stat_span": "yesterday",
        "cost_min": "10.00",
        "cost_max": "80.50",
        "recovery_min": "20",
        "recovery_max": "90.5",
    }
    data.update(kwargs)
    return DramaRuleWrite(**data)


class CatalogBoundaryTests(unittest.TestCase):
    def test_fake_catalog_satisfies_the_port(self) -> None:
        """假目录长得像业务端口，但不住在 app 包里。"""
        catalog = FakeUniRobotCatalog()
        self.assertIsInstance(catalog, UniRobotCatalog)
        self.assertFalse(FakeUniRobotCatalog.__module__.startswith("app."))

    def test_fake_ids_are_not_the_seeded_theater_platforms(self) -> None:
        """假平台避开已灌库的番茄 1 和鸥溪 22。"""
        ids = {row.id for row in FAKE_PLATFORMS}
        self.assertTrue(ids.isdisjoint({1, 22}))

    def test_business_package_does_not_import_the_fake(self) -> None:
        """业务模块、应用入口、迁移环境都不引用假目录。"""
        roots = [
            BACKEND / "app" / "modules" / "uni_robot",
            BACKEND / "main.py",
            BACKEND / "alembic" / "env.py",
        ]
        files: list[Path] = []
        for root in roots:
            files.extend(root.rglob("*.py") if root.is_dir() else [root])
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    modules.append(node.module)
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                for name in modules:
                    self.assertNotIn("fake_catalog", name, path.name)
                    self.assertNotIn("tests.modules.uni_robot", name, path.name)

    def test_startup_does_not_mount_a_robot_route(self) -> None:
        """这一轮不挂 HTTP。迁移环境只导入模型。"""
        main_text = (BACKEND / "main.py").read_text(encoding="utf-8")
        env_text = (BACKEND / "alembic" / "env.py").read_text(encoding="utf-8")
        self.assertNotIn("uni_robot", main_text)
        self.assertIn("app.modules.uni_robot.model", env_text)
        self.assertNotIn("fake_catalog", env_text)

    def test_only_the_two_live_rule_kinds_exist(self) -> None:
        """只存按推广链接和按剧条件。"""
        self.assertEqual(
            set(RuleKind),
            {RuleKind.PROMOTION_LINK, RuleKind.DRAMA_CONDITION},
        )


class BodyTests(unittest.TestCase):
    def test_link_rule_strips_name_and_defaults_the_cap_and_switch(self) -> None:
        """名称去空白。素材上限默认 800，开关默认关。"""
        body = link_body()
        self.assertEqual(body.name, "按链接")
        self.assertEqual(body.max_videos_per_series, 800)
        self.assertFalse(body.is_enabled)

    def test_link_rule_rejects_drama_fields(self) -> None:
        """按推广链接不收统计时间和区间。"""
        with self.assertRaises(ValidationError):
            link_body(stat_span="today", cost_min="1", cost_max="2")

    def test_hour_and_minute_stay_inside_a_day(self) -> None:
        """小时只到 23，分钟只到 59。"""
        with self.assertRaises(ValidationError):
            link_body(schedule_hour=24)
        with self.assertRaises(ValidationError):
            link_body(schedule_minute=60)

    def test_drama_rule_keeps_the_ranges(self) -> None:
        """按剧条件收下当天/昨天、消耗区间和回收率区间。"""
        body = drama_body(stat_span="today")
        self.assertEqual(body.stat_span, "today")
        self.assertEqual(body.cost_min, Decimal("10.00"))
        self.assertEqual(body.cost_max, Decimal("80.50"))
        self.assertEqual(body.recovery_min, Decimal("20"))
        self.assertEqual(body.recovery_max, Decimal("90.5"))
        self.assertTrue(body.is_enabled)

    def test_drama_range_cannot_run_backwards(self) -> None:
        """消耗或回收率下限大于上限则拒。"""
        with self.assertRaises(ValidationError):
            drama_body(cost_min="9", cost_max="1")
        with self.assertRaises(ValidationError):
            drama_body(recovery_min="80", recovery_max="10")

    def test_drama_stat_span_is_today_or_yesterday(self) -> None:
        """统计时间没有第三种。"""
        with self.assertRaises(ValidationError):
            drama_body(stat_span="week")

    def test_equal_bounds_are_allowed(self) -> None:
        """区间两端相等可以。"""
        body = drama_body(cost_min="5", cost_max="5", recovery_min="1", recovery_max="1")
        self.assertEqual(body.cost_min, body.cost_max)


class ShapeTests(unittest.TestCase):
    def test_check_keeps_link_rows_free_of_ranges(self) -> None:
        """库约束要求按推广链接的条件列为空，按剧条件必须带区间。"""
        checks = [
            constraint.sqltext.text
            for constraint in UniRobotRule.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        ]
        shape = next(item for item in checks if "promotion_link" in item)
        self.assertIn("stat_span IS NULL", shape)
        self.assertIn("drama_condition", shape)
        self.assertIn("cost_min <= cost_max", shape)
        self.assertIn("recovery_min <= recovery_max", shape)

    def test_name_lookup_is_per_kind_and_ignores_deleted_rows(self) -> None:
        """重名只在同一种未删除规则里算。"""
        sql = str(
            name_taken_stmt(RuleKind.DRAMA_CONDITION, "按剧", None).compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        self.assertIn("uni_robot_rule.rule_kind = 'drama_condition'", sql)
        self.assertIn("uni_robot_rule.name = '按剧'", sql)
        self.assertIn("uni_robot_rule.is_deleted = 0", sql)


class SaveTests(unittest.TestCase):
    def test_link_rule_stores_ids_from_the_port(self) -> None:
        """保存的模板 id 和平台 id 是端口交回的，条件列为空。"""
        session = FakeSession()
        catalog = FakeUniRobotCatalog()
        row = asyncio.run(create_link_rule(session, catalog, link_body(max_videos_per_series=100)))
        self.assertEqual(row.rule_kind, RuleKind.PROMOTION_LINK)
        self.assertEqual(row.template_id, FAKE_TEMPLATES[0].id)
        self.assertEqual(row.platform_id, FAKE_PLATFORMS[0].id)
        self.assertEqual(catalog.template_calls, [FAKE_TEMPLATES[0].id])
        self.assertEqual(catalog.platform_calls, [FAKE_PLATFORMS[0].id])
        self.assertEqual(row.max_videos_per_series, 100)
        self.assertEqual((row.schedule_hour, row.schedule_minute), (9, 30))
        self.assertFalse(row.is_enabled)
        self.assertIsNone(row.stat_span)
        self.assertIsNone(row.cost_min)
        self.assertIsNone(row.recovery_max)
        self.assertEqual(session.commits, 1)
        self.assertEqual(session.added, [row])

    def test_unknown_template_is_rejected_before_insert(self) -> None:
        """假目录里没有的模板 id 不落库，也不再去问平台。"""
        session = FakeSession()
        catalog = FakeUniRobotCatalog()
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_link_rule(session, catalog, link_body(template_id=1)))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "全域模板不存在")
        self.assertEqual(catalog.platform_calls, [])
        self.assertEqual(session.added, [])
        self.assertEqual(session.commits, 0)

    def test_unknown_platform_is_rejected(self) -> None:
        """假目录里没有的平台 id 不落库。真实番茄 id 也不在假目录里。"""
        session = FakeSession()
        catalog = FakeUniRobotCatalog()
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_drama_rule(session, catalog, drama_body(platform_id=1)))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "剧场平台不存在")
        self.assertEqual(session.added, [])

    def test_drama_rule_stores_span_and_ranges(self) -> None:
        """按剧条件把统计时间、消耗和回收率写进行。"""
        session = FakeSession()
        row = asyncio.run(create_drama_rule(session, FakeUniRobotCatalog(), drama_body()))
        self.assertEqual(row.rule_kind, RuleKind.DRAMA_CONDITION)
        self.assertEqual(row.template_id, FAKE_TEMPLATES[1].id)
        self.assertEqual(row.platform_id, FAKE_PLATFORMS[1].id)
        self.assertEqual(row.stat_span, "yesterday")
        self.assertEqual(row.cost_min, Decimal("10.00"))
        self.assertEqual(row.cost_max, Decimal("80.50"))
        self.assertEqual(row.recovery_min, Decimal("20"))
        self.assertEqual(row.recovery_max, Decimal("90.5"))
        self.assertEqual(row.max_videos_per_series, 800)
        self.assertTrue(row.is_enabled)
        self.assertEqual((row.schedule_hour, row.schedule_minute), (18, 5))

    def test_duplicate_name_is_a_conflict(self) -> None:
        """同类型重名是 409，不插入。"""
        session = FakeSession([[5]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_link_rule(session, FakeUniRobotCatalog(), link_body()))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(session.added, [])

    def test_switch_flips_an_existing_rule(self) -> None:
        """开关只改 is_enabled。"""
        current = UniRobotRule(
            rule_kind=RuleKind.PROMOTION_LINK,
            name="按链接",
            template_id=FAKE_TEMPLATES[0].id,
            platform_id=FAKE_PLATFORMS[0].id,
            max_videos_per_series=800,
            schedule_hour=9,
            schedule_minute=30,
            is_enabled=False,
        )
        current.id = 7
        session = FakeSession([[current]])
        row = asyncio.run(set_rule_enabled(session, 7, True))
        self.assertTrue(row.is_enabled)
        self.assertEqual(row.schedule_hour, 9)
        self.assertEqual(session.commits, 1)

    def test_missing_rule_cannot_be_switched(self) -> None:
        """没有这条规则时开关是 404。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(set_rule_enabled(session, 7, True))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.commits, 0)
