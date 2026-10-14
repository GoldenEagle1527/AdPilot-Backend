"""巨量、常读的长 id 返回给前端时是字符串，传进来时字符串和数字都认。"""

from __future__ import annotations

import json
import unittest

from app.core.envelope import Envelope
from app.core.pagination import PageData
from app.modules.ocean_ads.schema import (
    AccountItem,
    MaterialItem,
    ProjectBatchResult,
    ProjectBatchWrite,
    ProjectItem,
    PromotionBatchWrite,
    PromotionItem,
    UniProjectItem,
)

_PROJECT = 7691188278174826546
_PROMOTION = 7691188146411814975
_MATERIAL = 7690329043916685321
_ACCOUNT = 1877368580368602


def _money_row() -> dict:
    return {
        "stat_cost": "0.00",
        "revenue_today": "0.00",
        "revenue_total": "0.00",
        "revenue_today_rate": "0.00",
        "revenue_total_rate": "0.00",
        "show_cnt": 0,
        "cpm": "0.00",
        "click_cnt": 0,
        "ctr": "0.00",
        "cpc": "0.00",
    }


def _effect_row() -> dict:
    return {
        **_money_row(),
        "convert_cnt": 0,
        "convert_cost": "0.00",
        "convert_rate": "0.00",
        "active": 0,
        "recycle_amount": "0.00",
        "active_arpu": "0.00",
        "active_cost": "0.00",
    }


def _json(model: type, data: dict) -> dict:
    """和接口一样，套信封后按 JSON 输出。"""
    body = Envelope[PageData[model]].model_validate(
        {"code": 200, "message": "ok", "data": {"list": [data], "total": 1, "page": 1, "page_size": 20}}
    )
    return json.loads(body.model_dump_json(by_alias=True))["data"]["list"][0]


class LongIdIsTextTest(unittest.TestCase):
    def test_project_row(self) -> None:
        row = _json(
            ProjectItem,
            {
                "project_id": _PROJECT,
                "project_name": "p",
                "project_status": "开启",
                "account_id": _ACCOUNT,
                "account_name": "a",
                "budget": None,
                "promotion_links": [],
                **_effect_row(),
            },
        )
        self.assertEqual(row["project_id"], "7691188278174826546")
        self.assertEqual(row["account_id"], "1877368580368602")

    def test_promotion_row(self) -> None:
        row = _json(
            PromotionItem,
            {
                "promotion_id": _PROMOTION,
                "promotion_name": "g",
                "promotion_status": "投放中",
                "project_id": _PROJECT,
                "project_name": "p",
                "series_name": None,
                "book_id": None,
                "account_id": _ACCOUNT,
                "account_name": "a",
                "promotion_links": [],
                "budget": None,
                "reject_reasons": [],
                **_effect_row(),
            },
        )
        self.assertEqual(row["promotion_id"], "7691188146411814975")
        self.assertEqual(row["project_id"], "7691188278174826546")
        self.assertIsNone(row["book_id"])

    def test_material_row_keeps_our_video_id_a_number(self) -> None:
        row = _json(
            MaterialItem,
            {
                "material_id": _MATERIAL,
                "video_id": 12,
                "material_name": "m",
                "promotion_id": _PROMOTION,
                "promotion_name": "g",
                "project_id": _PROJECT,
                "project_name": "p",
                "account_id": _ACCOUNT,
                "account_name": "a",
                "stat_cost": "0.00",
                "show_cnt": 0,
                "click_cnt": 0,
                "ctr": "0.00",
                "cpc": "0.00",
                "convert_cnt": 0,
                "convert_cost": "0.00",
                "convert_rate": "0.00",
            },
        )
        self.assertEqual(row["material_id"], "7690329043916685321")
        self.assertEqual(row["video_id"], 12)

    def test_account_and_uni_rows(self) -> None:
        account = _json(
            AccountItem, {"account_id": _ACCOUNT, "account_name": "a", "balance": None, **_money_row()}
        )
        self.assertEqual(account["account_id"], "1877368580368602")
        uni = _json(
            UniProjectItem,
            {
                "project_id": _PROJECT,
                "project_name": "p",
                "project_status": "开启",
                "subject_name": None,
                "account_id": _ACCOUNT,
                "account_name": "a",
                "pitcher_user_id": 3,
                "pitcher_name": None,
                "series_name": None,
                "douyin_aweme_id": None,
                "douyin_name": None,
                "stat_cost": "0.00",
                "budget": None,
                "roi_goal": "-",
                "created_at": "2026-10-14T12:00:00+08:00",
                "create_result": "创建成功",
                "failure_reason": None,
            },
        )
        self.assertEqual(uni["project_id"], "7691188278174826546")
        self.assertEqual(uni["pitcher_user_id"], 3)

    def test_batch_result_ids(self) -> None:
        body = ProjectBatchResult(project_ids=[_PROJECT], promotion_count=2)
        self.assertEqual(json.loads(body.model_dump_json())["project_ids"], ["7691188278174826546"])


class LongIdInputTest(unittest.TestCase):
    def test_text_ids_keep_every_digit(self) -> None:
        body = ProjectBatchWrite.model_validate_json('{"project_ids": ["7691188278174826546"], "action": "暂停"}')
        self.assertEqual(body.project_ids, [_PROJECT])
        body = PromotionBatchWrite.model_validate_json(
            '{"promotion_ids": ["7691188146411814975"], "action": "开启"}'
        )
        self.assertEqual(body.promotion_ids, [_PROMOTION])

    def test_number_ids_still_accepted(self) -> None:
        body = ProjectBatchWrite.model_validate_json('{"project_ids": [80030001], "action": "暂停"}')
        self.assertEqual(body.project_ids, [80030001])
