"""启动时按 oceanengine.mock 选定客户端。业务模块不要 import 本文件。"""

from __future__ import annotations

from app.core.config import Settings
from app.modules.oceanengine.client import OceanEngineClient, OceanEnginePort
from app.modules.oceanengine.runtime import install_ocean_client


def install_ocean_client_for_settings(settings: Settings) -> OceanEnginePort:
    """mock 用假客户端，否则用只发 HTTP 的客户端。"""
    if settings.oceanengine.mock:
        from app.modules.oceanengine.fake_client import FakeOceanEngineClient

        client: OceanEnginePort = FakeOceanEngineClient()
    else:
        client = OceanEngineClient(settings.oceanengine)
    install_ocean_client(client)
    return client
