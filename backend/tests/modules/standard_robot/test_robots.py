"""免费和付费端原生机器人的列表过滤、修改、删除和开关。不提交投放。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.standard_robot.model import StandardNativeRobotRule
from app.modules.standard_robot.schema import RobotQuery, RobotWrite
from app.modules.standard_robot.service import (
    delete_robot_rule,
    robot_filters,
    set_robot_enabled,
    update_robot_rule,
)

CREATED = datetime(2026, 10, 10, 8, tzinfo=BEIJING)


def make_rule(**kwargs: object) -> StandardNativeRobotRule:
    """一条已在库里的规则。"""
    row = StandardNativeRobotRule(
        name=kwargs.get("name", "早间"),
        charge_mode=kwargs.get("charge_mode", "IAA"),
        rule_kind=kwargs.get("rule_kind", "drama"),
        schedule_kind=kwargs.get("schedule_kind", "hourly"),
        schedule_hour=kwargs.get("schedule_hour"),
        schedule_minute=kwargs.get("schedule_minute", 15),
        template_id=kwargs.get("template_id", 4),
        pitcher_user_id=kwargs.get("pitcher_user_id", 3),
        platform_id=kwargs.get("platform_id"),
        accounts_per_series=3,
        max_videos_per_series=200,
        stat_span="today",
        cost_min=Decimal("1.00"),
        cost_max=Decimal("9.00"),
        recovery_min=Decimal("0.1000"),
        recovery_max=Decimal("0.2000"),
        is_enabled=True,
    )
    row.id = int(kwargs.get("id", 7))
    row.is_deleted = int(kwargs.get("is_deleted", 0))
    row.created_date = CREATED
    row.updated_date = CREATED
    return row


def write_body(**kwargs: object) -> RobotWrite:
    """一份合法的保存体。"""
    data = {
        "name": "改名",
        "rule_kind": "nb",
        "schedule_kind": "period",
        "schedule_hour": 9,
        "schedule_minute": 5,
        "template_id": 4,
        "is_enabled": False,
    }
    data.update(kwargs)
    return RobotWrite(**data)


def _session(row: StandardNativeRobotRule | None) -> MagicMock:
    """get 返回这条规则。"""
    session = MagicMock()
    session.get = AsyncMock(return_value=row)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


class FilterTests(unittest.TestCase):
    def _sql(self, query: RobotQuery, user_id: int = 3, charge_mode: str = "IAA") -> str:
        """把过滤条件编译成字面量 SQL。"""
        return " AND ".join(
            str(item.compile(compile_kwargs={"literal_binds": True}))
            for item in robot_filters(query, user_id, charge_mode)
        )

    def test_list_is_own_charge_mode(self) -> None:
        """免费列表只看当前投手未删除的 IAA 规则。"""
        sql = self._sql(RobotQuery(name=" 50%_早 ", is_enabled=True))
        self.assertIn("standard_native_robot_rule.is_deleted = 0", sql)
        self.assertIn("standard_native_robot_rule.charge_mode = 'IAA'", sql)
        self.assertIn("standard_native_robot_rule.pitcher_user_id = 3", sql)
        self.assertIn("standard_native_robot_rule.is_enabled = true", sql)
        self.assertIn("lower(standard_native_robot_rule.name) LIKE lower('%50\\%\\_早%')", sql)

    def test_paid_list_uses_iap(self) -> None:
        """付费列表用 IAP。"""
        sql = self._sql(RobotQuery(), charge_mode="IAP")
        self.assertIn("standard_native_robot_rule.charge_mode = 'IAP'", sql)


class ManageTests(unittest.TestCase):
    def test_update_keeps_owner_and_charge_mode(self) -> None:
        """整表保存改名称和时刻，不改所属投手指和收费模式。"""
        row = make_rule()
        session = _session(row)
        template = MagicMock()
        template.id = 4
        template.charge_mode = "IAA"
        with patch(
            "app.modules.standard_robot.service.get_template_row",
            new=AsyncMock(return_value=(template, MagicMock())),
        ):
            data = asyncio.run(update_robot_rule(session, 7, write_body(), 3, "IAA"))
        self.assertEqual(row.name, "改名")
        self.assertEqual(row.schedule_kind, "period")
        self.assertEqual(row.schedule_hour, 9)
        self.assertFalse(row.is_enabled)
        self.assertEqual(row.charge_mode, "IAA")
        self.assertEqual(row.pitcher_user_id, 3)
        self.assertEqual(data["id"], "7")
        self.assertEqual(data["rule_kind"], "nb")
        session.commit.assert_awaited()

    def test_other_owner_or_other_menu_is_missing(self) -> None:
        """别人的规则、付费规则走免费路径，都是不存在。"""
        foreign = _session(make_rule(pitcher_user_id=9))
        with self.assertRaises(ApiError) as other:
            asyncio.run(update_robot_rule(foreign, 7, write_body(), 3, "IAA"))
        self.assertEqual(other.exception.status_code, 404)
        foreign.commit.assert_not_awaited()
        paid = _session(make_rule(charge_mode="IAP"))
        with self.assertRaises(ApiError) as wrong_menu:
            asyncio.run(delete_robot_rule(paid, 7, 3, "IAA"))
        self.assertEqual(wrong_menu.exception.status_code, 404)

    def test_delete_and_switch_do_not_submit(self) -> None:
        """删除是软删；开关只改 is_enabled。"""
        row = make_rule()
        session = _session(row)
        deleted = asyncio.run(delete_robot_rule(session, 7, 3, "IAA"))
        self.assertEqual(deleted, {"id": "7", "deleted": True})
        self.assertEqual(row.is_deleted, 1)
        row.is_deleted = 0
        switched = asyncio.run(set_robot_enabled(session, 7, False, 3, "IAA"))
        self.assertFalse(row.is_enabled)
        self.assertFalse(switched["is_enabled"])
        self.assertEqual(switched["charge_mode"], "IAA")
