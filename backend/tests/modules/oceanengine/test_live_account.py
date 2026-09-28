"""把 test.env 对应应用里的真实账户回包收成夹具。

密钥只从仓库根 test.env 读取，不写进本文件。类型不对时不覆盖夹具。
"""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

from app.modules.oceanengine.service import _company_name
from tests.modules.oceanengine.live_env import load_test_credentials, test_env_path
from tests.modules.oceanengine.live_fetch import fetch_account_snapshot, snapshot_type_errors

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "account_snapshot.json"
_PROBE = Path(__file__).resolve().parent / "fixtures" / "live_delivery_probe.json"


class LiveAccountSnapshotTests(unittest.TestCase):
    def test_pull_account_and_store_fixture(self) -> None:
        """拉取授权账户和广告主。类型通过后写入 fixtures/account_snapshot.json。"""
        if not test_env_path().is_file():
            self.skipTest("仓库根没有 test.env")
        credentials = load_test_credentials()
        snapshot = asyncio.run(fetch_account_snapshot(credentials))
        errors = snapshot_type_errors(snapshot)
        self.assertEqual(errors, [], "回包类型与落库字段不一致，不写入夹具")
        _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        _FIXTURE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        saved = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(saved["app_id"], credentials.app_id)
        self.assertIsInstance(saved["authorized_accounts"], list)
        self.assertIsInstance(saved["advertisers"], list)

    def test_saved_snapshot_types(self) -> None:
        """已写入的夹具类型稳定，不访问开放平台。"""
        if not _FIXTURE.is_file():
            self.skipTest("还没有账户夹具")
        snapshot = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(snapshot_type_errors(snapshot), [])
        self.assertEqual(snapshot["authorized_accounts"][0]["advertiser_id"], 1872115109920903)
        self.assertEqual(snapshot["authorized_accounts"][0]["advertiser_name"], "深圳发行中心")
        self.assertGreater(snapshot["advertiser_total"], 0)
        self.assertGreater(len(snapshot["advertisers"]), 0)
        self.assertEqual(
            snapshot["advertisers"][0]["company"],
            "杭州濠酝网络科技有限公司第五分公司",
        )

    def test_live_project_and_promotion_types(self) -> None:
        """有项目和广告的真实账户。报表行是空的，不把消耗当成已经对上。"""
        probe = json.loads(_PROBE.read_text(encoding="utf-8"))
        project = probe["project_scalars"]
        promotion = probe["promotion_scalars"]
        self.assertIsInstance(project["project_id"], int)
        self.assertIsInstance(project["advertiser_id"], int)
        self.assertEqual(project["landing_type"], "MICRO_GAME")
        self.assertEqual(project["marketing_goal"], "VIDEO_AND_IMAGE")
        self.assertEqual(project["ad_type"], "ALL")
        self.assertEqual(project["delivery_mode"], "PROCEDURAL")
        self.assertEqual(project["opt_status"], "ENABLE")
        self.assertIsInstance(promotion["promotion_id"], int)
        self.assertIsInstance(promotion["project_id"], int)
        self.assertEqual(promotion["opt_status"], "ENABLE")
        self.assertEqual(probe["report_rows"], [])
        self.assertIn("delivery_range", probe["project_object_keys"])
        self.assertIn("delivery_setting", probe["project_object_keys"])
        self.assertIn("optimize_goal", probe["project_object_keys"])

    def test_public_info_company_accepts_list_body(self) -> None:
        """公开信息的 data 直接是数组时也能读到公司名。"""
        body = {
            "data": [
                {"id": 1877343430576522, "company": "杭州濠酝网络科技有限公司第五分公司"},
            ]
        }
        self.assertEqual(
            _company_name(body, 1877343430576522),
            "杭州濠酝网络科技有限公司第五分公司",
        )
