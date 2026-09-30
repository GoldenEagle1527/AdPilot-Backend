"""全域模板的保存、列表，以及投手自己的抖音号分配。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError, register_exception_handlers
from app.core.times import BEIJING
from app.modules.account.model import DeliverySubject, DouyinAccount
from app.modules.standard_delivery.model import DeliveryTemplate
from app.modules.uni_template.controller import router
from app.modules.uni_template.crud import pitcher_douyin_stmt, uni_name_taken_stmt
from app.modules.uni_template.schema import DouyinAssignWrite, TemplateQuery, TemplateWrite
from app.modules.uni_template.service import (
    assign_douyin,
    create_template,
    delete_template,
    list_templates,
    require_uni_subject,
    template_filters,
    update_template,
)

CREATED = datetime(2026, 9, 30, 11, 0, tzinfo=BEIJING)
PREFIX = "/api/v1/uni-templates"


class FakeResult:
    """假 execute 结果。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one(self) -> Any:
        """返回唯一一行。分页总数用。"""
        return self._rows[0]

    def scalar_one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None

    def one_or_none(self) -> Any:
        """返回首行元组或实体，没有则 None。"""
        return self._rows[0] if self._rows else None

    def scalars(self) -> FakeResult:
        """让 scalars().all() 走同一份行。"""
        return self

    def all(self) -> list[Any]:
        """返回全部预置行。"""
        return self._rows


