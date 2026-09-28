"""组织版本由账户角色推出，不读接口里不存在的 ocean_version。"""

from __future__ import annotations

import unittest

from app.modules.oceanengine.sync import ocean_version_for_role


class OceanVersionTests(unittest.TestCase):
    def test_enterprise_bp_is_upgraded_org(self) -> None:
        self.assertEqual(
            ocean_version_for_role("PLATFORM_ROLE_ENTERPRISE_BP_ADMIN"),
            "升级版组织",
        )
        self.assertEqual(
            ocean_version_for_role("PLATFORM_ROLE_ENTERPRISE_BP_OPERATOR"),
            "升级版组织",
        )

    def test_customer_admin_is_legacy_workbench(self) -> None:
        self.assertEqual(ocean_version_for_role("CUSTOMER_ADMIN"), "旧版工作台")
        self.assertEqual(ocean_version_for_role("CUSTOMER_OPERATOR"), "旧版工作台")

    def test_other_role_keeps_the_raw_value(self) -> None:
        self.assertEqual(ocean_version_for_role("AGENT"), "AGENT")
