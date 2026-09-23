"""巨量测试夹具。mock 时业务模块只读写这里的内存数据，不打开放平台。"""

from __future__ import annotations

from typing import Any

_next_project_id = 7000000000000001
_next_video_seq = 1
_next_product_id = 9001

ORGANIZATIONS: tuple[dict[str, Any], ...] = (
    {
        "advertiser_id": 1872115109920903,
        "advertiser_name": "深圳发行中心",
        "account_role": "CUSTOMER_ADMIN",
        "ocean_version": "升级版组织",
    },
)

ADVERTISERS: tuple[dict[str, Any], ...] = (
    {
        "account_id": 1873916032590219,
        "account_name": "番茄漫剧测试户",
        "valid_balance": 100.5,
        "adv_company_name": (
            "番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2"
        ),
        "organization_id": 1872115109920903,
    },
)

PROJECTS: list[dict[str, Any]] = []
VIDEOS: list[dict[str, Any]] = []
PRODUCTS: list[dict[str, Any]] = []
PROMOTIONS: list[dict[str, Any]] = []

OAUTH_TOKEN: dict[str, str] = {
    "access_token": "",
    "refresh_token": "",
}

REPORTS: tuple[dict[str, Any], ...] = (
    {
        "promotion_id": 8001,
        "stat_cost": 120.0,
        "attribution_micro_game_0d_roi": 0.3,
        "advertiser_id": 1873916032590219,
    },
    {
        "promotion_id": 8002,
        "stat_cost": 10.0,
        "attribution_micro_game_0d_roi": 1.2,
        "advertiser_id": 1873916032590219,
    },
)


def remember_token(access_token: str, refresh_token: str) -> dict[str, str]:
    """记下换票结果，供本进程后续 mock 调用读取。"""
    OAUTH_TOKEN["access_token"] = access_token
    OAUTH_TOKEN["refresh_token"] = refresh_token
    return dict(OAUTH_TOKEN)


def append_project(row: dict[str, Any]) -> dict[str, Any]:
    """追加项目并分配 project_id。"""
    global _next_project_id
    saved = {**row, "project_id": _next_project_id}
    _next_project_id += 1
    PROJECTS.append(saved)
    return dict(saved)


def append_video(row: dict[str, Any]) -> dict[str, Any]:
    """追加视频，video_id 为 mock-video-N，状态为完成。"""
    global _next_video_seq
    saved = {
        **row,
        "video_id": f"mock-video-{_next_video_seq}",
        "status": "完成",
    }
    _next_video_seq += 1
    VIDEOS.append(saved)
    return dict(saved)


def append_product(row: dict[str, Any]) -> dict[str, Any]:
    """追加商品，product_id 从 9001 起。"""
    global _next_product_id
    saved = {**row, "product_id": _next_product_id}
    _next_product_id += 1
    PRODUCTS.append(saved)
    return dict(saved)


def upsert_promotion(advertiser_id: int, promotion_id: int, opt_status: str) -> dict[str, Any]:
    """按广告 id 改状态；没有则先建再改。"""
    for row in PROMOTIONS:
        if int(row["promotion_id"]) == promotion_id:
            row["advertiser_id"] = advertiser_id
            row["opt_status"] = opt_status
            return dict(row)
    saved = {
        "advertiser_id": advertiser_id,
        "promotion_id": promotion_id,
        "opt_status": opt_status,
    }
    PROMOTIONS.append(saved)
    return dict(saved)
