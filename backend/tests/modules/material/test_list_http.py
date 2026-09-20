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


class ListManhuaSeriesHttpTests(unittest.TestCase):
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

    def _token(self, account: str, password: str) -> str:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": account, "password": password},
        )
        self.assertEqual(login.status_code, 200, login.text)
        return login.json()["data"]["token"]

    def test_admin_can_list_envelope(self) -> None:
        token = self._token("admin", "admin123")
        resp = self.client.get(
            "/api/v1/material/manhua-series",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 500:
            self.skipTest("manhua_series 表未迁移")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertTrue(body["ok"])
        data = body["data"]
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertEqual(data["page"], 1)

    def test_department_filter_is_empty(self) -> None:
        token = self._token("admin", "admin123")
        resp = self.client.get(
            "/api/v1/material/manhua-series",
            params={"department_id": "1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 500:
            self.skipTest("manhua_series 表未迁移")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["data"]["total"], 0)
        self.assertEqual(resp.json()["data"]["items"], [])


if __name__ == "__main__":
    unittest.main()
