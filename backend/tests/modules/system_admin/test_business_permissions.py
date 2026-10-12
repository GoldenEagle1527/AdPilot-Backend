"""业务接口的菜单、角色勾选和部门数据范围。"""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import register_exception_handlers
from app.modules.file.controller import router as file_router
from app.modules.material_title.controller import router as title_router
from app.modules.material_video.controller import router as video_router
from app.modules.material_video.schema import VideoQuery
from app.modules.material_video.service import video_filters
from app.modules.oceanengine.catalog import org_wide_owner
from app.modules.standard_delivery.controller import router as standard_router
from app.modules.standard_delivery.model import DeliveryTaskDraft
from app.modules.standard_delivery.schema import DraftQuery
from app.modules.standard_delivery.service import draft_filters
from app.modules.system_admin.domain.models import User
from app.modules.system_admin.domain.scope import DataScope, owner_match
from app.modules.system_admin.domain.seed_data import menu_seed_rows, role_menu_seed_rows
from app.modules.theater.controller import router as theater_router
from app.modules.uni_native_auto_run.controller import router as auto_run_router
from app.modules.uni_native_task.controller import router as uni_task_router
from app.modules.uni_native_task.schema import TaskQuery
from app.modules.uni_native_task.service import task_filters
from app.modules.uni_robot.controller import router as robot_router
from app.modules.uni_template.controller import router as uni_template_router

_DIALECT = postgresql.dialect()


def _sql(clause) -> str:
    return str(clause.compile(dialect=_DIALECT, compile_kwargs={"literal_binds": True}))


class _Boom:
    """菜单通过之后才会碰到库。碰到就说明鉴权已经放行。"""

    async def execute(self, _statement):
        raise RuntimeError("past-menu")

    async def scalar(self, _statement):
        raise RuntimeError("past-menu")

    def add(self, _row) -> None:
        return None


def _client(*routers, menus: list[str]) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    for item in routers:
        app.include_router(item)

    async def _session():
        yield _Boom()

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[require_token] = lambda: {
        "id": "3",
        "nickname": "投手",
        "login_account": "pitcher",
        "tenant": "agent",
        "enabled": True,
        "menu_ids": menus,
        "data_scope": {"self_only": True, "department_ids": []},
    }
    return TestClient(app, raise_server_exceptions=False)


class SeedMenuTests(unittest.TestCase):
    def test_new_nodes_keep_old_ids_and_follow_sibling_roles(self) -> None:
        """1–102 不改号。新节点走同一套角色勾选。"""
        rows = {int(row["id"]): row for row in menu_seed_rows()}
        self.assertEqual(rows[102]["name"], "权限角色查询")
        self.assertEqual(rows[103]["name"], "文件上传")
        self.assertEqual(rows[103]["parent_id"], 88)
        self.assertEqual(rows[104]["name"], "产品快照")
        self.assertEqual(rows[104]["parent_id"], 38)
        self.assertEqual(rows[105]["name"], "抄到模板")
        self.assertEqual(rows[105]["parent_id"], 104)
        links = {(row["role_id"], row["menu_id"]) for row in role_menu_seed_rows()}
        # 运营管理员 5、组长 1、剪辑师 4、短剧投手 6。
        self.assertTrue({(5, 103), (5, 104), (5, 105)} <= links)
        self.assertTrue({(4, 103), (6, 103)} <= links)
        self.assertTrue({(1, 104), (1, 105)} <= links)
        self.assertNotIn((6, 104), links)


class DataScopeSqlTests(unittest.TestCase):
    def test_self_only_stays_the_caller(self) -> None:
        """没勾部门时仍是本人。"""
        sql = _sql(owner_match(DeliveryTaskDraft.pitcher_user_id, 3, DataScope(3, True, ())))
        self.assertIn("pitcher_user_id = 3", sql)
        self.assertNotIn("department_id", sql)

    def test_department_scope_uses_users_in_those_departments(self) -> None:
        """勾了部门就看这些部门里的用户。"""
        scope = DataScope(3, False, (2, 8))
        sql = _sql(owner_match(User.id, 3, scope))
        self.assertIn("department_id IN (2, 8)", sql)
        draft = " AND ".join(_sql(item) for item in draft_filters(DraftQuery(charge_mode="IAA"), 3, scope))
        self.assertIn("department_id IN (2, 8)", draft)
        task = " AND ".join(_sql(item) for item in task_filters(TaskQuery(), 3, scope))
        self.assertIn("department_id IN (2, 8)", task)

    def test_video_list_keeps_public_and_adds_department_uploaders(self) -> None:
        """公有素材仍可见。勾了部门再加这些部门上传的。"""
        own = " AND ".join(_sql(item) for item in video_filters(VideoQuery(), 3))
        self.assertIn("'public'", own)
        self.assertNotIn("department_id", own)
        scoped = " AND ".join(
            _sql(item) for item in video_filters(VideoQuery(), 3, DataScope(3, False, (2,)))
        )
        self.assertIn("'public'", scoped)
        self.assertIn("department_id IN (2)", scoped)

    def test_org_wide_advertisers_follow_scope_and_keep_unassigned_for_departments(self) -> None:
        """菜单 63：仅本人只看自己的户；勾了部门再看见未分配的户。"""
        self_only = _sql(org_wide_owner(DataScope(3, True, ())))
        self.assertIn("pitcher_user_id = 3", self_only)
        self.assertNotIn("IS NULL", self_only)
        wide = _sql(org_wide_owner(DataScope(3, False, (2,))))
        self.assertIn("department_id IN (2)", wide)
        self.assertIn("IS NULL", wide)


