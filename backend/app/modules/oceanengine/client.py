"""巨量引擎换票与账户查询。默认 mock，不打真实开放平台。"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import OceanEngineSettings, get_settings
from app.core.envelope import ApiError

_MOCK_COMPANY = (
    "番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2"
)


class OceanEngineError(RuntimeError):
    """巨量引擎 OpenAPI 调用失败。"""


class OceanEngineClient:
    """换票、账户查询、建项目、上传、报表与广告状态。mock 不发 HTTP。"""

    def __init__(
        self,
        settings: OceanEngineSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """缺省从 deployment yaml 读巨量配置。传入的 httpx 客户端由调用方关闭。"""
        if settings is None:
            settings = get_settings().oceanengine
        self._settings = settings
        self._client = client

    async def exchange_token(self, auth_code: str) -> dict[str, Any]:
        """用授权码换 access_token。"""
        if self._settings.mock:
            return _envelope(
                {
                    "access_token": "mock-access-token",
                    "refresh_token": "mock-refresh-token",
                    "advertiser_ids": [],
                }
            )
        return await self._request(
            "POST",
            f"{self._settings.api_base}/open_api/oauth2/access_token/",
            json_body={
                "app_id": self._settings.app_id,
                "secret": self._settings.secret,
                "auth_code": auth_code,
                "grant_type": "auth_code",
            },
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """用 refresh_token 换新的访问令牌。"""
        if self._settings.mock:
            return _envelope(
                {
                    "access_token": "mock-access-token-2",
                    "refresh_token": "mock-refresh-token-2",
                }
            )
        return await self._request(
            "POST",
            f"{self._settings.api_base}/open_api/oauth2/refresh_token/",
            json_body={
                "app_id": self._settings.app_id,
                "secret": self._settings.secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    async def list_authorized_accounts(self, access_token: str) -> dict[str, Any]:
        """列出授权账户。"""
        if self._settings.mock:
            return _envelope(
                {
                    "list": [
                        {
                            "advertiser_id": 1872115109920903,
                            "advertiser_name": "深圳发行中心",
                            "account_role": "CUSTOMER_ADMIN",
                        }
                    ]
                }
            )
        return await self._request(
            "GET",
            f"{self._settings.api_base}/open_api/oauth2/advertiser/get/",
            params={"access_token": access_token},
        )

    async def list_ebp_advertisers(
        self, access_token: str, enterprise_organization_id: int
    ) -> dict[str, Any]:
        """列出企业组织下的 EBP 广告主。"""
        if self._settings.mock:
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
        return await self._request(
            "GET",
            f"{self._settings.api_base}/open_api/2/ebp/advertiser/list/",
            headers={"Access-Token": access_token},
            params={"enterprise_organization_id": enterprise_organization_id},
        )

    async def fund_get(self, access_token: str, advertiser_id: int) -> dict[str, Any]:
        """查询广告主可用余额，单位元。"""
        if self._settings.mock:
            return _envelope({"valid_balance": 100.5, "advertiser_id": advertiser_id})
        return await self._request(
            "GET",
            f"{self._settings.ad_base}/open_api/2/advertiser/fund/get/",
            headers={"Access-Token": access_token},
            params={"advertiser_id": advertiser_id},
        )

    async def advertiser_info_query(
        self, access_token: str, account_ids: list[int]
    ) -> dict[str, Any]:
        """查询广告主主体名称。account_ids 以重复 query 发出。"""
        if self._settings.mock:
            return _envelope(
                {
                    "account_detail_list": [
                        {
                            "advertiser_id": 1873916032590219,
                            "adv_company_name": _MOCK_COMPANY,
                        }
                    ]
                }
            )
        return await self._request(
            "GET",
            f"{self._settings.api_base}/open_api/2/agent/advertiser_info/query/",
            headers={"Access-Token": access_token},
            params={"account_ids": account_ids},
        )

    async def create_project(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """创建项目。mock 固定 project_id。"""
        if self._settings.mock:
            return _envelope({"project_id": 7000000000000001})
        return await self._request(
            "POST",
            f"{self._settings.api_base}/open_api/v3.0/project/create/",
            headers={"Access-Token": access_token},
            json_body=body,
        )

    async def upload_video(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """上传广告视频。mock 固定 video_id。"""
        if self._settings.mock:
            return _envelope({"video_id": "mock-video-1"})
        return await self._request(
            "POST",
            f"{self._settings.api_base}/open_api/2/file/video/ad/",
            headers={"Access-Token": access_token},
            json_body=body,
        )

    async def custom_report(
        self, access_token: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """自定义报表。官方是 GET。mock 返回两条广告指标。"""
        if self._settings.mock:
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
        return await self._request(
            "GET",
            f"{self._settings.api_base}/open_api/v3.0/report/custom/get/",
            headers={"Access-Token": access_token},
            params=params,
        )

    async def update_promotion_status(
        self, access_token: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """更新广告启停。data 内含 promotion_id 与 opt_status，DISABLE 为暂停。"""
        if self._settings.mock:
            return _envelope({})
        return await self._request(
            "POST",
            f"{self._settings.api_base}/open_api/v3.0/promotion/status/update/",
            headers={"Access-Token": access_token},
            json_body=body,
        )

    async def upload_product(self, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
        """商品库上传。开放平台 path 未定，mock 以外拒绝请求。"""
        if self._settings.mock:
            return _envelope({"product_id": 9001})
        raise ApiError(503, "商品库上传接口未定")

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._client is None:
            async with httpx.AsyncClient(timeout=30) as http:
                response = await http.request(method, url, headers=headers, params=params, json=json_body)
        else:
            response = await self._client.request(method, url, headers=headers, params=params, json=json_body)
        return _parse(response)


def _envelope(data: dict[str, Any]) -> dict[str, Any]:
    return {"code": 0, "message": "OK", "data": data}


def _parse(response: httpx.Response) -> dict[str, Any]:
    if response.status_code != 200:
        raise OceanEngineError(f"巨量引擎 HTTP 失败：{response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        raise OceanEngineError("巨量引擎返回不是 JSON") from exc
    if not isinstance(body, dict) or body.get("code") != 0:
        code = body.get("code") if isinstance(body, dict) else None
        message = body.get("message") if isinstance(body, dict) else None
        raise OceanEngineError(f"巨量引擎业务失败：code={code} {message}")
    return body
