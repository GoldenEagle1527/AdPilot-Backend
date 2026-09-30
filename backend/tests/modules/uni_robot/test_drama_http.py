"""按剧条件规则的 HTTP。目录用测试里的假实现，不进应用启动。"""

from __future__ import annotations

import unittest
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.modules.uni_robot.crud import drama_page_stmt, get_drama_rule_stmt, name_taken_stmt
from app.modules.uni_robot.model import RuleKind, UniRobotRule
from app.modules.uni_robot.schema import DramaRuleQuery
from app.modules.uni_robot.service import drama_filters
from tests.modules.uni_robot.fake_catalog import FAKE_PLATFORMS, FAKE_TEMPLATES, FakeUniRobotCatalog
from tests.modules.uni_robot.test_link_http import http_client
from tests.modules.uni_robot.test_rules import CREATED, FakeSession

PREFIX = "/api/v1/uni-robot/drama-rules"


def live_drama(**kwargs: Any) -> UniRobotRule:
    """一条已在库里的按剧条件规则。"""
    row = UniRobotRule(
        rule_kind=kwargs.pop("rule_kind", RuleKind.DRAMA_CONDITION),
        name=kwargs.pop("name", "按剧"),
        template_id=kwargs.pop("template_id", FAKE_TEMPLATES[1].id),
        platform_id=kwargs.pop("platform_id", FAKE_PLATFORMS[1].id),
        max_videos_per_series=kwargs.pop("max_videos_per_series", 800),
        schedule_hour=kwargs.pop("schedule_hour", 18),
        schedule_minute=kwargs.pop("schedule_minute", 5),
        is_enabled=kwargs.pop("is_enabled", True),
    )
    row.id = kwargs.pop("id", 7)
    row.is_deleted = kwargs.pop("is_deleted", 0)
    row.created_date = CREATED
    row.updated_date = CREATED
    row.stat_span = kwargs.pop("stat_span", "yesterday")
    row.cost_min = kwargs.pop("cost_min", Decimal("10.00"))
    row.cost_max = kwargs.pop("cost_max", Decimal("80.50"))
    row.recovery_min = kwargs.pop("recovery_min", Decimal("20"))
    row.recovery_max = kwargs.pop("recovery_max", Decimal("90.5"))
    return row


def write_body(**kwargs: Any) -> dict[str, Any]:
    """一份合法的按剧条件请求体。素材上限和开关走默认。"""
    data: dict[str, Any] = {
        "name": "按剧",
        "template_id": FAKE_TEMPLATES[1].id,
        "platform_id": FAKE_PLATFORMS[1].id,
        "schedule_hour": 18,
        "schedule_minute": 5,
        "stat_span": "yesterday",
        "cost_min": "10.00",
        "cost_max": "80.50",
        "recovery_min": "20",
        "recovery_max": "90.5",
    }
    data.update(kwargs)
    return data