class FakeSession:
    """假会话：execute 按顺序吐预置结果。"""

    def __init__(self, results: list[list[Any]] | None = None) -> None:
        self.results = list(results or [])
        self.statements: list[Any] = []
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。"""
        self.statements.append(statement)
        rows = self.results.pop(0) if self.results else []
        return FakeResult(rows)

    def add(self, row: Any) -> None:
        """记下待插入行。"""
        self.added.append(row)

    async def commit(self) -> None:
        """记一次提交。"""
        self.commits += 1

    async def refresh(self, row: Any) -> None:
        """补上库里才有的主键和时间。"""
        row.id = row.id or 40
        row.created_date = row.created_date or CREATED
        row.updated_date = CREATED


def make_subject(**kwargs: Any) -> DeliverySubject:
    """造一条全域投放主体。"""
    row = DeliverySubject(
        name=kwargs.get("name", "全域主体"),
        subject_no=200,
        delivery_mode=kwargs.get("delivery_mode", "uni"),
        theater_name="番茄",
        theater_kind="端原生",
        charge_mode=kwargs.get("charge_mode", "IAA"),
        min_bid=Decimal("1.00"),
        max_bid=Decimal("2.00"),
        material_account_id=1,
        dual_bid=False,
    )
    row.id = kwargs.get("id", 7)
    return row


def make_template(**kwargs: Any) -> DeliveryTemplate:
    """造一条已在库里的全域模板。"""
    row = DeliveryTemplate(
        name=kwargs.get("name", "全域甲"),
        delivery_mode="uni",
        charge_mode=kwargs.get("charge_mode", "IAA"),
        subject_id=kwargs.get("subject_id", 7),
        bid_panels=[],
        ads_per_account=None,
        project_budget=kwargs.get("project_budget", Decimal("100.00")),
        roi_coefficient=kwargs.get("roi_coefficient", Decimal("1.200")),
        aigc_dynamic_creative=kwargs.get("aigc_dynamic_creative", True),
        title_select_mode=kwargs.get("title_select_mode", "manual"),
    )
    row.id = kwargs.get("id", 11)
    row.is_deleted = 0
    row.created_date = CREATED
    row.updated_date = CREATED
    return row


def make_douyin(**kwargs: Any) -> DouyinAccount:
    """造一条抖音号。默认是全域。"""
    row = DouyinAccount(
        aweme_id=kwargs.get("aweme_id", "aweme-u"),
        name=kwargs.get("name", "全域号"),
        delivery_mode=kwargs.get("delivery_mode", "uni"),
        enabled=kwargs.get("enabled", True),
    )
    row.id = kwargs.get("id", 4)
    row.is_deleted = 0
    return row


def body(**kwargs: Any) -> TemplateWrite:
    """一份合法的全域模板入参。"""
    data: dict[str, Any] = {
        "name": " 全域甲 ",
        "subject_id": 7,
        "charge_mode": "IAA",
        "project_budget": "88.50",
        "roi_coefficient": "1.25",
        "aigc_dynamic_creative": True,
        "title_select_mode": "manual",
    }
    data.update(kwargs)
    return TemplateWrite(**data)


def http_client(session: FakeSession, *, login: bool = True, user_id: str = "3") -> TestClient:
    """挂上本模块路由。"""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    if login:
        app.dependency_overrides[require_token] = lambda: {
            "id": user_id,
            "nickname": "投手",
            "login_account": "pitcher",
            "tenant": "agent",
        }
    return TestClient(app)


class BodyTests(unittest.TestCase):
    def test_name_is_stripped_and_title_mode_is_closed(self) -> None:
        """名称去空白。标题选择只有手动和自动。"""
        self.assertEqual(body().name, "全域甲")
        with self.assertRaises(ValidationError):
            body(title_select_mode="mixed")

    def test_budget_must_be_positive_and_ids_unique(self) -> None:
        """预算要大于 0。一次分配里的抖音号不能重复。"""
        with self.assertRaises(ValidationError):
            body(project_budget="0")
        with self.assertRaises(ValidationError):
            DouyinAssignWrite(douyin_account_ids=[4, 4])

    def test_standard_subject_is_rejected(self) -> None:
        """标准主体不能挂到全域模板上。"""
        with self.assertRaises(ApiError) as caught:
            require_uni_subject(make_subject(delivery_mode="standard"), "IAA")
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "主体不是全域投放")


class FilterTests(unittest.TestCase):
    def test_list_is_uni_and_shared(self) -> None:
        """列表只看未删除的全域模板，不按投手拆。"""
        sql = " AND ".join(
            str(item.compile(compile_kwargs={"literal_binds": True}))
            for item in template_filters(TemplateQuery(name="甲", subject_id=7, charge_mode="IAP"))
        )
        self.assertIn("delivery_template.delivery_mode = 'uni'", sql)
        self.assertIn("delivery_template.is_deleted = 0", sql)
        self.assertIn("delivery_template.charge_mode = 'IAP'", sql)
        self.assertIn("delivery_template.subject_id = 7", sql)
        self.assertNotIn("user_id", sql)

    def test_name_and_douyin_lookup_stay_on_uni_rows(self) -> None:
        """重名只在全域里算。抖音号只取当前投手挂上的全域号。"""
        taken = str(uni_name_taken_stmt("IAA", "全域甲", 11).compile(compile_kwargs={"literal_binds": True}))
        links = str(pitcher_douyin_stmt([11, 12], 3).compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("delivery_template.delivery_mode = 'uni'", taken)
        self.assertIn("delivery_template.id != 11", taken)
        self.assertIn("delivery_template_douyin.user_id = 3", links)
        self.assertIn("douyin_account.delivery_mode = 'uni'", links)
        self.assertNotIn("delivery_mode = 'standard'", links)


class SaveTests(unittest.TestCase):
    def test_create_stores_uni_columns_and_no_douyin(self) -> None:
        """新增写全域列，标准列留空，名称已去空白。"""
        session = FakeSession([[make_subject()], []])
        item = asyncio.run(create_template(session, body()))
        self.assertEqual(item["name"], "全域甲")
        self.assertEqual(item["subject_name"], "全域主体")
        self.assertEqual(item["charge_mode"], "IAA")
        self.assertEqual(item["project_budget"], "88.50")
        self.assertEqual(item["roi_coefficient"], "1.250")
        self.assertTrue(item["aigc_dynamic_creative"])
        self.assertEqual(item["title_select_mode"], "manual")
        self.assertEqual(item["douyin_accounts"], [])
        self.assertEqual(item["created_at"], "2026-09-30T11:00:00+08:00")
        row = session.added[0]
        self.assertEqual(row.delivery_mode, "uni")
        self.assertIsNone(row.ads_per_account)
        self.assertEqual(row.bid_panels, [])
        self.assertEqual(session.commits, 1)

    def test_missing_subject_does_not_insert(self) -> None:
        """主体不存在 404，不写。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_template(session, body()))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.added, [])

    def test_duplicate_name_is_conflict(self) -> None:
        """同一变现模式下重名 409。"""
        session = FakeSession([[make_subject()], [9]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(create_template(session, body()))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(session.commits, 0)

    def test_update_replaces_fields_and_keeps_assignments(self) -> None:
        """整表保存改预算和标题模式，再读回当前投手的号。"""
        template = make_template()
        subject = make_subject()
        account = make_douyin()
        session = FakeSession([[(template, subject)], [subject], [], [(template.id, account)]])
        item = asyncio.run(update_template(session, 11, body(title_select_mode="auto", project_budget="20"), 3))
        self.assertEqual(item["title_select_mode"], "auto")
        self.assertEqual(item["project_budget"], "20.00")
        self.assertEqual(item["douyin_accounts"], [{"id": "4", "aweme_id": "aweme-u", "name": "全域号"}])
        self.assertEqual(template.ads_per_account, None)
        self.assertEqual(session.commits, 1)

    def test_delete_is_soft(self) -> None:
        """删除只打软删标记。"""
        template = make_template()
        session = FakeSession([[(template, make_subject())]])
        item = asyncio.run(delete_template(session, 11))
        self.assertEqual(item, {"id": "11", "deleted": True})
        self.assertEqual(template.is_deleted, 1)
        self.assertIsNotNone(template.deleted_at)

    def test_list_shows_only_the_callers_accounts(self) -> None:
        """模板人人可见，抖音号只带回当前投手的。"""
        template = make_template()
        subject = make_subject()
        account = make_douyin()
        session = FakeSession([[1], [(template, subject)], [(template.id, account)]])
        page = asyncio.run(list_templates(session, TemplateQuery(), 3))
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["list"][0]["id"], "11")
        self.assertEqual(page["list"][0]["douyin_accounts"][0]["aweme_id"], "aweme-u")
        sql = str(session.statements[2].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("delivery_template_douyin.user_id = 3", sql)


class AssignTests(unittest.TestCase):
    def test_assign_replaces_only_this_pitchers_accounts(self) -> None:
        """替换当前投手的号，顺序跟请求走。"""
        template = make_template()
        first = make_douyin(id=4, aweme_id="a")
        second = make_douyin(id=5, aweme_id="b", name="乙")
        session = FakeSession([[(template, make_subject())], [first, second], [4, 5], []])
        item = asyncio.run(assign_douyin(session, 11, DouyinAssignWrite(douyin_account_ids=[5, 4]), 3))
        self.assertEqual([row["id"] for row in item["douyin_accounts"]], ["5", "4"])
        self.assertEqual(session.commits, 1)
        added = [row.douyin_account_id for row in session.added]
        self.assertEqual(added, [5, 4])
        self.assertTrue(all(row.user_id == 3 for row in session.added))
        delete_sql = str(session.statements[3].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("delivery_template_douyin.user_id = 3", delete_sql)

    def test_empty_list_clears_without_loading_accounts(self) -> None:
        """空数组清空当前投手的分配。"""
        session = FakeSession([[(make_template(), make_subject())], []])
        item = asyncio.run(assign_douyin(session, 11, DouyinAssignWrite(douyin_account_ids=[]), 3))
        self.assertEqual(item["douyin_accounts"], [])
        self.assertEqual(session.added, [])
        self.assertEqual(session.commits, 1)

    def test_standard_account_is_rejected(self) -> None:
        """标准号不能挂到全域模板上。"""
        session = FakeSession([[(make_template(), make_subject())], [make_douyin(delivery_mode="standard")]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(assign_douyin(session, 11, DouyinAssignWrite(douyin_account_ids=[4]), 3))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "只能分配全域抖音号")
        self.assertEqual(session.commits, 0)

    def test_account_must_belong_to_the_pitcher(self) -> None:
        """没分给当前投手的全域号不能挂。"""
        session = FakeSession([[(make_template(), make_subject())], [make_douyin()], []])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(assign_douyin(session, 11, DouyinAssignWrite(douyin_account_ids=[4]), 3))
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.message, "抖音号未分配给当前投手")
        self.assertEqual(session.commits, 0)

    def test_missing_template_is_not_found(self) -> None:
        """标准模板 id 或已删模板都当不存在。"""
        session = FakeSession([[]])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(assign_douyin(session, 11, DouyinAssignWrite(douyin_account_ids=[4]), 3))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(session.commits, 0)


class HttpTests(unittest.TestCase):
    def test_login_is_required(self) -> None:
        """未登录不能看模板。"""
        client = http_client(FakeSession(), login=False)
        res = client.get(PREFIX)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["message"], "未带或 Token 无效")

    def test_create_returns_the_envelope(self) -> None:
        """新增走统一信封，成功 code 是 200。"""
        session = FakeSession([[make_subject()], []])
        client = http_client(session)
        res = client.post(PREFIX, json=body().model_dump(mode="json"))
        self.assertEqual(res.status_code, 200)
        body_json = res.json()
        self.assertEqual(body_json["code"], 200)
        self.assertEqual(body_json["message"], "成功")
        self.assertEqual(body_json["data"]["name"], "全域甲")
        self.assertEqual(body_json["data"]["douyin_accounts"], [])

    def test_extra_field_is_422(self) -> None:
        """多传字段拒绝。"""
        client = http_client(FakeSession())
        payload = body().model_dump(mode="json")
        payload["ads_per_account"] = 2
        res = client.post(PREFIX, json=payload)
        self.assertEqual(res.status_code, 422)
        self.assertIn("ads_per_account", res.json()["message"])
