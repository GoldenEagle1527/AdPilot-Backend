"""漫剧全域端原生投放任务 HTTP。要有端原生投放任务菜单。列表按部门数据范围，改删提交仍只动自己的。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.envelope import ApiError, Envelope, success
from app.core.pagination import PageData
from app.modules.system_admin import require_menu
from app.modules.system_admin.domain.scope import resolve_data_scope
from app.modules.uni_native_task.schema import DeletedItem, SubmitResult, TaskItem, TaskQuery, TaskWrite
from app.modules.uni_native_task.service import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    mark_failed_if_saved,
    update_task,
)
from app.modules.uni_native_task.submit import submit_task

router = APIRouter(
    prefix="/api/v1/uni-native-tasks",
    tags=["uni-native-tasks"],
    dependencies=[Depends(require_menu("56"))],
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_menu("56"))]


def _user_id(principal: dict[str, Any]) -> int:
    """登录主体上的用户 id。"""
    return int(principal["id"])


async def _submit_saved(session: AsyncSession, task_id: int, user_id: int) -> dict[str, Any]:
    """落库之后提交一次。提交在改状态前失败时把 saved 标成 failed，再把原来的错误抛出去。"""
    try:
        await submit_task(session, task_id, user_id)
    except ApiError as exc:
        await mark_failed_if_saved(session, task_id, user_id, exc.message)
        raise
    return await get_task(session, task_id, user_id)


@router.get("", response_model=Envelope[PageData[TaskItem]], summary="分页查询端原生投放任务")
async def get_tasks(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[TaskQuery, Query()],
) -> dict[str, Any]:
    """仅本人看自己的任务；勾了部门则看这些部门里投手的。"""
    scope = await resolve_data_scope(session, principal)
    return success(await list_tasks(session, query, _user_id(principal), scope))


@router.get("/{task_id}", response_model=Envelope[TaskItem], summary="查询一条端原生投放任务")
async def get_one_task(task_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """取数据范围内的一条未删除任务。改删提交仍只动自己的。"""
    scope = await resolve_data_scope(session, principal)
    return success(await get_task(session, task_id, _user_id(principal), scope))


@router.post("", response_model=Envelope[TaskItem], summary="新增端原生投放任务")
async def post_task(body: TaskWrite, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """先落库，再在同一次请求里创建项目和广告。成功时状态为 done。"""
    user_id = _user_id(principal)
    saved = await create_task(session, body, user_id, require_template_assignment=True)
    return success(await _submit_saved(session, int(saved["id"]), user_id))


@router.put("/{task_id}", response_model=Envelope[TaskItem], summary="保存端原生投放任务")
async def put_task(
    task_id: int, body: TaskWrite, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """只改还停在 saved 的任务，改完再创建项目和广告。已经创建过的返回 409。"""
    user_id = _user_id(principal)
    await update_task(session, task_id, body, user_id, require_template_assignment=True)
    return success(await _submit_saved(session, task_id, user_id))


@router.delete("/{task_id}", response_model=Envelope[DeletedItem], summary="删除端原生投放任务")
async def remove_task(task_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """软删自己的任务。"""
    return success(await delete_task(session, task_id, _user_id(principal)))


@router.post("/{task_id}/submit", response_model=Envelope[SubmitResult], summary="确认提交端原生投放任务")
async def post_task_submit(task_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """只提交仍是 saved 的任务。已经在跑、完成或失败的返回 409，不再建一套项目。"""
    return success(await submit_task(session, task_id, _user_id(principal)))
