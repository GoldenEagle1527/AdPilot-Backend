from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from app.core.times import beijing_iso

_BEIJING = ZoneInfo("Asia/Shanghai")


class CoreTimesTests(TestCase):
    def test_iso8601_uses_beijing_offset(self) -> None:
        """对外时间带北京 +08:00。"""
        value = datetime(2026, 9, 20, 12, 0, 0, tzinfo=_BEIJING)
        self.assertEqual(beijing_iso(value), "2026-09-20T12:00:00+08:00")
