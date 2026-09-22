from __future__ import annotations

import socket
import time
import unittest

try:
    from fastapi.testclient import TestClient
except RuntimeError:
    TestClient = None  # type: ignore[misc, assignment]

from app.core.config import get_settings
from app.main import app


def _compose_hosts_resolvable() -> bool:
    settings = get_settings()
    try:
        socket.getaddrinfo(settings.postgres.host, settings.postgres.port)
        socket.getaddrinfo(settings.redis.host, settings.redis.port)
    except OSError:
        return False
    return True


class AclGapHttpTests(unittest.TestCase):
    client: TestClient
    skip_all: bool
    _cm: TestClient

    @classmethod
    def setUpClass(cls) -> None:
        if TestClient is None:
            raise unittest.SkipTest("缺少 httpx，无法使用 TestClient")
        if not _compose_hosts_resolvable():
            raise unittest.SkipTest("PostgreSQL/Redis 主机不可解析")
        cls._cm = TestClient(app)
        cls.client = cls._cm.__enter__()
        ready = cls.client.get("/api/v1/ready")
        cls.skip_all = ready.status_code != 200

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "_cm", None) is not None:
            cls._cm.__exit__(None, None, None)

    def setUp(self) -> None:
        if self.skip_all:
            self.skipTest("PostgreSQL/Redis 未就绪（/ready 非 200）")
        self._stamp = str(time.time_ns())

    def _admin_token(self) -> str:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "admin", "password": "admin123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        return login.json()["data"]["token"]

    def _auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _create_user(self, token: str, *, password: str = "AclGap@123") -> dict:
        account = f"acl_{self._stamp}"
        created = self.client.post(
            "/api/v1/system-admin/users",
            headers=self._auth(token),
            json={
                "nickname": "acl-gap",
                "login_account": account,
                "password": password,
                "phone": "13800001111",
                "department_id": "1",
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        return created.json()["data"]

    def test_password_reset_revokes_old_token(self) -> None:
        admin = self._admin_token()
        user = self._create_user(admin, password="OldPass@123")
        victim = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": user["login_account"], "password": "OldPass@123"},
        )
        self.assertEqual(victim.status_code, 200, victim.text)
        old = victim.json()["data"]["token"]

        reset = self.client.post(
            f"/api/v1/system-admin/users/{user['id']}/password-reset",
            headers=self._auth(admin),
            json={"password": "NewPass@123", "password_confirm": "NewPass@123"},
        )
        self.assertEqual(reset.status_code, 200, reset.text)

        me = self.client.get(
            "/api/v1/system-admin/session/me",
            headers=self._auth(old),
        )
        self.assertEqual(me.status_code, 401, me.text)
        users = self.client.get(
            "/api/v1/system-admin/users",
            headers=self._auth(old),
        )
        self.assertEqual(users.status_code, 401, users.text)

        again = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": user["login_account"], "password": "NewPass@123"},
        )
        self.assertEqual(again.status_code, 200, again.text)
        self.client.delete(
            f"/api/v1/system-admin/users/{user['id']}",
            headers=self._auth(admin),
        )

    def test_disable_user_revokes_old_token(self) -> None:
        admin = self._admin_token()
        user = self._create_user(admin)
        victim = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": user["login_account"], "password": "AclGap@123"},
        )
        self.assertEqual(victim.status_code, 200, victim.text)
        old = victim.json()["data"]["token"]

        status = self.client.patch(
            f"/api/v1/system-admin/users/{user['id']}/status",
            headers=self._auth(admin),
            json={"enabled": False},
        )
        self.assertEqual(status.status_code, 200, status.text)

        me = self.client.get(
            "/api/v1/system-admin/session/me",
            headers=self._auth(old),
        )
        self.assertEqual(me.status_code, 401, me.text)
        users = self.client.get(
            "/api/v1/system-admin/users",
            headers=self._auth(old),
        )
        self.assertEqual(users.status_code, 401, users.text)

        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": user["login_account"], "password": "AclGap@123"},
        )
        self.assertEqual(login.status_code, 403, login.text)
        self.assertEqual(login.json()["message"], "账号停用")
        self.client.delete(
            f"/api/v1/system-admin/users/{user['id']}",
            headers=self._auth(admin),
        )

    def test_phone_is_not_a_login_key(self) -> None:
        admin = self._admin_token()
        user = self._create_user(admin)
        by_phone = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "13800001111", "password": "AclGap@123"},
        )
        self.assertEqual(by_phone.status_code, 401, by_phone.text)
        by_account = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": user["login_account"], "password": "AclGap@123"},
        )
        self.assertEqual(by_account.status_code, 200, by_account.text)
        self.client.delete(
            f"/api/v1/system-admin/users/{user['id']}",
            headers=self._auth(admin),
        )

    def test_non_numeric_path_id_is_not_found(self) -> None:
        admin = self._admin_token()
        reset = self.client.post(
            "/api/v1/system-admin/users/abc/password-reset",
            headers=self._auth(admin),
            json={"password": "x", "password_confirm": "x"},
        )
        self.assertEqual(reset.status_code, 404, reset.text)
        self.assertEqual(reset.json()["code"], 404)
        dept = self.client.patch(
            "/api/v1/system-admin/departments/abc/status",
            headers=self._auth(admin),
            json={"enabled": False},
        )
        self.assertEqual(dept.status_code, 404, dept.text)

    def test_cannot_disable_self_or_strip_own_admin(self) -> None:
        admin = self._admin_token()
        me = self.client.get(
            "/api/v1/system-admin/session/me",
            headers=self._auth(admin),
        )
        self.assertEqual(me.status_code, 200, me.text)
        admin_id = me.json()["data"]["id"]

        disabled = self.client.patch(
            f"/api/v1/system-admin/users/{admin_id}/status",
            headers=self._auth(admin),
            json={"enabled": False},
        )
        self.assertEqual(disabled.status_code, 409, disabled.text)
        self.assertEqual(disabled.json()["message"], "不能停用当前登录账号")

        stripped = self.client.put(
            f"/api/v1/system-admin/users/{admin_id}/roles",
            headers=self._auth(admin),
            json={"role_ids": []},
        )
        self.assertEqual(stripped.status_code, 409, stripped.text)
        self.assertEqual(stripped.json()["message"], "不能去掉自己的用户管理权限")

        last_role = self.client.patch(
            "/api/v1/system-admin/roles/5/status",
            headers=self._auth(admin),
            json={"enabled": False},
        )
        self.assertEqual(last_role.status_code, 409, last_role.text)
        self.assertEqual(last_role.json()["message"], "至少保留一名可管理用户的账号")

    def test_disabled_department_rejects_new_members(self) -> None:
        admin = self._admin_token()
        created = self.client.post(
            "/api/v1/system-admin/departments",
            headers=self._auth(admin),
            json={"name": f"停用部{self._stamp}", "parent_id": "1", "sort": 0},
        )
        self.assertEqual(created.status_code, 200, created.text)
        dept_id = created.json()["data"]["id"]
        off = self.client.patch(
            f"/api/v1/system-admin/departments/{dept_id}/status",
            headers=self._auth(admin),
            json={"enabled": False},
        )
        self.assertEqual(off.status_code, 200, off.text)

        user = self.client.post(
            "/api/v1/system-admin/users",
            headers=self._auth(admin),
            json={
                "nickname": "nope",
                "login_account": f"acl_off_{self._stamp}",
                "password": "AclGap@123",
                "department_id": dept_id,
            },
        )
        self.assertEqual(user.status_code, 409, user.text)
        self.assertEqual(user.json()["message"], "部门已停用")

        child = self.client.post(
            "/api/v1/system-admin/departments",
            headers=self._auth(admin),
            json={"name": f"子{self._stamp}", "parent_id": dept_id, "sort": 0},
        )
        self.assertEqual(child.status_code, 409, child.text)
        self.assertEqual(child.json()["message"], "部门已停用")

        scope = self.client.put(
            "/api/v1/system-admin/users/1/data-scope",
            headers=self._auth(admin),
            json={"department_ids": [dept_id]},
        )
        self.assertEqual(scope.status_code, 409, scope.text)
        self.client.delete(
            f"/api/v1/system-admin/departments/{dept_id}",
            headers=self._auth(admin),
        )

    def test_batch_user_tags_accepts_string_ids(self) -> None:
        admin = self._admin_token()
        created = self.client.post(
            "/api/v1/system-admin/users",
            headers=self._auth(admin),
            json={
                "nickname": "tags",
                "login_account": f"acl_tag_{self._stamp}",
                "password": "AclGap@123",
                "department_id": "1",
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        user_id = created.json()["data"]["id"]
        catalog = self.client.get(
            "/api/v1/system-admin/user-tags",
            headers=self._auth(admin),
        )
        self.assertEqual(catalog.status_code, 200, catalog.text)
        tag_ids = [item["id"] for item in catalog.json()["data"]["items"][:2]]
        self.assertTrue(tag_ids)
        try:
            tagged = self.client.put(
                "/api/v1/system-admin/users/batch-tags",
                headers=self._auth(admin),
                json={"user_ids": [user_id], "tag_ids": tag_ids},
            )
            self.assertEqual(tagged.status_code, 200, tagged.text)
            got = tagged.json()["data"]["items"][0]["tags"]
            self.assertEqual([item["id"] for item in got], tag_ids)
        finally:
            self.client.delete(
                f"/api/v1/system-admin/users/{user_id}",
                headers=self._auth(admin),
            )

    def test_role_string_path_id_queries_as_int(self) -> None:
        admin = self._admin_token()
        created = self.client.post(
            "/api/v1/system-admin/roles",
            headers=self._auth(admin),
            json={"name": f"intq_{self._stamp}", "remark": "type-cast"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        role_id = created.json()["data"]["id"]
        try:
            menus = self.client.get(
                f"/api/v1/system-admin/roles/{role_id}/menus",
                headers=self._auth(admin),
            )
            self.assertEqual(menus.status_code, 200, menus.text)
            self.assertEqual(menus.json()["data"]["menu_ids"], [])

            updated = self.client.put(
                f"/api/v1/system-admin/roles/{role_id}",
                headers=self._auth(admin),
                json={"name": f"intq_{self._stamp}_u", "remark": "ok"},
            )
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assertEqual(updated.json()["data"]["name"], f"intq_{self._stamp}_u")
        finally:
            self.client.patch(
                f"/api/v1/system-admin/roles/{role_id}/status",
                headers=self._auth(admin),
                json={"enabled": False},
            )

    def test_get_data_scope_expands_new_child(self) -> None:
        admin = self._admin_token()
        created = self.client.post(
            "/api/v1/system-admin/departments",
            headers=self._auth(admin),
            json={"name": f"新子{self._stamp}", "parent_id": "1", "sort": 0},
        )
        self.assertEqual(created.status_code, 200, created.text)
        child_id = created.json()["data"]["id"]
        try:
            got = self.client.get(
                "/api/v1/system-admin/users/1/data-scope",
                headers=self._auth(admin),
            )
            self.assertEqual(got.status_code, 200, got.text)
            self.assertIn(child_id, got.json()["data"]["department_ids"])

            session_scope = self.client.get(
                "/api/v1/system-admin/session/data-scope",
                headers=self._auth(admin),
            )
            self.assertEqual(session_scope.status_code, 200, session_scope.text)
            self.assertIn(child_id, session_scope.json()["data"]["department_ids"])
        finally:
            self.client.delete(
                f"/api/v1/system-admin/departments/{child_id}",
                headers=self._auth(admin),
            )


if __name__ == "__main__":
    unittest.main()
