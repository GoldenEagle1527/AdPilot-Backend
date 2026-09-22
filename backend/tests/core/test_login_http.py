from __future__ import annotations

import asyncio
import socket
import unittest
from datetime import timedelta

import jwt
from redis.asyncio import Redis

try:
    from fastapi.testclient import TestClient
except RuntimeError:
    TestClient = None  # type: ignore[misc, assignment]

from app.core.config import get_settings
from app.core.times import beijing_now
from main import app


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
        self.assertEqual(body["code"], 200)
        token = body["data"]["token"]
        self.assertTrue(token)

        me = self.client.get(
            "/api/v1/system-admin/session/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me.status_code, 200, me.text)
        me_body = me.json()
        self.assertEqual(me_body["code"], 200)
        self.assertEqual(me_body["data"]["login_account"], "admin")

    def test_admin_can_list_users_via_cached_menu(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "admin", "password": "admin123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        token = login.json()["data"]["token"]
        users = self.client.get(
            "/api/v1/system-admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(users.status_code, 200, users.text)
        self.assertEqual(users.json()["code"], 200)
        self.assertIsInstance(users.json()["data"]["list"], list)

        menus = self.client.get(
            "/api/v1/system-admin/session/menus",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(menus.status_code, 200, menus.text)
        self.assertTrue(menus.json()["data"]["items"])

    def test_pitcher_cannot_list_users(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "pitcher", "password": "pitcher123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        token = login.json()["data"]["token"]
        users = self.client.get(
            "/api/v1/system-admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(users.status_code, 403, users.text)

    def test_wrong_password(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "admin", "password": "wrong"},
        )
        self.assertEqual(login.status_code, 401)
        body = login.json()
        self.assertEqual(body["code"], 401)
        self.assertEqual(body["message"], "账号或密码不对")
        self.assertIsNone(body["data"])

    def test_disabled_account(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "disabled", "password": "disabled123"},
        )
        self.assertEqual(login.status_code, 403)
        body = login.json()
        self.assertEqual(body["code"], 403)
        self.assertEqual(body["message"], "账号停用")

    def test_login_token_is_verifiable_jwt(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "admin", "password": "admin123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        token = login.json()["data"]["token"]
        self.assertEqual(len(token.split(".")), 3)
        claims = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        self.assertEqual(claims["login_account"], "admin")
        self.assertEqual(claims["sub"], login.json()["data"]["user"]["id"])
        self.assertTrue(claims.get("jti"))

    def test_tampered_jwt_is_unauthorized(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "admin", "password": "admin123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        token = login.json()["data"]["token"]
        header, payload, signature = token.split(".")
        flip = "A" if payload[-1] != "A" else "B"
        tampered = f"{header}.{payload[:-1]}{flip}.{signature}"
        me = self.client.get(
            "/api/v1/system-admin/session/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        self.assertEqual(me.status_code, 401, me.text)
        self.assertEqual(me.json()["code"], 401)

    def test_wrong_secret_jwt_is_unauthorized(self) -> None:
        now = beijing_now()
        forged = jwt.encode(
            {
                "sub": "1",
                "login_account": "admin",
                "nickname": "x",
                "tenant": "t",
                "jti": "forged-jti",
                "iat": now,
                "exp": now + timedelta(hours=1),
            },
            "wrong-secret-wrong-secret-wrong-secret-xx",
            algorithm="HS256",
        )
        me = self.client.get(
            "/api/v1/system-admin/session/me",
            headers={"Authorization": f"Bearer {forged}"},
        )
        self.assertEqual(me.status_code, 401, me.text)
        self.assertEqual(me.json()["code"], 401)

    def test_revoked_jti_is_unauthorized(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"login_account": "admin", "password": "admin123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        token = login.json()["data"]["token"]
        jti = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])["jti"]

        async def wipe_jti() -> None:
            settings = get_settings()
            redis = Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                password=settings.redis.password,
                decode_responses=True,
            )
            try:
                await redis.delete(f"adpilot:token:{jti}")
            finally:
                await redis.aclose()

        asyncio.run(wipe_jti())
        me = self.client.get(
            "/api/v1/system-admin/session/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me.status_code, 401, me.text)
        self.assertEqual(me.json()["code"], 401)


if __name__ == "__main__":
    unittest.main()
