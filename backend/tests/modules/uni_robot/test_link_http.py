"""按推广链接规则的 HTTP。目录用测试里的假实现，不进应用启动。"""

from __future__ import annotations

import unittest
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import register_exception_handlers
from app.modules.uni_robot.controller import get_catalog, router
from app.modules.uni_robot.crud import get_link_rule_stmt, link_page_stmt, name_taken_stmt
from app.modules.uni_robot.model import RuleKind, UniRobotRule
from app.modules.uni_robot.schema import LinkRuleQuery
from app.modules.uni_robot.service import link_filters
from tests.modules.uni_robot.fake_catalog import FAKE_PLATFORMS, FAKE_TEMPLATES, FakeUniRobotCatalog
from tests.modules.uni_robot.test_rules import CREATED, FakeSession

PREFIX = "/api/v1/uni-robot/promotion-link-rules"


def live_link(**kwargs: Any) -> UniRobotRule:
    """一条已在库里的按推广链接规则。"""
    row = UniRobotRule(
        rule_kind=kwargs.pop("rule_kind", RuleKind.PROMOTION_LINK),
        name=kwargs.pop("name", "按链接"),
        template_id=kwargs.pop("template_id", FAKE_TEMPLATES[0].id),
        platform_id=kwargs.pop("platform_id", FAKE_PLATFORMS[0].id),
        max_videos_per_series=kwargs.pop("max_videos_per_series", 800),
        schedule_hour=kwargs.pop("schedule_hour", 9),
        schedule_minute=kwargs.pop("schedule_minute", 30),
        is_enabled=kwargs.pop("is_enabled", False),
    )
    row.id = kwargs.pop("id", 7)
    row.is_deleted = kwargs.pop("is_deleted", 0)
    row.created_date = CREATED
    row.updated_date = CREATED
    row.stat_span = None
    row.cost_min = None
    row.cost_max = None
    row.recovery_min = None
    row.recovery_max = None
    return row


def http_client(session: FakeSession, catalog: FakeUniRobotCatalog | None, *, login: bool = True) -> TestClient:
    """挂上本模块路由。登录和目录都可以换成测试替身。"""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    if login:
        app.dependency_overrides[require_token] = lambda: {
            "id": "1",
            "nickname": "测",
            "login_account": "tester",
            "tenant": "agent",
        }
    if catalog is not None:
        app.dependency_overrides[get_catalog] = lambda: catalog
    return TestClient(app)


def write_body(**kwargs: Any) -> dict[str, Any]:
    """一份合法的按推广链接请求体。"""
    data: dict[str, Any] = {
        "name": "按链接",
        "template_id": FAKE_TEMPLATES[0].id,
        "platform_id": FAKE_PLATFORMS[0].id,
        "schedule_hour": 9,
        "schedule_minute": 30,
    }
    data.update(kwargs)
    return data


