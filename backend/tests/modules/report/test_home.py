"""首页：缺省字段、点击率、小时/日曲线、可见范围、账户筛选、全域展示点击不进列表。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError, register_exception_handlers
from app.core.times import BEIJING
from app.modules.report.controller import router
from app.modules.report.home import HomeQuery, _keep_group_pitchers, _pitchers, card_value, home_view, save_home_fields
from app.modules.report.refresh import (
    _uni_drama,
    _uni_group,
    _uni_money,
    _uni_pitcher,
    _uni_pitcher_drama,
    backfill_uni_show_click,
)
from app.modules.report.service import MANHUA_BASE, UNI_MONEY, ProjectLink, UniFact, uni_drama_rows, uni_metrics, uni_summary
from app.modules.report.serving import (
    ReportManhuaDramaDay,
    ReportManhuaPromotionDay,
    ReportUniDramaDay,
    ReportUniPitcherDay,
    ReportUniPitcherDramaDay,
)

ME = 3
DAY = date(2026, 10, 13)
EARLIER = date(2026, 10, 12)
HIDDEN_DAY = date(2026, 10, 11)


def _ns(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def drama_row(**kwargs: Any) -> SimpleNamespace:
    values: dict[str, Any] = {name: 0 for name in MANHUA_BASE}
    values.update(
        panel_key="",
        book_name="剧",
        drama_type="",
        channel="",
        publish_date=None,
        pitcher_names=["甲"],
        department_names=["组"],
        bid_types=[],
        panel_names=[],
        costed_promotion_ids=[],
    )
    values.update(kwargs)
    return _ns(**values)


def promotion_row(**kwargs: Any) -> SimpleNamespace:
    values: dict[str, Any] = {name: 0 for name in MANHUA_BASE}
    values.update(kwargs)
    return _ns(**values)


class EmptySession:
    async def scalar(self, statement: Any) -> None:
        return None

    async def scalars(self, statement: Any) -> Any:
        return self

    async def execute(self, statement: Any) -> Any:
        return self

    def all(self) -> list[Any]:
        return []

    def add(self, row: Any) -> None:
        raise AssertionError("首页 GET 不应写入")

    async def commit(self) -> None:
        return None


class MemSession(EmptySession):
    def __init__(self) -> None:
        self.row: Any = None

    async def scalar(self, statement: Any) -> Any:
        return self.row

    def add(self, row: Any) -> None:
        self.row = row


def _card(data: dict[str, Any], key: str) -> Any:
    return next(item["value"] for item in data["cards"] if item["key"] == key)


class FieldTests(unittest.TestCase):
    def test_ctr_is_recomputed_from_totals(self) -> None:
        hour_one = {"show_cnt": Decimal(100), "click_cnt": Decimal(50)}
        hour_two = {"show_cnt": Decimal(10), "click_cnt": Decimal(0)}
        total = {"show_cnt": Decimal(110), "click_cnt": Decimal(50)}
        self.assertEqual(card_value("manhua", hour_one, "ctr"), 50.0)
        self.assertEqual(card_value("manhua", hour_two, "ctr"), 0.0)
        self.assertEqual(card_value("manhua", total, "ctr"), 45.45)
        self.assertNotEqual(card_value("manhua", total, "ctr"), 25.0)
        self.assertEqual(card_value("manhua", {"show_cnt": Decimal(0), "click_cnt": Decimal(5)}, "ctr"), 0.0)
        self.assertEqual(
            card_value("uni_drama", {"all_show_cnt_trend": Decimal(0), "all_click_cnt_trend": Decimal(3)}, "ctr"),
            0.0,
        )

    def test_defaults_and_saved_fields_follow_the_account_and_surface(self) -> None:
        saved: dict[tuple[int, str], tuple[str, str, str] | None] = {(3, "manhua"): ("active", "convert_cnt", "stat_cost")}

        async def lookup(_session: Any, user_id: int, surface: str) -> tuple[str, str, str] | None:
            return saved.get((user_id, surface))

        async def run(user_id: str, **kwargs: Any) -> dict[str, Any]:
            with patch("app.modules.report.home._saved_fields", lookup):
                return await home_view(EmptySession(), {"id": user_id}, HomeQuery(**kwargs))

        iaa = asyncio.run(run("3", surface="manhua", charge_mode="IAA"))
        iap = asyncio.run(run("3", surface="manhua", charge_mode="IAP"))
        other = asyncio.run(run("9", surface="manhua", charge_mode="IAA"))
        uni = asyncio.run(run("3", surface="uni_drama"))
        self.assertEqual([item["key"] for item in iaa["cards"][2:]], ["active", "convert_cnt", "stat_cost"])
        self.assertEqual([item["key"] for item in iap["cards"][2:]], ["active", "convert_cnt", "stat_cost"])
        self.assertEqual([item["key"] for item in other["cards"][2:]], ["stat_cost", "click_cnt", "convert_cnt"])
        self.assertEqual(
            [item["key"] for item in uni["cards"]],
            ["all_show_cnt_trend", "ctr", "all_stat_cost_trend", "all_gmv_trend", "all_roi_trend"],
        )
        asyncio.run(home_view(EmptySession(), {"id": "3"}, HomeQuery(surface="manhua", charge_mode="IAA")))

    def test_save_replaces_the_row_and_rejects_a_bad_set(self) -> None:
        session = MemSession()
        saved = asyncio.run(save_home_fields(session, 3, "manhua", ["stat_cost", "click_cnt", "convert_cnt"]))
        self.assertEqual(saved, {"surface": "manhua", "fields": ["stat_cost", "click_cnt", "convert_cnt"]})
        self.assertEqual(session.row.user_id, 3)
        self.assertEqual((session.row.field_1, session.row.field_2, session.row.field_3), ("stat_cost", "click_cnt", "convert_cnt"))
        asyncio.run(save_home_fields(session, 3, "manhua", ["active", "convert_cnt", "click_cnt"]))
        self.assertEqual(session.row.field_1, "active")
        self.assertFalse(getattr(session, "added_twice", False))
        with self.assertRaises(ApiError) as caught:
            asyncio.run(save_home_fields(session, 3, "uni_drama", ["all_show_cnt_trend", "all_gmv_trend", "all_roi_trend"]))
        self.assertEqual(caught.exception.status_code, 422)
        with self.assertRaises(ApiError):
            asyncio.run(save_home_fields(session, 3, "manhua", ["stat_cost", "stat_cost", "click_cnt"]))


class CurveTests(unittest.TestCase):
    def test_one_day_is_hourly_and_skips_hours_without_a_snapshot(self) -> None:
        hour_rows = [
            (8, 1, 101, {"show_cnt": Decimal(100), "click_cnt": Decimal(50), "stat_cost": Decimal("10")}),
            (9, 2, 201, {"show_cnt": Decimal(10), "click_cnt": Decimal(0), "stat_cost": Decimal("5")}),
        ]
        links = {
            1: ProjectLink(1, 8, "剧", ME, "甲", 10, "组", charge_mode="IAP", bid_panel="小额"),
            2: ProjectLink(2, 8, "剧", 7, "乙", 11, "组2", charge_mode="IAP", bid_panel="小额"),
        }

        async def run() -> dict[str, Any]:
            with (
                patch("app.modules.report.home._manhua_hour_rows", AsyncMock(return_value=hour_rows)),
                patch("app.modules.report.home.crud.standard_links", AsyncMock(return_value=links)),
                patch("app.modules.report.home._load_model_rows", AsyncMock(side_effect=AssertionError("单日不读日表"))),
            ):
                return await home_view(
                    EmptySession(),
                    {"id": str(ME)},
                    HomeQuery(surface="manhua", charge_mode="IAP", date_start=DAY, date_end=DAY, curve="ctr"),
                )

        data = asyncio.run(run())
        self.assertEqual(data["grain"], "hour")
        self.assertEqual(_card(data, "show_cnt"), 110)
        self.assertEqual(_card(data, "ctr"), 45.45)
        self.assertEqual(data["curve"]["points"], [{"hour": 8, "value": 50.0}, {"hour": 9, "value": 0.0}])

    def test_many_days_and_open_range_read_day_rows(self) -> None:
        rows = [
            drama_row(stat_date=EARLIER, series_id=8, pitcher_ids=[ME, 7], stat_cost=Decimal("150")),
            drama_row(stat_date=EARLIER, series_id=9, pitcher_ids=[7], stat_cost=Decimal("50")),
            drama_row(stat_date=HIDDEN_DAY, series_id=9, pitcher_ids=[7], stat_cost=Decimal("80")),
            drama_row(stat_date=DAY, series_id=8, pitcher_ids=[ME], stat_cost=Decimal("10")),
        ]

        async def run(**kwargs: Any) -> dict[str, Any]:
            with (
                patch("app.modules.report.home._load_model_rows", AsyncMock(return_value=rows)) as loader,
                patch("app.modules.report.home._manhua_hour_rows", AsyncMock(side_effect=AssertionError("跨天不读小时"))),
            ):
                data = await home_view(EmptySession(), {"id": str(ME)}, HomeQuery(surface="manhua", charge_mode="IAP", curve="stat_cost", **kwargs))
                self.assertIs(loader.await_args.args[1], ReportManhuaDramaDay)
                return data

        spanned = asyncio.run(run(date_start=HIDDEN_DAY, date_end=DAY))
        self.assertEqual(spanned["grain"], "day")
        self.assertEqual(_card(spanned, "stat_cost"), 160.0)
        self.assertEqual([item["date"] for item in spanned["curve"]["points"]], ["2026-10-12", "2026-10-13"])
        self.assertEqual([item["value"] for item in spanned["curve"]["points"]], [150.0, 10.0])
        open_range = asyncio.run(run())
        self.assertEqual(_card(open_range, "stat_cost"), _card(spanned, "stat_cost"))
        self.assertEqual([item["date"] for item in open_range["curve"]["points"]], ["2026-10-12", "2026-10-13"])


class ScopeTests(unittest.TestCase):
    def _rows(self) -> list[SimpleNamespace]:
        return [
            drama_row(stat_date=EARLIER, series_id=8, pitcher_ids=[ME, 7], stat_cost=Decimal("150")),
            drama_row(stat_date=EARLIER, series_id=9, pitcher_ids=[7], stat_cost=Decimal("50")),
            drama_row(stat_date=DAY, series_id=8, pitcher_ids=[ME], stat_cost=Decimal("10")),
        ]

    def test_drama_card_keeps_co_pitchers_on_my_dramas_only(self) -> None:
        async def load(viewer: int | None) -> float:
            with (
                patch("app.modules.report.home._load_model_rows", AsyncMock(return_value=self._rows())),
                patch("app.modules.report.controller._viewer_id", AsyncMock(return_value=viewer)),
            ):
                data = await home_view(
                    EmptySession(),
                    {"id": str(ME)},
                    HomeQuery(surface="manhua", charge_mode="IAP", curve="stat_cost"),
                )
            return _card(data, "stat_cost")

        self.assertEqual(asyncio.run(load(ME)), 160.0)
        self.assertEqual(asyncio.run(load(None)), 210.0)

    def test_group_with_empty_scope_is_only_my_department(self) -> None:
        rows = [
            _ns(stat_date=DAY, department_id=10, all_stat_cost_trend=Decimal("100")),
            _ns(stat_date=DAY, department_id=11, all_stat_cost_trend=Decimal("40")),
        ]
        principal = {"id": str(ME), "login_account": "a", "data_scope": {"self_only": True, "department_ids": []}}

        async def run() -> dict[str, Any]:
            with (
                patch("app.modules.report.home._load_model_rows", AsyncMock(return_value=rows)),
                patch("app.modules.report.pages.crud.user_department_id", AsyncMock(return_value=10)),
            ):
                return await home_view(
                    EmptySession(),
                    principal,
                    HomeQuery(surface="uni_group", curve="all_stat_cost_trend"),
                )

        data = asyncio.run(run())
        self.assertEqual(_card(data, "all_stat_cost_trend"), 100.0)

    def test_department_and_users_are_a_union(self) -> None:
        class DeptSession(EmptySession):
            async def scalars(self, statement: Any) -> Any:
                return self

            def all(self) -> list[int]:
                return [4, 5]

        found = asyncio.run(
            _pitchers(DeptSession(), HomeQuery(surface="manhua", charge_mode="IAA", user_ids=(ME,), department_ids=(10,)))
        )
        self.assertEqual(found, {ME, 4, 5})

    def test_pitchers_outside_visibility_are_not_added(self) -> None:
        async def run() -> dict[str, Any]:
            with (
                patch("app.modules.report.home._pitchers", AsyncMock(return_value={7})),
                patch("app.modules.report.home._load_model_rows", AsyncMock(side_effect=AssertionError("空交集不退回全部"))),
            ):
                return await home_view(
                    EmptySession(),
                    {"id": str(ME)},
                    HomeQuery(surface="manhua", charge_mode="IAP", user_ids=(7,), curve="stat_cost"),
                )

        data = asyncio.run(run())
        self.assertEqual(_card(data, "stat_cost"), 0.0)
        self.assertEqual(data["curve"]["points"], [])

    def test_filtered_uni_drama_uses_the_pitchers_own_rows(self) -> None:
        seen: list[Any] = []

        async def load(_session: Any, model: Any, _filters: list[Any]) -> list[Any]:
            seen.append(model)
            return [_ns(stat_date=DAY, pitcher_id=ME, all_stat_cost_trend=Decimal("40"))]

        async def run() -> dict[str, Any]:
            with (
                patch("app.modules.report.home._pitchers", AsyncMock(return_value={ME})),
                patch("app.modules.report.controller._viewer_id", AsyncMock(return_value=None)),
                patch("app.modules.report.home._load_model_rows", load),
            ):
                return await home_view(
                    EmptySession(),
                    {"id": str(ME)},
                    HomeQuery(surface="uni_drama", user_ids=(ME,), curve="all_stat_cost_trend"),
                )

        data = asyncio.run(run())
        self.assertIs(seen[0], ReportUniPitcherDramaDay)
        self.assertNotIn(ReportUniDramaDay, seen)
        self.assertEqual(_card(data, "all_stat_cost_trend"), 40.0)

    def test_filtered_promotion_count_is_distinct_promotions_with_cost(self) -> None:
        rows = [
            promotion_row(stat_date=EARLIER, promotion_id=1, pitcher_id=ME, stat_cost=Decimal("10")),
            promotion_row(stat_date=EARLIER, promotion_id=2, pitcher_id=ME, stat_cost=Decimal("0")),
            promotion_row(stat_date=DAY, promotion_id=1, pitcher_id=ME, stat_cost=Decimal("0")),
        ]
        seen: list[Any] = []

        async def load(_session: Any, model: Any, _filters: list[Any]) -> list[Any]:
            seen.append(model)
            return rows

        async def lookup(_session: Any, user_id: int, surface: str) -> tuple[str, str, str]:
            return ("promotion_with_cost_count", "stat_cost", "click_cnt")

        async def run() -> dict[str, Any]:
            with (
                patch("app.modules.report.home._pitchers", AsyncMock(return_value={ME})),
                patch("app.modules.report.controller._viewer_id", AsyncMock(return_value=None)),
                patch("app.modules.report.home._saved_fields", lookup),
                patch("app.modules.report.home._load_model_rows", load),
            ):
                return await home_view(
                    EmptySession(),
                    {"id": str(ME)},
                    HomeQuery(surface="manhua", charge_mode="IAP", user_ids=(ME,), curve="promotion_with_cost_count"),
                )

        data = asyncio.run(run())
        self.assertIs(seen[0], ReportManhuaPromotionDay)
        self.assertEqual(_card(data, "promotion_with_cost_count"), 1)
        self.assertEqual(data["curve"]["points"][0]["value"], 1)
        self.assertEqual(data["curve"]["points"][1]["value"], 0)

    def test_group_keeps_people_whose_current_department_is_visible(self) -> None:
        class DeptSession(EmptySession):
            async def execute(self, statement: Any) -> Any:
                return self

            def all(self) -> list[tuple[int, int]]:
                return [(ME, 10), (7, 11), (8, 10)]

        kept = asyncio.run(_keep_group_pitchers(DeptSession(), {ME, 7, 8, 99}, {10}))
        self.assertEqual(kept, {ME, 8})


class UniShowClickTests(unittest.TestCase):
    def test_list_rows_omit_show_and_click_while_sums_keep_them(self) -> None:
        link = ProjectLink(1, 8, "剧", ME, "甲", 10, "组")
        fact = UniFact(
            "2026-10-13",
            1,
            metrics={
                "all_stat_cost_trend": Decimal("1"),
                "all_show_cnt_trend": Decimal("9"),
                "all_click_cnt_trend": Decimal("3"),
            },
        )
        row = uni_drama_rows([fact], {1: link}, DAY, DAY, None)[0]
        self.assertNotIn("all_show_cnt_trend", row)
        self.assertNotIn("all_click_cnt_trend", row)
        self.assertEqual(row["_sums"]["all_show_cnt_trend"], Decimal("9"))
        self.assertNotIn("all_show_cnt_trend", uni_metrics(row["_sums"]))
        self.assertNotIn("all_click_cnt_trend", uni_summary([row]))

    def test_refresh_writes_show_and_click_as_integers(self) -> None:
        raw = {name: Decimal("1") for name in (*UNI_MONEY, "new_project_count")}
        raw["all_show_cnt_trend"] = Decimal("12")
        raw["all_click_cnt_trend"] = Decimal("4")
        body = {
            "_sums": raw,
            "series_id": 8,
            "book_name": "剧",
            "platform_name": "番茄",
            "pitcher_ids": [ME],
            "pitcher_user_id": ME,
            "pitcher_name": "甲",
            "department_id": 10,
            "department_name": "组",
        }
        built = (
            _uni_drama(DAY, body),
            _uni_pitcher_drama(DAY, body),
            _uni_pitcher(DAY, body),
            _uni_group(DAY, body),
        )
        for item in built:
            self.assertEqual(item.all_show_cnt_trend, 12)
            self.assertEqual(item.all_click_cnt_trend, 4)
            self.assertIsInstance(item.all_show_cnt_trend, int)
        money = _uni_money(body)
        self.assertEqual(money["all_stat_cost_trend"], Decimal("1"))

    def test_backfill_updates_existing_rows_and_does_not_insert(self) -> None:
        class Conn:
            def __init__(self) -> None:
                self.sql: list[str] = []

            def execute(self, statement: Any) -> None:
                self.sql.append(str(statement))

        conn = Conn()
        backfill_uni_show_click(conn)
        text = "\n".join(conn.sql).upper()
        self.assertNotIn("INSERT", text)
        self.assertEqual(text.count("UPDATE"), 4)
        self.assertNotIn("SET ALL_STAT_COST_TREND", text)
        path = Path(__file__).resolve().parents[3] / "alembic" / "versions" / "20261014_02_uni_day_show_click.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn('down_revision: Union[str, None] = "20261014_01"', source)
        self.assertIn("backfill_uni_show_click(op.get_bind())", source)


def _client(principal: dict[str, Any] | None, session: Any | None = None) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    holder = session or EmptySession()

    async def _session() -> Any:
        yield holder

    app.dependency_overrides[get_session] = _session
    if principal is not None:
        app.dependency_overrides[require_token] = lambda: principal
    return TestClient(app, raise_server_exceptions=False)


class HttpTests(unittest.TestCase):
    def test_home_uses_token_not_menu(self) -> None:
        response = _client({"id": str(ME), "login_account": "a"}).get(
            "/api/v1/reports/home",
            params={"surface": "manhua", "charge_mode": "IAA"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual([item["key"] for item in body["data"]["cards"]], ["show_cnt", "ctr", "stat_cost", "click_cnt", "convert_cnt"])

    def test_anonymous_is_unauthorized(self) -> None:
        response = _client(None).get("/api/v1/reports/home", params={"surface": "uni_drama"})
        self.assertEqual(response.status_code, 401)

    def test_invalid_query_is_422(self) -> None:
        client = _client({"id": str(ME), "login_account": "a"})
        self.assertEqual(client.get("/api/v1/reports/home", params={"surface": "manhua"}).status_code, 422)
        self.assertEqual(
            client.get("/api/v1/reports/home", params={"surface": "uni_drama", "charge_mode": "IAA"}).status_code,
            422,
        )
        self.assertEqual(
            client.get("/api/v1/reports/home", params={"surface": "uni_drama", "date_start": "2026-10-13"}).status_code,
            422,
        )
        self.assertEqual(
            client.get(
                "/api/v1/reports/home",
                params={"surface": "uni_drama", "date_start": "2026-10-14", "date_end": "2026-10-13"},
            ).status_code,
            422,
        )
        self.assertEqual(
            client.get("/api/v1/reports/home", params={"surface": "uni_drama", "curve": "nope"}).status_code,
            422,
        )

    def test_put_replaces_fields(self) -> None:
        client = _client({"id": str(ME), "login_account": "a"}, MemSession())
        bad = client.put(
            "/api/v1/reports/home/fields",
            json={"surface": "uni_drama", "fields": ["all_show_cnt_trend", "all_gmv_trend", "all_roi_trend"]},
        )
        self.assertEqual(bad.status_code, 422)
        short = client.put("/api/v1/reports/home/fields", json={"surface": "manhua", "fields": ["stat_cost", "click_cnt"]})
        self.assertEqual(short.status_code, 422)
        ok = client.put(
            "/api/v1/reports/home/fields",
            json={"surface": "manhua", "fields": ["stat_cost", "click_cnt", "convert_cnt"]},
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["data"], {"surface": "manhua", "fields": ["stat_cost", "click_cnt", "convert_cnt"]})


class _Unused:
    """占位，避免测试文件引用未使用的日模型被误删时看不出来。"""

    models = (ReportUniPitcherDay, datetime, BEIJING)
