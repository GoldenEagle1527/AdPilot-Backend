"""端原生自动化投放执行记录 HTTP。要有端原生自动化投放菜单。

执行记录和机器人规则都没有投手或部门，有菜单的人看到全部记录和失败日志。
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.system_admin import require_menu
from app.modules.uni_native_auto_run.schema import FailureItem, FailureQuery, RunItem, RunQuery
from app.modules.uni_native_auto_run.service import get_one_run, list_failure_logs, list_runs

router = APIRouter(
    prefix="/api/v1/uni-native-auto-runs",
    tags=["uni-native-auto-runs"],
    dependencies=[Depends(require_menu("57"))],
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_menu("57"))]


@router.get("", response_model=Envelope[PageData[RunItem]], summary="分页查询端原生自动化投放记录")
async def get_runs(
    session: SessionDep,
    _principal: PrincipalDep,
    query: Annotated[RunQuery, Query()],
) -> dict[str, Any]:
    """按规则类型、规则、剧名列出未删除的执行记录。"""
    return success(await list_runs(session, query))


@router.get(
    "/{run_id}/failure-logs",
    response_model=Envelope[PageData[FailureItem]],
    summary="分页查询一条执行记录的失败日志",
)
async def get_failure_logs(
    run_id: int,
    session: SessionDep,
    _principal: PrincipalDep,
    query: Annotated[FailureQuery, Query()],
) -> dict[str, Any]:
    """列出这一次执行失败的短剧和原因。"""
    return success(await list_failure_logs(session, run_id, query))


@router.get("/{run_id}", response_model=Envelope[RunItem], summary="查询一条端原生自动化投放记录")
async def get_run(run_id: int, session: SessionDep, _principal: PrincipalDep) -> dict[str, Any]:
    """取一条未删除的执行记录。"""
    return success(await get_one_run(session, run_id))
