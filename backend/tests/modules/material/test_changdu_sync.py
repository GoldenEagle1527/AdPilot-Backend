from __future__ import annotations

import hashlib
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import ChangduSettings, PostgresSettings, RedisSettings, Settings
from app.modules.material.domain.changdu import parse_record, sign_get, sync_window
from app.modules.material.domain.queries import list_filters
from app.modules.material.domain.sync import credentials_ready, pull_window, sync_once
from app.modules.material.domain.times import beijing_today_prefix


def _settings(*, distributor_id: str = "", secret_key: str = "") -> Settings:
    return Settings(
        postgres=PostgresSettings(host="x", port=5432, database="d", user="u", password="p"),
        redis=RedisSettings(host="x", port=6379),
        changdu=ChangduSettings(distributor_id=distributor_id, secret_key=secret_key),
    )


class SignAndWindowTests(unittest.TestCase):
    def test_sign_matches_doc_concat(self) -> None:
        params = {"distributor_id": 1811111111, "page_index": 0, "page_size": 50}
        ts = 1618367023
        got = sign_get("1811111111", "ZMSa111111111111", ts, params)
        raw = "1811111111ZMSa11111111111116183670231811111111|0|50|"
        self.assertEqual(got, hashlib.md5(raw.encode()).hexdigest())

    def test_sync_window_around_1400_beijing(self) -> None:
        now = datetime(2026, 9, 20, 14, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.assertEqual(sync_window(now), ("2026-09-20", "2026-09-20"))

    def test_parse_record(self) -> None:
        rec = parse_record(
            {
                "thumb_url": "https://x",
                "book_id": "11",
                "playlet_id": 22,
                "book_name": "剧A",
                "episode_amount": 8,
                "category_text": "IAA短剧",
                "publish_status": 2,
                "delivery_status": True,
            }
        )
        self.assertEqual(rec.playlet_id, 22)
        self.assertEqual(rec.book_id, 11)
        self.assertEqual(rec.book_name, "剧A")
        self.assertTrue(rec.delivery_status)


class FilterTests(unittest.TestCase):
    def test_department_id_forces_empty(self) -> None:
        filters = list_filters(
            category_text=None,
            book_name=None,
            estimate_publish_time_from=None,
            estimate_publish_time_to=None,
            collected_at_from=None,
            collected_at_to=None,
            publish_status=None,
            listed_today=None,
            department_id="1",
            episode_amount_min=None,
            episode_amount_max=None,
        )
        self.assertEqual(len(filters), 1)
        self.assertEqual(str(filters[0]), "false")

    def test_listed_today_uses_beijing_date(self) -> None:
        now = datetime(2026, 9, 20, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(beijing_today_prefix(now), "2026-09-20")


class SyncSkipTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_credentials_is_noop(self) -> None:
        settings = _settings()
        self.assertFalse(credentials_ready(settings))
        self.assertEqual(await sync_once(settings), 0)

    async def test_pull_window_stops_when_page_covers_total(self) -> None:
        rec = parse_record({"playlet_id": 1, "book_name": "A"})
        calls: list[int] = []

        class _Client:
            async def fetch_page(self, **kwargs):
                calls.append(kwargs["page_index"])
                return 1, [rec]

        class _Session:
            async def execute(self, _stmt):
                return None

        written = await pull_window(
            _Client(),
            _Session(),  # type: ignore[arg-type]
            start_time="2026-09-20 13:30:00",
            end_time="2026-09-20 14:30:00",
            page_gap_seconds=0,
        )
        self.assertEqual(written, 1)
        self.assertEqual(calls, [0])


if __name__ == "__main__":
    unittest.main()
