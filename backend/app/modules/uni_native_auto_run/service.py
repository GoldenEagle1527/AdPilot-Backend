"""端原生自动化投放执行记录。只查询，并给以后的执行器留一个写入函数。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import BEIJING, beijing_iso
from app.modules.uni_native_auto_run.crud import get_run, page_failures, page_runs
from app.modules.uni_native_auto_run.model import (
    RunRuleType,
    RunStatus,
    UniNativeAutoRun,
    UniNativeAutoRunFailure,
)
from app.modules.uni_native_auto_run.schema import FailureQuery, RunQuery

_RULE_NAME_LIMIT = 128
_TEMPLATE_NAME_LIMIT = 128
_SERIES_NAME_LIMIT = 512
_REASON_LIMIT = 2000


@dataclass(frozen=True, slots=True)
class RunFailure:
    """执行器带来的一条失败。不是 HTTP 入参。"""

    series_name: str
    reason: str


def _like(raw: str) -> str:
    """ILIKE 片段。% 和 _ 按字面量匹配。"""
    escaped = raw.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _text(value: str, label: str, limit: int) -> str:
    """去掉首尾空白。空的和超长的留给调用方处理，不写入。"""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label}不能为空")
    if len(cleaned) > limit:
        raise ValueError(f"{label}过长")
    return cleaned


def _series_names(names: list[str]) -> list[str]:
    """短剧名称去空白、去重，保留第一次出现的顺序。"""
    cleaned: list[str] = []
    seen: set[str] = set()
    for name in names:
        text = _text(name, "短剧名称", _SERIES_NAME_LIMIT)
        if text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned


def _executed_at(value: datetime) -> datetime:
    """执行时间要带时区，存成北京时间。"""
    if value.tzinfo is None:
        raise ValueError("执行时间要带时区")
    return value.astimezone(BEIJING)


def series_name_match(pattern: str) -> ColumnElement[bool]:
    """短剧名称模糊：命中 series_names 里的任意一个。"""
    series_name = func.unnest(UniNativeAutoRun.series_names).column_valued("series_name")
    return exists(select(literal(1)).where(series_name.ilike(pattern, escape="\\")))


def run_filters(query: RunQuery) -> list[ColumnElement[bool]]:
    """拼列表过滤。空白的名称当没传。"""
    filters: list[ColumnElement[bool]] = [UniNativeAutoRun.is_deleted == 0]
    if query.rule_type is not None:
        filters.append(UniNativeAutoRun.rule_type == query.rule_type)
    if query.rule_id is not None:
        filters.append(UniNativeAutoRun.rule_id == query.rule_id)
    rule_name = (query.rule_name or "").strip()
    if rule_name:
        filters.append(UniNativeAutoRun.rule_name.ilike(_like(rule_name), escape="\\"))
    series_name = (query.series_name or "").strip()
    if series_name:
        filters.append(series_name_match(_like(series_name)))
    return filters


def run_item(row: UniNativeAutoRun) -> dict[str, Any]:
    """把执行记录收成出参。主键是字符串。"""
    return {
        "id": str(row.id),
        "rule_id": str(row.rule_id),
        "rule_name": row.rule_name,
        "rule_type": row.rule_type,
        "executed_at": beijing_iso(row.executed_at),
        "template_name": row.template_name,
        "status": row.status,
        "series_names": list(row.series_names or []),
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def failure_item(row: UniNativeAutoRunFailure) -> dict[str, Any]:
    """把失败日志收成出参。"""
    return {
        "id": str(row.id),
        "series_name": row.series_name,
        "reason": row.reason,
        "created_at": beijing_iso(row.created_date),
    }


async def record_run(
    session: AsyncSession,
    *,
    rule_id: int,
    rule_name: str,
    rule_type: str,
    executed_at: datetime,
    template_name: str,
    status: str,
    series_names: list[str],
    failures: list[RunFailure] | None = None,
) -> UniNativeAutoRun:
    """写入一条执行记录和它的失败日志。

    给以后的漫剧机器人执行器调用。只 flush，由调用方提交。
    启动过程和 HTTP 接口不能调用。
    """
    if rule_id < 1:
        raise ValueError("规则 id 无效")
    if rule_type not in {item.value for item in RunRuleType}:
        raise ValueError("规则类型无效")
    if status not in {item.value for item in RunStatus}:
        raise ValueError("执行状态无效")
    run = UniNativeAutoRun(
        rule_id=rule_id,
        rule_name=_text(rule_name, "规则名称", _RULE_NAME_LIMIT),
        rule_type=rule_type,
        executed_at=_executed_at(executed_at),
        template_name=_text(template_name, "模板名称", _TEMPLATE_NAME_LIMIT),
        status=status,
        series_names=_series_names(series_names),
    )
    session.add(run)
    await session.flush()
    for failure in failures or []:
        session.add(
            UniNativeAutoRunFailure(
                run_id=run.id,
                series_name=_text(failure.series_name, "短剧名称", _SERIES_NAME_LIMIT),
                reason=_text(failure.reason, "失败原因", _REASON_LIMIT),
            )
        )
    if failures:
        await session.flush()
    return run


async def list_runs(session: AsyncSession, query: RunQuery) -> dict[str, Any]:
    """分页列出未删除的执行记录。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_runs(
        session, run_filters(query), offset=params.offset, limit=params.page_size
    )
    return page_data([run_item(row) for row in rows], total, params)


async def get_one_run(session: AsyncSession, run_id: int) -> dict[str, Any]:
    """取一条未删除的执行记录。"""
    row = await get_run(session, run_id)
    if row is None:
        raise ApiError(404, "执行记录不存在")
    return run_item(row)


async def list_failure_logs(session: AsyncSession, run_id: int, query: FailureQuery) -> dict[str, Any]:
    """分页列出一条执行记录的失败日志。记录不存在则 404。"""
    if await get_run(session, run_id) is None:
        raise ApiError(404, "执行记录不存在")
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_failures(session, run_id, offset=params.offset, limit=params.page_size)
    return page_data([failure_item(row) for row in rows], total, params)
