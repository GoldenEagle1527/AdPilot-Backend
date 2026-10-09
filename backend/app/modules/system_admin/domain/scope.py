"""部门数据范围。业务列表用 owner_match 限制能看见谁的行。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.envelope import ApiError
from app.modules.system_admin.domain.access import user_by_login
from app.modules.system_admin.domain.models import User
from app.modules.system_admin.domain.org import effective_data_scope, user_not_deleted

_FORBIDDEN = "已登录但无对应菜单或组件"


@dataclass(frozen=True)
class DataScope:
    """当前用户的有效数据范围。self_only 时 department_ids 为空。"""

    user_id: int
    self_only: bool
    department_ids: tuple[int, ...]


def owner_match(column: Any, user_id: int, scope: DataScope | None = None) -> ColumnElement[bool]:
    """仅本人，或勾选部门里未删除用户的行。scope 为空或仅本人时等于本人。"""
    if scope is not None and not scope.self_only and scope.department_ids:
        return column.in_(
            select(User.id).where(
                User.department_id.in_(scope.department_ids),
                user_not_deleted(),
            )
        )
    return column == user_id


def _from_cache(user_id: int, cached: dict[str, Any]) -> DataScope:
    self_only = bool(cached.get("self_only", True))
    raw_ids = cached.get("department_ids") or []
    department_ids = tuple(int(item) for item in raw_ids)
    if self_only or not department_ids:
        return DataScope(user_id, True, ())
    return DataScope(user_id, False, department_ids)


async def resolve_data_scope(session: AsyncSession, principal: dict[str, Any]) -> DataScope:
    """读当前用户的数据范围。主体上已带 data_scope 时不再查库。"""
    cached = principal.get("data_scope")
    if isinstance(cached, dict):
        return _from_cache(int(principal["id"]), cached)
    user = await user_by_login(session, str(principal["login_account"]))
    if user is None or not user.enabled:
        raise ApiError(403, _FORBIDDEN)
    self_only, department_ids = await effective_data_scope(session, user)
    if self_only or not department_ids:
        return DataScope(int(user.id), True, ())
    return DataScope(int(user.id), False, tuple(int(item) for item in department_ids))
