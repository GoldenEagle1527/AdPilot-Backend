"""假客户端发号和真客户端拒未定接口。请求路径不补种、不 import 假客户端。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.core.config import OceanEngineSettings
from app.core.db import get_session
from app.core.envelope import ApiError
from app.modules.oceanengine.client import OceanEngineClient
from app.modules.oceanengine.delivery import create_project
from app.modules.oceanengine.fake_client import FakeOceanEngineClient
from app.modules.oceanengine.runtime import install_ocean_client
from app.modules.oceanengine.schema import ProjectCreate
from app.modules.oceanengine import runtime


def _backend() -> Path:
    return Path(__file__).resolve().parents[3]


def _python_files():
    backend = _backend()
    roots = [backend / "app", backend / "scripts"]
    for root in roots:
        for path in root.rglob("*.py"):
            if ".venv" in path.parts or "alembic" in path.parts:
                continue
            yield path
    yield backend / "main.py"


class FakeClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_exchange_token_uses_fixed_mock_tokens(self) -> None:
        body = await FakeOceanEngineClient().exchange_token("auth-code")
        self.assertEqual(body["data"]["access_token"], "mock-access-token")
        self.assertEqual(body["data"]["refresh_token"], "mock-refresh-token")

    async def test_upload_video_id_is_local_uuid(self) -> None:
        body = await FakeOceanEngineClient().upload_video("", {"advertiser_id": 1, "video_url": "https://example.test/a.mp4"})
        video_id = body["data"]["video_id"]
        self.assertTrue(video_id.startswith("local-"))
        self.assertEqual(len(video_id), len("local-") + 32)

    async def test_product_ids_follow_the_database_sequence(self) -> None:
        from app.core.db import dispose_engine

        client = FakeOceanEngineClient()
        try:
            first = int((await client.upload_product("", {}))["data"]["product_id"])
            second = int((await client.upload_product("", {}))["data"]["product_id"])
            self.assertGreaterEqual(first, 9001)
            self.assertEqual(second, first + 1)
        finally:
            await dispose_engine()

    async def test_create_project_stores_one_sequence_value(self) -> None:
        previous = runtime._installed
        install_ocean_client(FakeOceanEngineClient())
        body = ProjectCreate(
            advertiser_id=1873916032590219,
            name="序列测试",
            landing_type="MICRO_GAME",
            marketing_goal="VIDEO_AND_IMAGE",
            ad_type="ALL",
            delivery_mode="MANUAL",
            subject_id=0,
        )
        try:
            async for session in get_session():
                try:
                    first = await create_project(session, body)
                    second = await create_project(session, body)
                    self.assertGreaterEqual(first["project_id"], 7000000000000001)
                    self.assertEqual(second["project_id"], first["project_id"] + 1)
                finally:
                    await session.rollback()
                break
        finally:
            install_ocean_client(previous)
            from app.core.db import dispose_engine

            await dispose_engine()


class RealClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_product_stays_unavailable(self) -> None:
        client = OceanEngineClient(OceanEngineSettings(mock=True))
        with self.assertRaises(ApiError) as raised:
            await client.upload_product("token", {"library_id": 1})
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.message, "商品库上传接口未定")


class OceanSeedPlacementTests(unittest.TestCase):
    def test_seed_is_only_called_from_startup(self) -> None:
        hits: list[str] = []
        for path in _python_files():
            text = path.read_text(encoding="utf-8")
            if "ensure_oceanengine_seed(" in text:
                hits.append(path.relative_to(_backend()).as_posix())
        self.assertEqual(sorted(hits), ["app/modules/account/seed.py", "main.py"])

    def test_frontend_demo_is_only_the_manual_script(self) -> None:
        hits: list[str] = []
        for path in _python_files():
            text = path.read_text(encoding="utf-8")
            if "ensure_frontend_demo" in text:
                hits.append(path.relative_to(_backend()).as_posix())
        self.assertEqual(hits, ["scripts/ensure_frontend_demo.py"])

    def test_request_modules_do_not_import_the_fake_client(self) -> None:
        ocean = _backend() / "app" / "modules" / "oceanengine"
        allowed = {"fake_client.py", "client_factory.py"}
        for path in ocean.glob("*.py"):
            if path.name in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("fake_client", text, path.name)
            self.assertNotIn("ensure_oceanengine_seed", text, path.name)
        for name in ("delivery.py", "oauth.py"):
            text = (ocean / name).read_text(encoding="utf-8")
            self.assertNotIn(".mock", text, name)
