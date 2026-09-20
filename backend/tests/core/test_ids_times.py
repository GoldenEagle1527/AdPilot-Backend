from __future__ import annotations

from datetime import datetime, timezone
from unittest import TestCase

from app.core.ids import new_id
from app.core.times import iso8601_z


class CoreIdsTimesTests(TestCase):
    def test_new_id_is_decimal_string(self) -> None:
        a, b = new_id(), new_id()
        self.assertTrue(a.isdigit())
        self.assertTrue(b.isdigit())
        self.assertNotEqual(a, b)

    def test_iso8601_z_uses_utc_suffix(self) -> None:
        value = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(iso8601_z(value), "2026-09-20T12:00:00Z")
