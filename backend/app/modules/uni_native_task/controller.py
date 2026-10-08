"""漫剧全域端原生投放任务 HTTP。只认登录态，每人只看自己的任务。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.uni_native_task.schema import DeletedItem, SubmitResult, TaskItem, TaskQuery, TaskWrite
from app.modules.uni_native_task.service import create_task, delete_task, get_task, list_tasks, update_task
from app.modules.uni_native_task.submit import submit_task

router = APIRouter(
    prefix="/api/v1/uni-native-tasks",
    tags=["uni-native-tasks"],
    dependencies=[Depends(require_token)],
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


def _user_id(principal: dict[str, Any]) -> int:
    """登录主体上的用户 id。"""
    return int(principal["id"])


@router.get("", response_model=Envelope[PageData[TaskItem]], summary="分页查询端原生投放任务")
async def get_tasks(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[TaskQuery, Query()],
) -> dict[str, Any]:
    """按创建日期和剧名列出当前投手未删除的任务。"""
    return success(await list_tasks(session, query, _user_id(principal)))


@router.get("/{task_id}", response_model=Envelope[TaskItem], summary="查询一条端原生投放任务")
async def get_one_task(task_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """取自己的一条未删除任务。"""
    return success(await get_task(session, task_id, _user_id(principal)))


@router.post("", response_model=Envelope[TaskItem], summary="新增端原生投放任务")
async def post_task(body: TaskWrite, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """本地保存。不上传素材，也不调用巨量。状态为已保存未提交。"""
    return success(await create_task(session, body, _user_id(principal)))


@router.put("/{task_id}", response_model=Envelope[TaskItem], summary="保存端原生投放任务")
async def put_task(
    task_id: int, body: TaskWrite, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """整表保存自己的任务。"""
    return success(await update_task(session, task_id, body, _user_id(principal)))


@router.delete("/{task_id}", response_model=Envelope[DeletedItem], summary="删除端原生投放任务")
async def remove_task(task_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """软删自己的任务。"""
    return success(await delete_task(session, task_id, _user_id(principal)))


@router.post("/{task_id}/submit", response_model=Envelope[SubmitResult], summary="确认提交端原生投放任务")
async def post_task_submit(task_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """按任务组项目和广告报文。状态保持已保存，不把素材标成传完。"""
    return success(await submit_task(session, task_id, _user_id(principal)))
