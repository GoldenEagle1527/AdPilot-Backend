"""授权链接按 channel 选应用，不因配置了 app_id 改走自研。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.envelope import ApiError
from app.modules.oceanengine.oauth import authorize_url


def _live_settings() -> SimpleNamespace:
    return SimpleNamespace(
        oceanengine=SimpleNamespace(
            mock=False,
            app_id="1870855836080240",
            redirect_uri="",
        )
    )


class AuthorizeUrlChannelTests(unittest.IsolatedAsyncioTestCase):
    async def test_third_keeps_channel_app_when_live_app_id_is_set(self) -> None:
        app = SimpleNamespace(
            id=9,
            app_id=1870857293665690,
            agent_key="1",
            agency=False,
            material_auth=1,
            oauth_rid="tg29ccnkpzm",
        )
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=app)
        with (
            patch("app.modules.oceanengine.oauth.get_settings", return_value=_live_settings()),
            patch("app.modules.oceanengine.oauth._prepare", new=AsyncMock()),
        ):
            url = await authorize_url(session, "third")
        self.assertIn("app_id=1870857293665690", url)
        self.assertNotIn("agency", url)

    async def test_missing_channel_app_is_404_even_when_app_id_configured(self) -> None:
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        with (
            patch("app.modules.oceanengine.oauth.get_settings", return_value=_live_settings()),
            patch("app.modules.oceanengine.oauth._prepare", new=AsyncMock()),
        ):
            with self.assertRaises(ApiError) as raised:
                await authorize_url(session, "third")
        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.message, "该渠道没有有效应用")
