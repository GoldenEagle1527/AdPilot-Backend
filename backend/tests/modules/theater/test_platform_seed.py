"""平台种子是番茄和鸥溪。启动时联合夹具只从巨量 mock 分支写入。不连库。"""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.seed_theater_platforms import _ROWS

BACKEND = Path(__file__).resolve().parents[3]


class PlatformSeedTests(unittest.TestCase):
    def test_rows_are_fanqie_and_ouxi(self) -> None:
        """种子就是番茄 1 和鸥溪 22。"""
        self.assertEqual(_ROWS[0]["id"], 1)
        self.assertEqual(_ROWS[0]["name"], "番茄")
        self.assertEqual(_ROWS[1]["id"], 22)
        self.assertEqual(_ROWS[1]["name"], "鸥溪")

    def test_startup_seeds_platforms_only_with_the_ocean_mock(self) -> None:
        """mock 分支只调用一次联合夹具，旧种子入口不再出现。"""
        text = (BACKEND / "main.py").read_text(encoding="utf-8")
        marker = "if settings.oceanengine.mock:"
        self.assertIn(marker, text)
        branch_start = text.index(marker) + len(marker)
        rebuild = "await _rebuild_report_days()"
        self.assertIn(rebuild, text[branch_start:])
        branch = text[branch_start : text.index(rebuild, branch_start)]
        self.assertEqual(branch.count("ensure_joint_mock("), 1)
        for retired in (
            "_seed_ocean_ads",
            "_seed_oceanengine",
            "ensure_oceanengine_seed",
            "ensure_report_mock",
            "ensure_ocean_ads_mock",
            "ensure_theater_platforms",
        ):
            self.assertNotIn(retired, branch)
        self.assertNotIn("fake_catalog", text)
        self.assertNotIn("9101", text)
