"""端原生自动化投放执行记录：只列出，写入留给执行器。"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError, register_exception_handlers
from app.core.times import BEIJING
from app.modules.uni_native_auto_run.controller import router
from app.modules.uni_native_auto_run.model import UniNativeAutoRun, UniNativeAutoRunFailure
from app.modules.uni_native_auto_run.schema import FailureQuery, RunQuery
from app.modules.uni_native_auto_run.service import (
    RunFailure,
    get_one_run,
    list_failure_logs,
    list_runs,
    record_run,
    run_filters,
)

EXECUTED = datetime(2026, 9, 30, 9, 15, tzinfo=BEIJING)
CREATED = datetime(2026, 9, 30, 9, 16, tzinfo=BEIJING)
PREFIX = "/api/v1/uni-native-auto-runs"
MIGRATION = Path(__file__).resolve().parents[3] / "alembic" / "versions" / "20260930_04_uni_native_auto_run.py"
ROOT = Path(__file__).resolve().parents[3]


class FakeResult:
    """假 execute 结果。"""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one(self) -> Any:
        """返回唯一一个值。分页总数用。"""
        return self._rows[0]

    def scalar_one_or_none(self) -> Any:
        """返回首行，没有则 None。"""
        return self._rows[0] if self._rows else None

    def scalars(self) -> FakeResult:
        """让 scalars().all() 走同一份行。"""
        return self

    def all(self) -> list[Any]:
        """返回全部预置行。"""
        return self._rows


class FakeSession:
    """假会话。execute 按次序吐预置结果。"""

    def __init__(self, results: list[list[Any]] | None = None) -> None:
        self.results = list(results or [])
        self.statements: list[Any] = []
        self.added: list[Any] = []
        self.commits = 0
        self._next_id = 40

    async def execute(self, statement: Any) -> FakeResult:
        """不看 SQL，按调用次序返回下一份预置结果。"""
        self.statements.append(statement)
        rows = self.results.pop(0) if self.results else []
        return FakeResult(rows)

    def add(self, row: Any) -> None:
        """记下待插入行。"""
        self.added.append(row)

    async def flush(self) -> None:
        """给还没有 id 的行补 id。"""
        for row in self.added:
            if getattr(row, "id", None) is None:
                row.id = self._next_id
                self._next_id += 1

    async def commit(self) -> None:
        """记一次提交。写入函数不该走到这里。"""
        self.commits += 1


def make_run(**kwargs: Any) -> UniNativeAutoRun:
    """造一条执行记录。"""
    row = UniNativeAutoRun(
        rule_id=kwargs.get("rule_id", 12),
        rule_name=kwargs.get("rule_name", "早班推广"),
        rule_type=kwargs.get("rule_type", "promotion_link"),
        executed_at=kwargs.get("executed_at", EXECUTED),
        template_name=kwargs.get("template_name", "全域甲"),
        status=kwargs.get("status", "partial"),
        series_names=kwargs.get("series_names", ["甲壳虫", "乙剧"]),
    )
    row.id = kwargs.get("id", 40)
    row.is_deleted = 0
    row.created_date = CREATED
    row.updated_date = CREATED
    return row


def make_failure(**kwargs: Any) -> UniNativeAutoRunFailure:
    """造一条失败日志。"""
    row = UniNativeAutoRunFailure(
        run_id=kwargs.get("run_id", 40),
        series_name=kwargs.get("series_name", "甲壳虫"),
        reason=kwargs.get("reason", "没有上传素材"),
    )
    row.id = kwargs.get("id", 70)
    row.is_deleted = 0
    row.created_date = CREATED
    row.updated_date = CREATED
    return row


def http_client(session: FakeSession, *, login: bool = True) -> TestClient:
    """挂上本模块路由。"""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    if login:
        app.dependency_overrides[require_token] = lambda: {
            "id": "3",
            "nickname": "投手",
            "login_account": "pitcher",
            "tenant": "agent",
        }
    return TestClient(app)


def _sql(items: list[Any]) -> str:
    """按 PostgreSQL 把过滤条件编成可读 SQL。"""
    dialect = postgresql.dialect()
    return " AND ".join(
        str(item.compile(dialect=dialect, compile_kwargs={"literal_binds": True})) for item in items
    )


class QueryTests(unittest.TestCase):
    def test_rule_type_only_accepts_the_two_robot_kinds(self) -> None:
        """规则类型只有按推广链接和按剧条件。多传字段 422。"""
        self.assertEqual(RunQuery(rule_type="drama_condition").rule_type, "drama_condition")
        with self.assertRaises(ValidationError):
            RunQuery(rule_type="drama")
        with self.assertRaises(ValidationError):
            RunQuery(extra="no")

    def test_filters_match_type_rule_and_series(self) -> None:
        """类型精确，规则 id 精确，规则名和剧名模糊，并且只看未删除。"""
        sql = _sql(
            run_filters(
                RunQuery(rule_type="promotion_link", rule_id=12, rule_name="早班%", series_name="甲_")
            )
        )
        self.assertIn("uni_native_auto_run.is_deleted = 0", sql)
        self.assertIn("uni_native_auto_run.rule_type = 'promotion_link'", sql)
        self.assertIn("uni_native_auto_run.rule_id = 12", sql)
        self.assertIn("ILIKE", sql)
        self.assertIn("unnest", sql)
        self.assertIn("ESCAPE", sql)
        self.assertIn("%早班\\\\%", sql)
        self.assertIn("%甲\\\\_%", sql)

    def test_blank_names_do_not_filter(self) -> None:
        """空白的名称当没传。"""
        sql = _sql(run_filters(RunQuery(rule_name="  ", series_name="")))
        self.assertNotIn("ILIKE", sql)
        self.assertIn("is_deleted = 0", sql)

    def test_migration_revises_native_task_and_inserts_nothing(self) -> None:
        """迁移接在端原生投放任务之后。只建表，不灌执行记录。"""
        text = MIGRATION.read_text(encoding="utf-8")
        self.assertIn('revision: str = "20260930_04"', text)
        self.assertIn('down_revision: Union[str, None] = "20260930_03"', text)
        self.assertIn('["rule_id"], ["uni_robot_rule.id"]', text)
        self.assertIn("uni_native_auto_run_failure", text)
        self.assertIn("is_deleted", text)
        self.assertNotIn("INSERT", text)
        self.assertNotIn("op.bulk_insert", text)


class RecordTests(unittest.TestCase):
    def test_record_run_keeps_the_snapshot_and_failures(self) -> None:
        """执行器写入快照和失败日志。函数自己不提交。"""
        session = FakeSession()
        run = asyncio.run(
            record_run(
                session,
                rule_id=12,
                rule_name=" 早班推广 ",
                rule_type="drama_condition",
                executed_at=EXECUTED,
                template_name="全域甲",
                status="failed",
                series_names=["甲壳虫", " 甲壳虫 ", "乙剧"],
                failures=[RunFailure(series_name=" 甲壳虫 ", reason=" 没有上传素材 ")],
            )
        )
        self.assertEqual(session.commits, 0)
        self.assertEqual(run.rule_id, 12)
        self.assertEqual(run.rule_name, "早班推广")
        self.assertEqual(run.rule_type, "drama_condition")
        self.assertEqual(run.template_name, "全域甲")
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.series_names, ["甲壳虫", "乙剧"])
        failure = session.added[1]
        self.assertIsInstance(failure, UniNativeAutoRunFailure)
        self.assertEqual(failure.run_id, run.id)
        self.assertEqual(failure.series_name, "甲壳虫")
        self.assertEqual(failure.reason, "没有上传素材")

    def test_record_run_rejects_bad_input(self) -> None:
        """类型、状态、空名称和没时区的时间都不写。"""
        session = FakeSession()
        with self.assertRaises(ValueError):
            asyncio.run(
                record_run(
                    session,
                    rule_id=12,
                    rule_name="早班",
                    rule_type="drama",
                    executed_at=EXECUTED,
                    template_name="全域甲",
                    status="failed",
                    series_names=[],
                )
            )
        self.assertEqual(session.added, [])
        with self.assertRaises(ValueError):
            asyncio.run(
                record_run(
                    session,
                    rule_id=12,
                    rule_name=" ",
                    rule_type="promotion_link",
                    executed_at=datetime(2026, 9, 30, 9, 15),
                    template_name="全域甲",
                    status="done",
                    series_names=[],
                )
            )


class ReadTests(unittest.TestCase):
    def test_list_returns_the_page(self) -> None:
        """列表带分页字段。空库是空 list。"""
        session = FakeSession([[1], [make_run()]])
        data = asyncio.run(list_runs(session, RunQuery(series_name="甲")))
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["list"][0]["rule_id"], "12")
        self.assertEqual(data["list"][0]["series_names"], ["甲壳虫", "乙剧"])
        self.assertEqual(data["list"][0]["status"], "partial")
        self.assertTrue(data["list"][0]["executed_at"].endswith("+08:00"))
        empty = asyncio.run(list_runs(FakeSession([[0], []]), RunQuery()))
        self.assertEqual(empty["list"], [])
        self.assertEqual(empty["total"], 0)

    def test_get_missing_run_is_not_found(self) -> None:
        """没有这条记录就是 404。"""
        with self.assertRaises(ApiError) as caught:
            asyncio.run(get_one_run(FakeSession([[]]), 40))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(caught.exception.message, "执行记录不存在")

    def test_failure_logs_follow_the_run(self) -> None:
        """失败日志挂在这一次执行上。记录不存在则 404，有记录没有日志则空页。"""
        session = FakeSession([[make_run()], [1], [make_failure()]])
        data = asyncio.run(list_failure_logs(session, 40, FailureQuery()))
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["list"][0]["series_name"], "甲壳虫")
        self.assertEqual(data["list"][0]["reason"], "没有上传素材")
        self.assertNotIn("updated_at", data["list"][0])
        empty = asyncio.run(list_failure_logs(FakeSession([[make_run()], [0], []]), 40, FailureQuery()))
        self.assertEqual(empty["list"], [])
        with self.assertRaises(ApiError) as caught:
            asyncio.run(list_failure_logs(FakeSession([[]]), 40, FailureQuery()))
        self.assertEqual(caught.exception.status_code, 404)


class HttpTests(unittest.TestCase):
    def test_login_is_required(self) -> None:
        """未登录不能看执行记录。"""
        res = http_client(FakeSession(), login=False).get(PREFIX)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["code"], 401)
        self.assertEqual(res.json()["message"], "未带或 Token 无效")

    def test_list_uses_the_page_envelope(self) -> None:
        """列表走统一信封。查询会进到 SQL，接口自己不插入。"""
        session = FakeSession([[1], [make_run()]])
        res = http_client(session).get(
            PREFIX,
            params={"rule_type": "promotion_link", "rule_id": 12, "rule_name": "早班", "series_name": "甲"},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "成功")
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual(body["data"]["page"], 1)
        self.assertEqual(body["data"]["page_size"], 20)
        self.assertEqual(body["data"]["list"][0]["template_name"], "全域甲")
        self.assertEqual(session.added, [])
        sql = str(session.statements[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("promotion_link", sql)
        self.assertIn("12", sql)

    def test_get_and_failure_logs(self) -> None:
        """详情和失败日志都是登录后的 GET。"""
        got = http_client(FakeSession([[make_run()]])).get(f"{PREFIX}/40")
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()["data"]["id"], "40")
        missing = http_client(FakeSession([[]])).get(f"{PREFIX}/40")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["message"], "执行记录不存在")
        logs = http_client(FakeSession([[make_run()], [1], [make_failure()]])).get(f"{PREFIX}/40/failure-logs")
        self.assertEqual(logs.status_code, 200)
        self.assertEqual(logs.json()["data"]["list"][0]["reason"], "没有上传素材")

    def test_there_is_no_create_route(self) -> None:
        """页面不能新增。POST 不是接口。"""
        res = http_client(FakeSession()).post(PREFIX, json={"rule_id": 12})
        self.assertEqual(res.status_code, 405)
        methods: set[str] = set()
        for route in router.routes:
            methods.update(getattr(route, "methods", set()))
        self.assertNotIn("POST", methods)
        self.assertNotIn("PUT", methods)
        self.assertNotIn("DELETE", methods)

    def test_startup_and_handlers_do_not_record_runs(self) -> None:
        """启动和 HTTP 不调用写入函数，也不在处理器里插行。"""
        controller = (ROOT / "app" / "modules" / "uni_native_auto_run" / "controller.py").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        lifespan = (ROOT / "app" / "modules" / "system_admin" / "domain" / "load_seed.py").read_text(encoding="utf-8")
        self.assertNotIn("record_run", controller)
        self.assertNotIn("record_run", main)
        self.assertNotIn("uni_native_auto_run", lifespan)
        self.assertNotIn("session.add", controller)


if __name__ == "__main__":
    unittest.main()
