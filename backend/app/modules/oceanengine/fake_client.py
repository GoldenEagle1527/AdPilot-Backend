"""巨量假客户端。只在启动且 oceanengine.mock 为真时装上。业务模块不要 import。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text

from app.modules.account.model import OE_PRODUCT_ID_SEQ, OE_PROJECT_ID_SEQ

_COMPANY = (
    "番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2"
)
_SEQUENCES = frozenset({OE_PROJECT_ID_SEQ, OE_PRODUCT_ID_SEQ})


def _envelope(data: dict[str, Any]) -> dict[str, Any]:
    return {"code": 0, "message": "OK", "data": data}


async def _next_sequence(name: str) -> int:
    """与表默认值同一条 PostgreSQL 序列。发号不放进进程变量。"""
    if name not in _SEQUENCES:
        raise RuntimeError("未知发号序列")
    from app.core.db import get_engine

    async with get_engine().begin() as conn:
        value = await conn.scalar(text(f"SELECT nextval('{name}')"))
    if value is None:
        raise RuntimeError("序列没有返回值")
    return int(value)


class FakeOceanEngineClient:
    """不发 HTTP。项目和商品 id 走库序列，视频 id 为 local-{uuid}，换票用固定假令牌。"""

    requires_stored_token = False

    async def exchange_token(self, auth_code: str) -> dict[str, Any]:
        """授权码换成固定假票。"""
        return _envelope(
            {
                "access_token": "mock-access-token",
                "refresh_token": "mock-refresh-token",
                "advertiser_ids": [],
            }
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """续期换成另一组固定假票。"""
        return _envelope(
            {
                "access_token": "mock-access-token-2",
                "refresh_token": "mock-refresh-token-2",
            }
        )

    async def list_authorized_accounts(self, access_token: str) -> dict[str, Any]:
        """列出授权账户。"""
        return _envelope(
            {
                "list": [
                    {
                        "account_id": 1872115109920903,
                        "account_name": "深圳发行中心",
                        "account_type": "PLATFORM_ROLE_ENTERPRISE_BP_ADMIN",
                    }
                ]
            }
        )

    async def list_ebp_advertisers(
        self,
        access_token: str,
        enterprise_organization_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """列出企业组织下的 EBP 广告主。"""
        return _envelope(
            {
                "account_list": [
                    {
                        "account_id": 1873916032590219,
                        "account_name": "番茄漫剧测试户",
                        "account_type": "AD_NORMAL",
                    }
                ],
                "page_info": {"page": 1, "page_size": page_size, "total_page": 1},
            }
        )

    async def create_ebp_advertiser_task(
        self, access_token: str, enterprise_organization_id: int
    ) -> dict[str, Any]:
        """超过 1 万条时创建全量账户导出任务。"""
        return _envelope({"task_id": 1})

    async def list_ebp_advertiser_tasks(
        self, access_token: str, enterprise_organization_id: int, task_ids: list[int]
    ) -> dict[str, Any]:
        """查询导出任务状态。"""
        return _envelope(
            {"list": [{"task_id": task_ids[0] if task_ids else 1, "task_status": "COMPLETED"}]}
        )

    async def download_ebp_advertiser_task(
        self, access_token: str, enterprise_organization_id: int, task_id: int
    ) -> dict[str, Any]:
        """下载导出结果。"""
        return _envelope(
            {
                "account_list": [
                    {
                        "account_id": 1873916032590219,
                        "account_name": "番茄漫剧测试户",
                        "account_type": "AD_NORMAL",
                    }
                ]
            }
        )

    async def list_customer_center_advertisers(
        self,
        access_token: str,
        cc_account_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """列出旧版工作台下的广告主。"""
        return _envelope(
            {
                "list": [
                    {
                        "advertiser_id": 1873916032590219,
                        "advertiser_name": "番茄漫剧测试户",
                    }
                ],
                "page_info": {"page": 1, "page_size": page_size, "total_page": 1},
            }
        )

    async def fund_get(self, access_token: str, advertiser_id: int) -> dict[str, Any]:
        """查询广告主可用余额，单位元。"""
        return _envelope({"valid_balance": 100.5, "advertiser_id": advertiser_id})

    async def advertiser_public_info(
        self, access_token: str, advertiser_ids: list[int]
    ) -> dict[str, Any]:
        """查询广告主公开信息。"""
        return _envelope(
            {
                "advertisers": [
                    {
                        "id": 1873916032590219,
                        "company": _COMPANY,
                    }
                ]
            }
        )

    async def advertiser_info_query(
        self, access_token: str, account_ids: list[int]
    ) -> dict[str, Any]:
        """代理商查询广告主主体。"""
        return _envelope(
            {
                "account_detail_list": [
                    {
                        "advertiser_id": 1873916032590219,
                        "adv_company_name": _COMPANY,
                    }
                ]
            }
        )

    async def create_project(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """项目 id 取 oe_project 序列，从 7000000000000001 起。"""
        project_id = await _next_sequence(OE_PROJECT_ID_SEQ)
        return _envelope({"project_id": project_id})

    async def create_promotion(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """广告 id 用本地计数，不打开放平台。"""
        promotion_id = await _next_sequence(OE_PROJECT_ID_SEQ)
        return _envelope({"promotion_id": promotion_id + 100000})

    async def list_projects(self, access_token: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """假项目列表。识别 NB 时再并上本地 oe_project。"""
        return _envelope({"list": []})

    async def upload_video(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """视频 id 为 local- 加十六进制 uuid。"""
        return _envelope({"video_id": f"local-{uuid.uuid4().hex}"})

    async def custom_report(
        self, access_token: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """自定义报表。两条广告指标。"""
        return _envelope(
            {
                "list": [
                    {
                        "promotion_id": 8001,
                        "stat_cost": 120.0,
                        "attribution_micro_game_0d_roi": 0.3,
                    },
                    {
                        "promotion_id": 8002,
                        "stat_cost": 10.0,
                        "attribution_micro_game_0d_roi": 1.2,
                    },
                ]
            }
        )

    async def update_promotion_status(
        self, access_token: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """不返回失败项，调用方按本批全部成功处理。"""
        return _envelope({})

    async def upload_product(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """商品 id 取 oe_product 序列，从 9001 起。不返回 503。"""
        product_id = await _next_sequence(OE_PRODUCT_ID_SEQ)
        return _envelope({"product_id": product_id})

    async def upload_image(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """图片 id 用 img- 前缀。视频 id 才是 local-。概念上是 UPLOAD_BY_FILE。

        正文可以不带文件。这个客户端不读文件字节。
        """
        return _envelope({"id": f"img-{uuid.uuid4().hex}", "upload_type": "UPLOAD_BY_FILE"})