class QueryShapeTests(unittest.TestCase):
    def test_list_sql_is_only_live_drama_rules(self) -> None:
        """列表只查未删除的按剧条件，按创建时间倒序。"""
        sql = str(
            drama_page_stmt(drama_filters(DramaRuleQuery()), offset=0, limit=20).compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        self.assertIn("drama_condition", sql)
        self.assertNotIn("promotion_link", sql)
        self.assertIn("is_deleted = 0", sql)
        self.assertIn("created_date DESC", sql)

    def test_blank_name_does_not_filter(self) -> None:
        """空白名称当没传。百分号按字面量。"""
        blank = str(
            select(UniRobotRule)
            .where(*drama_filters(DramaRuleQuery(name="  ")))
            .compile(compile_kwargs={"literal_binds": True})
        )
        self.assertNotIn("LIKE", blank.upper())
        named = str(
            select(UniRobotRule)
            .where(*drama_filters(DramaRuleQuery(name="100%", is_enabled=False)))
            .compile(compile_kwargs={"literal_binds": True})
        )
        self.assertIn("100\\%", named)
        self.assertIn("is_enabled = false", named)

    def test_get_sql_excludes_link_rules(self) -> None:
        """单条查询带规则类型，按推广链接不会被取出来。"""
        sql = str(get_drama_rule_stmt(7).compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("uni_robot_rule.id = 7", sql)
        self.assertIn("drama_condition", sql)
        self.assertIn("is_deleted = 0", sql)
        self.assertNotIn("promotion_link", sql)

    def test_rename_check_ignores_the_row_itself(self) -> None:
        """整表保存时，自己原来的名字不算重名。"""
        sql = str(
            name_taken_stmt(RuleKind.DRAMA_CONDITION, "按剧", 7).compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        self.assertIn("uni_robot_rule.id != 7", sql)
        self.assertIn("drama_condition", sql)


class DramaHttpTests(unittest.TestCase):
    def test_missing_token_is_unauthorized(self) -> None:
        """没登录不能列规则。"""
        client = http_client(FakeSession(), None, login=False)
        res = client.get(PREFIX)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body["code"], 401)
        self.assertEqual(body["message"], "未带或 Token 无效")
        self.assertIsNone(body["data"])

    def test_create_stores_port_ids_and_ranges(self) -> None:
        """新建走目录端口。出参带统计时间和两个区间，素材上限默认 800。"""
        session = FakeSession()
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.post(PREFIX, json=write_body(name="  按剧  "))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["id"], "40")
        self.assertEqual(data["name"], "按剧")
        self.assertEqual(data["template_id"], str(FAKE_TEMPLATES[1].id))
        self.assertEqual(data["platform_id"], str(FAKE_PLATFORMS[1].id))
        self.assertEqual(data["max_videos_per_series"], 800)
        self.assertEqual(data["schedule_hour"], 18)
        self.assertEqual(data["schedule_minute"], 5)
        self.assertFalse(data["is_enabled"])
        self.assertEqual(data["stat_span"], "yesterday")
        self.assertEqual(data["cost_min"], "10.00")
        self.assertEqual(data["cost_max"], "80.50")
        self.assertEqual(data["recovery_min"], "20.0000")
        self.assertEqual(data["recovery_max"], "90.5000")
        self.assertEqual(data["created_at"], "2026-09-30T09:30:00+08:00")
        row = session.added[0]
        self.assertEqual(row.rule_kind, RuleKind.DRAMA_CONDITION)
        self.assertEqual(row.stat_span, "yesterday")
        self.assertEqual(row.cost_min, Decimal("10.00"))
        self.assertEqual(row.recovery_max, Decimal("90.5"))
        self.assertEqual(catalog.template_calls, [FAKE_TEMPLATES[1].id])
        self.assertEqual(catalog.platform_calls, [FAKE_PLATFORMS[1].id])
        self.assertEqual(session.commits, 1)

    def test_create_rejects_unknown_catalog_ids_and_bad_ranges(self) -> None:
        """假目录没有的模板或平台不落库。缺区间、区间颠倒、统计时间写错都是 422。"""
        session = FakeSession()
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        missing_template = client.post(PREFIX, json=write_body(template_id=1))
        self.assertEqual(missing_template.status_code, 400)
        self.assertEqual(missing_template.json()["message"], "全域模板不存在")
        self.assertEqual(catalog.platform_calls, [])
        missing_platform = client.post(PREFIX, json=write_body(platform_id=1))
        self.assertEqual(missing_platform.status_code, 400)
        self.assertEqual(missing_platform.json()["message"], "剧场平台不存在")
        incomplete = dict(write_body())
        incomplete.pop("cost_min")
        missing_range = client.post(PREFIX, json=incomplete)
        self.assertEqual(missing_range.status_code, 422)
        self.assertIn("cost_min", missing_range.json()["message"])
        backwards = client.post(PREFIX, json=write_body(cost_min="9", cost_max="1"))
        self.assertEqual(backwards.status_code, 422)
        self.assertIn("消耗区间的下限不能大于上限", backwards.json()["message"])
        span = client.post(PREFIX, json=write_body(stat_span="week"))
        self.assertEqual(span.status_code, 422)
        self.assertIn("stat_span", span.json()["message"])
        extra = client.post(PREFIX, json=write_body(book_id=3))
        self.assertEqual(extra.status_code, 422)
        self.assertEqual(session.added, [])

    def test_create_without_catalog_does_not_insert(self) -> None:
        """没注入目录时，新建不能确认模板，也不落库。"""
        session = FakeSession()
        client = http_client(session, None)
        res = client.post(PREFIX, json=write_body())
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()["message"], "全域目录尚未接入")
        self.assertEqual(session.added, [])
        self.assertEqual(session.commits, 0)

    def test_duplicate_name_is_conflict(self) -> None:
        """同类型重名是 409。"""
        session = FakeSession([[5]])
        client = http_client(session, FakeUniRobotCatalog())
        res = client.post(PREFIX, json=write_body())
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["message"], "规则名称已存在")
        self.assertEqual(session.added, [])

    def test_list_get_and_empty_page(self) -> None:
        """列表和单条走信封。空页是空数组。多传查询参数拒绝。"""
        row = live_drama()
        session = FakeSession([[1], [row], [row]])
        client = http_client(session, None)
        listed = client.get(PREFIX, params={"name": "按剧", "is_enabled": "true"})
        self.assertEqual(listed.status_code, 200)
        page = listed.json()["data"]
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["page"], 1)
        self.assertEqual(page["page_size"], 20)
        self.assertEqual(page["list"][0]["id"], "7")
        self.assertEqual(page["list"][0]["stat_span"], "yesterday")
        self.assertEqual(page["list"][0]["cost_min"], "10.00")
        self.assertEqual(page["list"][0]["recovery_max"], "90.5000")
        one = client.get(f"{PREFIX}/7")
        self.assertEqual(one.status_code, 200)
        self.assertEqual(one.json()["data"]["name"], "按剧")
        empty = http_client(FakeSession([[0], []]), None).get(PREFIX)
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["data"]["list"], [])
        self.assertEqual(empty.json()["data"]["total"], 0)
        rejected = client.get(PREFIX, params={"cost_min": "1"})
        self.assertEqual(rejected.status_code, 422)

    def test_full_update_rewrites_ranges(self) -> None:
        """整表保存再次问目录，并改写统计时间和两个区间。"""
        row = live_drama()
        session = FakeSession([[row], []])
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.put(
            f"{PREFIX}/7",
            json=write_body(
                name="新名称",
                template_id=FAKE_TEMPLATES[0].id,
                platform_id=FAKE_PLATFORMS[0].id,
                max_videos_per_series=20,
                schedule_hour=8,
                schedule_minute=15,
                is_enabled=False,
                stat_span="today",
                cost_min="1.5",
                cost_max="2",
                recovery_min="0",
                recovery_max="1",
            ),
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["name"], "新名称")
        self.assertEqual(data["template_id"], str(FAKE_TEMPLATES[0].id))
        self.assertEqual(data["platform_id"], str(FAKE_PLATFORMS[0].id))
        self.assertEqual(data["max_videos_per_series"], 20)
        self.assertEqual((data["schedule_hour"], data["schedule_minute"]), (8, 15))
        self.assertFalse(data["is_enabled"])
        self.assertEqual(data["stat_span"], "today")
        self.assertEqual(data["cost_min"], "1.50")
        self.assertEqual(data["cost_max"], "2.00")
        self.assertEqual(data["recovery_min"], "0.0000")
        self.assertEqual(data["recovery_max"], "1.0000")
        self.assertEqual(row.rule_kind, RuleKind.DRAMA_CONDITION)
        self.assertEqual(row.stat_span, "today")
        self.assertEqual(catalog.template_calls, [FAKE_TEMPLATES[0].id])
        self.assertEqual(session.commits, 1)

    def test_update_unknown_template_does_not_save(self) -> None:
        """模板不在目录里时，整表保存不写库，也不再问平台。"""
        row = live_drama()
        session = FakeSession([[row]])
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.put(f"{PREFIX}/7", json=write_body(template_id=1))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(row.name, "按剧")
        self.assertEqual(row.cost_min, Decimal("10.00"))
        self.assertEqual(catalog.platform_calls, [])
        self.assertEqual(session.commits, 0)

    def test_update_without_catalog_does_not_save(self) -> None:
        """没注入目录时，整表保存不写库。"""
        row = live_drama()
        session = FakeSession([[row]])
        client = http_client(session, None)
        res = client.put(f"{PREFIX}/7", json=write_body())
        self.assertEqual(res.status_code, 503)
        self.assertEqual(row.name, "按剧")
        self.assertEqual(session.commits, 0)

    def test_update_duplicate_name_is_conflict(self) -> None:
        """改成已有名称是 409，原行不动。"""
        row = live_drama()
        session = FakeSession([[row], [9]])
        client = http_client(session, FakeUniRobotCatalog())
        res = client.put(f"{PREFIX}/7", json=write_body(name="别的"))
        self.assertEqual(res.status_code, 409)
        self.assertEqual(row.name, "按剧")
        self.assertEqual(session.commits, 0)

    def test_update_rejects_a_partial_body(self) -> None:
        """整表替换缺区间是 422，原行不动。"""
        row = live_drama()
        session = FakeSession([[row]])
        client = http_client(session, FakeUniRobotCatalog())
        body = write_body()
        body.pop("recovery_max")
        res = client.put(f"{PREFIX}/7", json=body)
        self.assertEqual(res.status_code, 422)
        self.assertIn("recovery_max", res.json()["message"])
        self.assertEqual(row.recovery_max, Decimal("90.5"))
        self.assertEqual(session.commits, 0)

    def test_link_row_is_not_on_this_resource(self) -> None:
        """按推广链接即使被取回来，这条资源也当不存在，并且不改它。"""
        row = live_drama(
            rule_kind=RuleKind.PROMOTION_LINK,
            name="按链接",
            is_enabled=False,
            stat_span=None,
            cost_min=None,
            cost_max=None,
            recovery_min=None,
            recovery_max=None,
        )
        session = FakeSession([[row], [row], [row], [row], [row]])
        client = http_client(session, FakeUniRobotCatalog())
        for call in (
            lambda: client.get(f"{PREFIX}/7"),
            lambda: client.put(f"{PREFIX}/7", json=write_body(name="改掉")),
            lambda: client.delete(f"{PREFIX}/7"),
            lambda: client.patch(f"{PREFIX}/7/switch", json={"is_enabled": True}),
            lambda: client.patch(f"{PREFIX}/7/schedule", json={"schedule_hour": 1, "schedule_minute": 2}),
        ):
            res = call()
            self.assertEqual(res.status_code, 404)
            self.assertEqual(res.json()["message"], "规则不存在")
        self.assertEqual(row.name, "按链接")
        self.assertFalse(row.is_enabled)
        self.assertIsNone(row.stat_span)
        self.assertEqual(session.commits, 0)

    def test_deleted_row_is_not_found(self) -> None:
        """已软删的按剧条件不再出现，也不再改。"""
        row = live_drama(is_deleted=1)
        session = FakeSession([[row]])
        client = http_client(session, None)
        res = client.get(f"{PREFIX}/7")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(session.commits, 0)

    def test_soft_delete_hides_the_rule(self) -> None:
        """删除是软删。"""
        row = live_drama()
        session = FakeSession([[row]])
        client = http_client(session, None)
        res = client.delete(f"{PREFIX}/7")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"], {"id": "7", "deleted": True})
        self.assertEqual(row.is_deleted, 1)
        self.assertIsNotNone(row.deleted_at)
        self.assertEqual(session.commits, 1)

    def test_switch_only_flips_enabled(self) -> None:
        """开关不改时分和区间，也不问目录。"""
        row = live_drama(is_enabled=False)
        session = FakeSession([[row]])
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.patch(f"{PREFIX}/7/switch", json={"is_enabled": True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["data"]["is_enabled"])
        self.assertEqual(res.json()["data"]["schedule_hour"], 18)
        self.assertEqual(res.json()["data"]["cost_min"], "10.00")
        self.assertTrue(row.is_enabled)
        self.assertEqual((row.schedule_hour, row.schedule_minute), (18, 5))
        self.assertEqual(row.stat_span, "yesterday")
        self.assertEqual(catalog.template_calls, [])
        extra = client.patch(f"{PREFIX}/7/switch", json={"is_enabled": False, "name": "不行"})
        self.assertEqual(extra.status_code, 422)

    def test_schedule_only_changes_hour_and_minute(self) -> None:
        """每天时分单独改，不改开关和区间，也不问目录。"""
        row = live_drama(is_enabled=True)
        session = FakeSession([[row]])
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.patch(f"{PREFIX}/7/schedule", json={"schedule_hour": 23, "schedule_minute": 59})
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.json()["data"]["schedule_hour"], res.json()["data"]["schedule_minute"]), (23, 59))
        self.assertTrue(res.json()["data"]["is_enabled"])
        self.assertEqual(res.json()["data"]["recovery_min"], "20.0000")
        self.assertEqual(row.cost_max, Decimal("80.50"))
        self.assertEqual(catalog.platform_calls, [])
        missing = client.patch(f"{PREFIX}/7/schedule", json={"schedule_hour": 1})
        self.assertEqual(missing.status_code, 422)
        late = client.patch(f"{PREFIX}/7/schedule", json={"schedule_hour": 24, "schedule_minute": 0})
        self.assertEqual(late.status_code, 422)

    def test_missing_rule_is_not_found(self) -> None:
        """没有这条按剧条件规则时，查询、保存、删除、开关、时分都是 404。"""
        session = FakeSession([[], [], [], [], []])
        client = http_client(session, FakeUniRobotCatalog())
        calls = [
            client.get(f"{PREFIX}/7"),
            client.put(f"{PREFIX}/7", json=write_body()),
            client.delete(f"{PREFIX}/7"),
            client.patch(f"{PREFIX}/7/switch", json={"is_enabled": True}),
            client.patch(f"{PREFIX}/7/schedule", json={"schedule_hour": 1, "schedule_minute": 2}),
        ]
        for res in calls:
            self.assertEqual(res.status_code, 404)
            self.assertEqual(res.json()["message"], "规则不存在")
        self.assertEqual(session.commits, 0)