class MenuRouteTests(unittest.TestCase):
    def test_logged_in_without_the_menu_is_forbidden(self) -> None:
        """登录了但会话里没有节点，按没有这个角色拒绝。"""
        cases = [
            (_client(file_router, menus=[]), "post", "/api/v1/files/upload", None),
            (_client(title_router, menus=[]), "get", "/api/v1/material/titles", None),
            (_client(video_router, menus=["89"]), "post", "/api/v1/material/videos/batch-delete", {"video_ids": [1]}),
            (_client(uni_template_router, menus=["61"]), "get", "/api/v1/uni-templates", None),
            (_client(uni_template_router, menus=["60"]), "put", "/api/v1/uni-templates/1/douyin-accounts", {}),
            (_client(uni_task_router, menus=[]), "get", "/api/v1/uni-native-tasks", None),
            (_client(auto_run_router, menus=[]), "get", "/api/v1/uni-native-auto-runs", None),
            (_client(auto_run_router, menus=[]), "get", "/api/v1/uni-native-auto-runs/1/failure-logs", None),
            (_client(robot_router, menus=[]), "get", "/api/v1/uni-robot/promotion-link-rules", None),
            (_client(robot_router, menus=[]), "get", "/api/v1/uni-robot/drama-rules", None),
            (_client(theater_router, menus=[]), "get", "/api/v1/theater/platforms", None),
            (_client(theater_router, menus=["82"]), "patch", "/api/v1/theater/platforms/1", {}),
            (_client(theater_router, menus=[]), "get", "/api/v1/theater/apps", None),
            (_client(theater_router, menus=[]), "get", "/api/v1/theater/promotion-links", None),
            (_client(theater_router, menus=[]), "get", "/api/v1/theater/promotion-tasks", None),
            (
                _client(standard_router, menus=["45"]),
                "get",
                "/api/v1/standard-delivery/product-snapshots",
                None,
            ),
            (
                _client(standard_router, menus=["39"]),
                "post",
                "/api/v1/standard-delivery/templates/1/copy-product-snapshot",
                {"snapshot_id": 1},
            ),
        ]
        for client, method, path, body in cases:
            with self.subTest(path=path, method=method):
                kwargs = {} if body is None else {"json": body}
                response = getattr(client, method)(path, **kwargs)
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["message"], "已登录但无对应菜单或组件")

    def test_menu_in_the_session_gets_past_the_check(self) -> None:
        """会话里有节点就不再是 403。后面的库可以失败。"""
        cases = [
            (_client(file_router, menus=["103"]), "post", "/api/v1/files/upload", None),
            (_client(title_router, menus=["92"]), "get", "/api/v1/material/titles", None),
            (_client(video_router, menus=["89"]), "get", "/api/v1/material/videos", None),
            (_client(video_router, menus=["90"]), "post", "/api/v1/material/videos/batch-delete", {"video_ids": [1]}),
            (_client(uni_template_router, menus=["60"]), "get", "/api/v1/uni-templates", None),
            (_client(uni_task_router, menus=["56"]), "get", "/api/v1/uni-native-tasks", None),
            (_client(auto_run_router, menus=["57"]), "get", "/api/v1/uni-native-auto-runs", None),
            (_client(robot_router, menus=["80"]), "get", "/api/v1/uni-robot/promotion-link-rules", None),
            (_client(theater_router, menus=["82"]), "get", "/api/v1/theater/platforms", None),
            (_client(theater_router, menus=["83"]), "patch", "/api/v1/theater/platforms/1", {}),
            (_client(theater_router, menus=["84"]), "get", "/api/v1/theater/apps", None),
            (_client(theater_router, menus=["85"]), "get", "/api/v1/theater/promotion-links", None),
            (_client(theater_router, menus=["86"]), "get", "/api/v1/theater/promotion-tasks", None),
            (
                _client(standard_router, menus=["104"]),
                "get",
                "/api/v1/standard-delivery/product-snapshots",
                None,
            ),
            (
                _client(standard_router, menus=["39", "46"]),
                "get",
                "/api/v1/standard-delivery/task-drafts?charge_mode=IAA",
                None,
            ),
        ]
        for client, method, path, body in cases:
            with self.subTest(path=path, method=method):
                kwargs = {} if body is None else {"json": body}
                response = getattr(client, method)(path, **kwargs)
                self.assertNotEqual(response.status_code, 403, response.text)
                if response.status_code == 200:
                    continue
                message = response.json().get("message", "")
                self.assertNotEqual(message, "已登录但无对应菜单或组件")
