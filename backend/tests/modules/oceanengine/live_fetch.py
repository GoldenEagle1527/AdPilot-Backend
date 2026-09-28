"""用 test.env 的应用凭证，只读拉取已授权账户里的数据。

调用顺序：
1. POST /open_api/oauth2/refresh_token/  仅当库里已有该应用的 refresh_token
2. GET  /open_api/oauth2/advertiser/get/  已授权账户
3. GET  /open_api/2/ebp/advertiser/list/   升级版工作台下的广告主（含下级组织）
4. 有广告主时再查：
   GET /open_api/2/advertiser/fund/get/
   GET /open_api/2/advertiser/public_info/
   GET /open_api/v3.0/project/list/
   GET /open_api/v3.0/promotion/list/
   GET /open_api/v3.0/report/custom/get/

只有 APP_ID 和 Secret、库里没有该应用令牌时，开放平台发不出 access_token，本模块直接报错，不写夹具。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import httpx

from app.core.config import get_settings
from tests.modules.oceanengine.live_env import OceanEngineTestCredentials

_API = "https://api.oceanengine.com"
_AD = "https://ad.oceanengine.com"
_SAMPLE_SIZE = 5


class OceanEngineLiveError(RuntimeError):
    """拉取失败，且不能把回包写进测试夹具。"""


async def fetch_account_snapshot(credentials: OceanEngineTestCredentials) -> dict[str, Any]:
    """刷新该应用令牌并拉账户数据。返回值不含令牌。"""
    token = await _refresh(credentials)
    headers = {"Access-Token": token}
    async with httpx.AsyncClient(timeout=40) as http:
        authorized = await _get(http, headers, f"{_API}/open_api/oauth2/advertiser/get/")
        accounts = _list(authorized, "list")
        advertisers: list[dict[str, Any]] = []
        advertiser_total = 0
        seen: set[int] = set()
        for account in accounts:
            if not isinstance(account, dict):
                raise OceanEngineLiveError("授权账户列表里有非对象元素")
            _require_int(account, "advertiser_id", "授权账户")
            _require_str(account, "advertiser_name", "授权账户")
            if not isinstance(account.get("account_role"), str) or not account.get("account_role"):
                account_type = account.get("account_type")
                if not isinstance(account_type, str) or not account_type:
                    raise OceanEngineLiveError("授权账户的 account_role 不是 str")
                account["account_role"] = account_type
            role = str(account.get("account_role") or "")
            org_id = int(account["advertiser_id"])
            if role == "CUSTOMER_ADMIN":
                rows, total = await _customer_center(http, headers, org_id)
            elif role.startswith("PLATFORM_ROLE_ENTERPRISE_BP"):
                rows, total = await _ebp_advertisers(http, headers, org_id)
            else:
                rows, total = [], 0
            advertiser_total += total
            for row in rows:
                account_id = int(row["account_id"])
                if account_id in seen:
                    continue
                seen.add(account_id)
                advertisers.append(await _advertiser_detail(http, headers, row))
        return {
            "app_id": credentials.app_id,
            "authorized_accounts": [_public_account(item) for item in accounts if isinstance(item, dict)],
            "advertiser_total": advertiser_total,
            "advertisers": advertisers,
        }


def snapshot_type_errors(snapshot: dict[str, Any]) -> list[str]:
    """检查夹具里我们会落库的字段类型。空列表表示通过。"""
    errors: list[str] = []
    if not isinstance(snapshot.get("app_id"), int):
        errors.append("app_id 不是 int")
    if not isinstance(snapshot.get("advertiser_total"), int):
        errors.append("advertiser_total 不是 int")
    accounts = snapshot.get("authorized_accounts")
    if not isinstance(accounts, list):
        errors.append("authorized_accounts 不是 list")
        accounts = []
    for index, account in enumerate(accounts):
        errors.extend(_account_errors(account, f"authorized_accounts[{index}]"))
    advertisers = snapshot.get("advertisers")
    if not isinstance(advertisers, list):
        errors.append("advertisers 不是 list")
        return errors
    for index, item in enumerate(advertisers):
        prefix = f"advertisers[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} 不是 object")
            continue
        errors.extend(_id_name_errors(item, prefix, "account_id", "account_name"))
        if not isinstance(item.get("account_type"), str):
            errors.append(f"{prefix}.account_type 不是 str")
        balance = item.get("valid_balance")
        if balance is not None and not isinstance(balance, (int, float)):
            errors.append(f"{prefix}.valid_balance 不是 number")
        company = item.get("company")
        if company is not None and not isinstance(company, str):
            errors.append(f"{prefix}.company 不是 str")
        errors.extend(_collection_errors(item.get("projects"), f"{prefix}.projects", "project_id", "name"))
        errors.extend(
            _collection_errors(item.get("promotions"), f"{prefix}.promotions", "promotion_id", "promotion_name")
        )
        reports = item.get("reports")
        if not isinstance(reports, list):
            errors.append(f"{prefix}.reports 不是 list")
            continue
        for report_index, report in enumerate(reports):
            report_prefix = f"{prefix}.reports[{report_index}]"
            if not isinstance(report, dict):
                errors.append(f"{report_prefix} 不是 object")
                continue
            if not isinstance(report.get("promotion_id"), int):
                errors.append(f"{report_prefix}.promotion_id 不是 int")
            for metric in ("stat_cost", "attribution_micro_game_0d_roi"):
                value = report.get(metric)
                if not isinstance(value, str):
                    errors.append(f"{report_prefix}.{metric} 不是 str")
    return errors


async def _refresh(credentials: OceanEngineTestCredentials) -> str:
    settings = get_settings()
    postgres = settings.postgres
    host = "127.0.0.1" if postgres.host in {"postgres", "localhost"} else postgres.host
    connection = await asyncpg.connect(
        host=host,
        port=postgres.port,
        user=postgres.user,
        password=postgres.password,
        database=postgres.database,
    )
    try:
        row = await connection.fetchrow(
            """
            select t.refresh_token
            from oe_token t
            join oe_app a on a.id = t.oe_app_id
            where a.app_id = $1 and t.is_deleted = 0 and t.refresh_token is not null
            """,
            credentials.app_id,
        )
        if row is None:
            raise OceanEngineLiveError(
                f"应用 {credentials.app_id} 在 oe_token 里没有 refresh_token。"
                "APP_ID 和 Secret 不能单独换访问令牌，需要先完成一次授权回调。"
            )
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(
                f"{_API}/open_api/oauth2/refresh_token/",
                json={
                    "app_id": credentials.app_id,
                    "secret": credentials.secret,
                    "refresh_token": row["refresh_token"],
                    "grant_type": "refresh_token",
                },
            )
        body = response.json()
        if body.get("code") != 0:
            raise OceanEngineLiveError(f"刷新令牌失败：code={body.get('code')} {body.get('message')}")
        data = body.get("data") or {}
        access_token = str(data.get("access_token") or "")
        refresh_token = str(data.get("refresh_token") or "")
        if not access_token or not refresh_token:
            raise OceanEngineLiveError("刷新令牌成功但没有返回 access_token 或 refresh_token")
        now = datetime.now(timezone.utc)
        await connection.execute(
            """
            update oe_token
            set access_token = $1,
                refresh_token = $2,
                access_expire_at = $3,
                refresh_expire_at = $4,
                last_refresh_at = $5,
                last_error = null
            where oe_app_id = (select id from oe_app where app_id = $6)
            """,
            access_token,
            refresh_token,
            now + timedelta(seconds=int(data.get("expires_in") or 0)),
            now + timedelta(seconds=int(data.get("refresh_token_expires_in") or 0)),
            now,
            credentials.app_id,
        )
        return access_token
    finally:
        await connection.close()


async def _ebp_advertisers(
    http: httpx.AsyncClient, headers: dict[str, str], org_id: int
) -> tuple[list[dict[str, Any]], int]:
    body = await _get(
        http,
        headers,
        f"{_API}/open_api/2/ebp/advertiser/list/",
        {
            "enterprise_organization_id": org_id,
            "account_source": "AD",
            "filtering": json.dumps({"query_type": "TRAVERSE"}),
            "page": 1,
            "page_size": _SAMPLE_SIZE,
        },
    )
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    page = data.get("page_info") if isinstance(data.get("page_info"), dict) else {}
    total = int(page.get("total_number") or 0)
    rows = [_account_row(item) for item in _list(body, "account_list")]
    return rows[:_SAMPLE_SIZE], total


async def _customer_center(
    http: httpx.AsyncClient, headers: dict[str, str], org_id: int
) -> tuple[list[dict[str, Any]], int]:
    body = await _get(
        http,
        headers,
        f"{_AD}/open_api/2/customer_center/advertiser/list/",
        {"cc_account_id": org_id, "account_source": "AD", "page": 1, "page_size": _SAMPLE_SIZE},
    )
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    page = data.get("page_info") if isinstance(data.get("page_info"), dict) else {}
    total = int(page.get("total_number") or 0)
    return [_account_row(item) for item in _list(body, "list")][:_SAMPLE_SIZE], total


async def _advertiser_detail(
    http: httpx.AsyncClient, headers: dict[str, str], row: dict[str, Any]
) -> dict[str, Any]:
    account_id = int(row["account_id"])
    fund = await _get(
        http,
        headers,
        f"{_AD}/open_api/2/advertiser/fund/get/",
        {"advertiser_id": account_id},
    )
    info = await _get(
        http,
        headers,
        f"{_AD}/open_api/2/advertiser/public_info/",
        {"advertiser_ids": json.dumps([account_id])},
    )
    projects = await _optional_list(
        http,
        headers,
        f"{_API}/open_api/v3.0/project/list/",
        {"advertiser_id": account_id, "page": 1, "page_size": 20},
        "list",
    )
    promotions = await _optional_list(
        http,
        headers,
        f"{_API}/open_api/v3.0/promotion/list/",
        {"advertiser_id": account_id, "page": 1, "page_size": 20},
        "list",
    )
    reports = await _reports(http, headers, account_id)
    fund_data = fund.get("data") if isinstance(fund.get("data"), dict) else {}
    balance = fund_data.get("valid_balance")
    if balance is None:
        balance = fund_data.get("account_valid")
    return {
        "account_id": account_id,
        "account_name": row["account_name"],
        "account_type": row.get("account_type") or "",
        "valid_balance": float(balance) if isinstance(balance, (int, float, str)) and balance != "" else None,
        "company": _company(info, account_id),
        "projects": [_slim(item, ("project_id", "name", "landing_type", "opt_status")) for item in projects],
        "promotions": [
            _slim(item, ("promotion_id", "promotion_name", "project_id", "opt_status")) for item in promotions
        ],
        "reports": reports,
        "fund_code": fund.get("code"),
        "info_code": info.get("code"),
    }


async def _reports(
    http: httpx.AsyncClient, headers: dict[str, str], advertiser_id: int
) -> list[dict[str, Any]]:
    today = datetime.now().strftime("%Y-%m-%d")
    body = await _get(
        http,
        headers,
        f"{_API}/open_api/v3.0/report/custom/get/",
        {
            "advertiser_id": advertiser_id,
            "dimensions": json.dumps(["cdp_promotion_id"]),
            "metrics": json.dumps(["stat_cost", "attribution_micro_game_0d_roi"]),
            "filters": json.dumps([]),
            "start_time": f"{today} 00:00:00",
            "end_time": f"{today} 23:59:59",
            "order_by": json.dumps([{"field": "stat_cost", "type": "DESC"}]),
            "page": 1,
            "page_size": 20,
        },
    )
    if body.get("code") != 0:
        return []
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    parsed: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        dimensions = raw.get("dimensions") if isinstance(raw.get("dimensions"), dict) else {}
        metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
        promotion_text = str(dimensions.get("cdp_promotion_id") or "")
        if not promotion_text.isdigit():
            continue
        parsed.append(
            {
                "promotion_id": int(promotion_text),
                "stat_cost": str(metrics.get("stat_cost") or "0"),
                "attribution_micro_game_0d_roi": str(metrics.get("attribution_micro_game_0d_roi") or "0"),
            }
        )
    return parsed


async def _optional_list(
    http: httpx.AsyncClient,
    headers: dict[str, str],
    url: str,
    params: dict[str, Any],
    key: str,
) -> list[dict[str, Any]]:
    body = await _get(http, headers, url, params)
    if body.get("code") != 0:
        return []
    return [item for item in _list(body, key) if isinstance(item, dict)]


async def _get(
    http: httpx.AsyncClient,
    headers: dict[str, str],
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await http.get(url, headers=headers, params=params)
    try:
        body = response.json()
    except ValueError as exc:
        raise OceanEngineLiveError(f"{url} 返回不是 JSON") from exc
    if not isinstance(body, dict):
        raise OceanEngineLiveError(f"{url} 返回不是对象")
    if body.get("code") not in (0, None) and "oauth2/advertiser/get" in url:
        raise OceanEngineLiveError(f"授权账户失败：code={body.get('code')} {body.get('message')}")
    if "oauth2/advertiser/get" in url and body.get("code") != 0:
        raise OceanEngineLiveError(f"授权账户失败：code={body.get('code')} {body.get('message')}")
    if "ebp/advertiser/list" in url and body.get("code") != 0:
        raise OceanEngineLiveError(f"广告主列表失败：code={body.get('code')} {body.get('message')}")
    return body


def _list(body: dict[str, Any], key: str) -> list[Any]:
    data = body.get("data")
    if not isinstance(data, dict):
        return []
    rows = data.get(key)
    if not isinstance(rows, list):
        return []
    return rows


def _account_row(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise OceanEngineLiveError("广告主列表里有非对象元素")
    account_id = raw.get("account_id")
    if account_id is None:
        account_id = raw.get("advertiser_id")
    name = raw.get("account_name") or raw.get("advertiser_name") or ""
    if not isinstance(account_id, int) or not isinstance(name, str):
        raise OceanEngineLiveError("广告主 account_id 或名称类型不对")
    account_type = raw.get("account_type")
    return {
        "account_id": account_id,
        "account_name": name,
        "account_type": account_type if isinstance(account_type, str) else "",
    }


def _company(body: dict[str, Any], account_id: int) -> str | None:
    data = body.get("data")
    if isinstance(data, list):
        advertisers = data
    elif isinstance(data, dict):
        advertisers = data.get("advertisers")
    else:
        return None
    if not isinstance(advertisers, list):
        return None
    for item in advertisers:
        if not isinstance(item, dict):
            continue
        if int(item.get("id") or 0) == account_id:
            company = item.get("company")
            return company if isinstance(company, str) else None
    return None


def _public_account(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "advertiser_id": int(raw["advertiser_id"]),
        "advertiser_name": str(raw.get("advertiser_name") or ""),
        "account_role": str(raw.get("account_role") or ""),
        "is_valid": bool(raw.get("is_valid")),
    }


def _slim(raw: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    slim: dict[str, Any] = {}
    for key in keys:
        value = raw.get(key)
        if isinstance(value, (int, str)):
            slim[key] = value
    return slim


def _require_int(raw: dict[str, Any], key: str, label: str) -> None:
    if not isinstance(raw.get(key), int):
        raise OceanEngineLiveError(f"{label} 的 {key} 不是 int")


def _require_str(raw: dict[str, Any], key: str, label: str) -> None:
    if not isinstance(raw.get(key), str):
        raise OceanEngineLiveError(f"{label} 的 {key} 不是 str")


def _account_errors(account: Any, prefix: str) -> list[str]:
    if not isinstance(account, dict):
        return [f"{prefix} 不是 object"]
    return _id_name_errors(account, prefix, "advertiser_id", "advertiser_name") + (
        [] if isinstance(account.get("account_role"), str) else [f"{prefix}.account_role 不是 str"]
    )


def _id_name_errors(item: dict[str, Any], prefix: str, id_key: str, name_key: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(item.get(id_key), int):
        errors.append(f"{prefix}.{id_key} 不是 int")
    if not isinstance(item.get(name_key), str):
        errors.append(f"{prefix}.{name_key} 不是 str")
    return errors


def _collection_errors(rows: Any, prefix: str, id_key: str, name_key: str) -> list[str]:
    if not isinstance(rows, list):
        return [f"{prefix} 不是 list"]
    errors: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{prefix}[{index}] 不是 object")
            continue
        if id_key in row and not isinstance(row.get(id_key), int):
            errors.append(f"{prefix}[{index}].{id_key} 不是 int")
        if name_key in row and not isinstance(row.get(name_key), str):
            errors.append(f"{prefix}[{index}].{name_key} 不是 str")
    return errors
