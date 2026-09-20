from __future__ import annotations

import socket
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


class LoginHttpTests(unittest.TestCase):
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

    def test_admin_login_then_session_me(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "admin", "password": "admin123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        body = login.json()
        self.assertTrue(body["ok"])
        token = body["data"]["token"]
        self.assertTrue(token)

        me = self.client.get(
            "/api/v1/system-admin/session/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me.status_code, 200, me.text)
        me_body = me.json()
        self.assertTrue(me_body["ok"])
        self.assertEqual(me_body["data"]["login_account"], "admin")

    def test_wrong_password(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "admin", "password": "wrong"},
        )
        self.assertEqual(login.status_code, 401)
        body = login.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "INVALID_CREDENTIALS")

    def test_disabled_account(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "disabled", "password": "disabled123"},
        )
        self.assertEqual(login.status_code, 403)
        body = login.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "ACCOUNT_DISABLED")


if __name__ == "__main__":
    unittest.main()