class QueryShapeTests(unittest.TestCase):
    def test_list_sql_is_only_live_link_rules(self) -> None:
        """列表只查未删除的按推广链接，按创建时间倒序。"""
        sql = str(
            link_page_stmt(link_filters(LinkRuleQuery()), offset=0, limit=20).compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        self.assertIn("promotion_link", sql)
        self.assertNotIn("drama_condition", sql)
        self.assertIn("is_deleted = 0", sql)
        self.assertIn("created_date DESC", sql)

    def test_blank_name_does_not_filter(self) -> None:
        """空白名称当没传。百分号按字面量。"""
        blank = str(
            select(UniRobotRule)
            .where(*link_filters(LinkRuleQuery(name="  ")))
            .compile(compile_kwargs={"literal_binds": True})
        )
        self.assertNotIn("LIKE", blank.upper())
        named = str(
            select(UniRobotRule)
            .where(*link_filters(LinkRuleQuery(name="100%", is_enabled=True)))
            .compile(compile_kwargs={"literal_binds": True})
        )
        self.assertIn("100\\%", named)
        self.assertIn("is_enabled = true", named)

    def test_get_sql_excludes_drama_rules(self) -> None:
        """单条查询带规则类型，按剧条件不会被取出来。"""
        sql = str(get_link_rule_stmt(7).compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("uni_robot_rule.id = 7", sql)
        self.assertIn("promotion_link", sql)
        self.assertIn("is_deleted = 0", sql)
        self.assertNotIn("drama_condition", sql)

    def test_rename_check_ignores_the_row_itself(self) -> None:
        """整表保存时，自己原来的名字不算重名。"""
        sql = str(
            name_taken_stmt(RuleKind.PROMOTION_LINK, "按链接", 7).compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        self.assertIn("uni_robot_rule.id != 7", sql)
        self.assertIn("promotion_link", sql)


class RouteTests(unittest.TestCase):
    def test_only_link_rule_routes_are_mounted(self) -> None:
        """应用只挂按推广链接这一组，没有按剧条件。"""
        from main import create_app

        paths = create_app().openapi()["paths"]
        found = {path: set(paths[path]) for path in paths if "/uni-robot/" in path}
        self.assertEqual(
            found,
            {
                PREFIX: {"get", "post"},
                f"{PREFIX}/{{rule_id}}": {"get", "put", "delete"},
                f"{PREFIX}/{{rule_id}}/switch": {"patch"},
                f"{PREFIX}/{{rule_id}}/schedule": {"patch"},
            },
        )
        self.assertFalse(any("drama" in path for path in paths))


class LinkHttpTests(unittest.TestCase):
    def test_missing_token_is_unauthorized(self) -> None:
        """没登录不能列规则。"""
        client = http_client(FakeSession(), None, login=False)
        res = client.get(PREFIX)
        self.assertEqual(res.status_code, 401)
        body = res.json()
        self.assertEqual(body["code"], 401)
        self.assertEqual(body["message"], "未带或 Token 无效")
        self.assertIsNone(body["data"])

    def test_create_stores_port_ids_and_leaves_drama_columns_empty(self) -> None:
        """新建走目录端口。出参没有剧条件字段，库里的条件列为空。"""
        session = FakeSession()
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.post(PREFIX, json=write_body(name="  按链接  ", max_videos_per_series=100))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["id"], "40")
        self.assertEqual(data["name"], "按链接")
        self.assertEqual(data["template_id"], str(FAKE_TEMPLATES[0].id))
        self.assertEqual(data["platform_id"], str(FAKE_PLATFORMS[0].id))
        self.assertEqual(data["max_videos_per_series"], 100)
        self.assertEqual(data["schedule_hour"], 9)
        self.assertEqual(data["schedule_minute"], 30)
        self.assertFalse(data["is_enabled"])
        self.assertEqual(data["created_at"], "2026-09-30T09:30:00+08:00")
        self.assertNotIn("stat_span", data)
        self.assertNotIn("cost_min", data)
        self.assertNotIn("recovery_max", data)
        row = session.added[0]
        self.assertEqual(row.rule_kind, RuleKind.PROMOTION_LINK)
        self.assertIsNone(row.stat_span)
        self.assertIsNone(row.cost_min)
        self.assertIsNone(row.cost_max)
        self.assertIsNone(row.recovery_min)
        self.assertIsNone(row.recovery_max)
        self.assertEqual(catalog.template_calls, [FAKE_TEMPLATES[0].id])
        self.assertEqual(catalog.platform_calls, [FAKE_PLATFORMS[0].id])

    def test_create_rejects_unknown_template_and_drama_fields(self) -> None:
        """假目录没有的模板不落库。多传剧条件字段是 422。"""
        session = FakeSession()
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        missing = client.post(PREFIX, json=write_body(template_id=1))
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()["message"], "全域模板不存在")
        self.assertEqual(session.added, [])
        self.assertEqual(catalog.platform_calls, [])
        extra = client.post(PREFIX, json=write_body(stat_span="today", cost_min="1", cost_max="2"))
        self.assertEqual(extra.status_code, 422)
        self.assertIn("stat_span", extra.json()["message"])
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
        row = live_link()
        session = FakeSession([[1], [row], [row]])
        client = http_client(session, None)
        listed = client.get(PREFIX, params={"name": "按链接", "is_enabled": "false"})
        self.assertEqual(listed.status_code, 200)
        page = listed.json()["data"]
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["page"], 1)
        self.assertEqual(page["page_size"], 20)
        self.assertEqual(page["list"][0]["id"], "7")
        self.assertNotIn("stat_span", page["list"][0])
        one = client.get(f"{PREFIX}/7")
        self.assertEqual(one.status_code, 200)
        self.assertEqual(one.json()["data"]["name"], "按链接")
        empty = http_client(FakeSession([[0], []]), None).get(PREFIX)
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["data"]["list"], [])
        self.assertEqual(empty.json()["data"]["total"], 0)
        rejected = client.get(PREFIX, params={"stat_span": "today"})
        self.assertEqual(rejected.status_code, 422)

    def test_full_update_rewrites_link_fields_and_keeps_drama_columns_empty(self) -> None:
        """整表保存再次问目录。条件列仍为空。"""
        row = live_link()
        session = FakeSession([[row], []])
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.put(
            f"{PREFIX}/7",
            json=write_body(
                name="新名称",
                template_id=FAKE_TEMPLATES[1].id,
                platform_id=FAKE_PLATFORMS[1].id,
                max_videos_per_series=20,
                schedule_hour=8,
                schedule_minute=15,
                is_enabled=True,
            ),
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["name"], "新名称")
        self.assertEqual(data["template_id"], str(FAKE_TEMPLATES[1].id))
        self.assertEqual(data["platform_id"], str(FAKE_PLATFORMS[1].id))
        self.assertEqual(data["max_videos_per_series"], 20)
        self.assertEqual((data["schedule_hour"], data["schedule_minute"]), (8, 15))
        self.assertTrue(data["is_enabled"])
        self.assertIsNone(row.stat_span)
        self.assertIsNone(row.cost_min)
        self.assertIsNone(row.recovery_max)
        self.assertEqual(row.rule_kind, RuleKind.PROMOTION_LINK)
        self.assertEqual(catalog.template_calls, [FAKE_TEMPLATES[1].id])
        self.assertEqual(session.commits, 1)

    def test_update_unknown_template_does_not_save(self) -> None:
        """模板不在目录里时，整表保存不写库，也不再问平台。"""
        row = live_link()
        session = FakeSession([[row]])
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.put(f"{PREFIX}/7", json=write_body(template_id=1))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(row.name, "按链接")
        self.assertEqual(catalog.platform_calls, [])
        self.assertEqual(session.commits, 0)

    def test_update_duplicate_name_is_conflict(self) -> None:
        """改成已有名称是 409，原行不动。"""
        row = live_link()
        session = FakeSession([[row], [9]])
        client = http_client(session, FakeUniRobotCatalog())
        res = client.put(f"{PREFIX}/7", json=write_body(name="别的"))
        self.assertEqual(res.status_code, 409)
        self.assertEqual(row.name, "按链接")
        self.assertEqual(session.commits, 0)

    def test_drama_row_is_not_on_this_resource(self) -> None:
        """按剧条件即使被取回来，这条资源也当不存在，并且不改它。"""
        row = live_link(rule_kind=RuleKind.DRAMA_CONDITION, name="按剧")
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
        self.assertEqual(row.name, "按剧")
        self.assertFalse(row.is_enabled)
        self.assertEqual(session.commits, 0)

    def test_soft_delete_hides_the_rule(self) -> None:
        """删除是软删。"""
        row = live_link()
        session = FakeSession([[row]])
        client = http_client(session, None)
        res = client.delete(f"{PREFIX}/7")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"], {"id": "7", "deleted": True})
        self.assertEqual(row.is_deleted, 1)
        self.assertIsNotNone(row.deleted_at)
        self.assertEqual(session.commits, 1)

    def test_switch_only_flips_enabled(self) -> None:
        """开关不改时分，也不问目录。"""
        row = live_link()
        session = FakeSession([[row]])
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.patch(f"{PREFIX}/7/switch", json={"is_enabled": True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["data"]["is_enabled"])
        self.assertEqual(res.json()["data"]["schedule_hour"], 9)
        self.assertTrue(row.is_enabled)
        self.assertEqual((row.schedule_hour, row.schedule_minute), (9, 30))
        self.assertEqual(catalog.template_calls, [])
        extra = client.patch(f"{PREFIX}/7/switch", json={"is_enabled": False, "name": "不行"})
        self.assertEqual(extra.status_code, 422)

    def test_schedule_only_changes_hour_and_minute(self) -> None:
        """每天时分单独改，不改开关，也不问目录。"""
        row = live_link(is_enabled=True)
        session = FakeSession([[row]])
        catalog = FakeUniRobotCatalog()
        client = http_client(session, catalog)
        res = client.patch(f"{PREFIX}/7/schedule", json={"schedule_hour": 23, "schedule_minute": 59})
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.json()["data"]["schedule_hour"], res.json()["data"]["schedule_minute"]), (23, 59))
        self.assertTrue(res.json()["data"]["is_enabled"])
        self.assertEqual(catalog.platform_calls, [])
        missing = client.patch(f"{PREFIX}/7/schedule", json={"schedule_hour": 1})
        self.assertEqual(missing.status_code, 422)
        late = client.patch(f"{PREFIX}/7/schedule", json={"schedule_hour": 24, "schedule_minute": 0})
        self.assertEqual(late.status_code, 422)

    def test_missing_rule_is_not_found(self) -> None:
        """没有这条按推广链接规则时，查询、保存、删除、开关、时分都是 404。"""
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
