---
name: adpilot-add-endpoint
description: Adds a backend HTTP endpoint in an existing business package using current AdPilot envelope, Token, and contract files. Use when adding an API route, new router, or implementing a Plan contract.
---

# 新建接口

在**已有业务包**里加路由。登录/health 已在 `core`，不要再往 `core` 堆业务路径。

## 步骤

1. 确认包存在（现有只有 `system_admin`）。没有契约先写：
   - 复制 `Plan/contracts/接口模板.md` → `Plan/modules/<id>/contracts/<endpoint>.md`
   - `contracts/最新表.md` 加一行；`后端.md` 加一行
2. Router 放 `app/modules/<pkg>/api/<resource>.py`（按资源拆文件，对齐已有 `users.py` / `departments.py`）。不要为每个 verb 新建包。
3. 请求体用 `schemas/` 里的 Pydantic；`extra="forbid"`（现有部门/角色已这样）。
4. 处理函数：

```python
from app.core.envelope import ApiError, success
from app.modules.system_admin.deps import SessionDep, current_principal

@router.get("/things")
async def list_things(session: SessionDep, _user: dict = Depends(current_principal)):
    return success({"items": [...]})
```

5. 对外错误用 `ApiError(status, "CODE", "一句话")`。共用码：`UNAUTHORIZED` `FORBIDDEN` `VALIDATION_ERROR` `NOT_FOUND` `INTERNAL_ERROR`。业务特有码写在该契约「错误」表，不要在 `core` 枚举业务名词。
6. **补 `response_model` 或把 `data` 做成 Pydantic 再 `success(...)`**，让 `/openapi.json` 看得到字段。现有大量 `-> dict` 是债，新接口不要学。
7. 列表走 `app.core.pagination.page_params` / `page_data`。树返回 `{ items }`，不分页。
8. 时间用 UTC `Z`（包内已有 `iso8601_z` / `iso_z`，不要再发明格式）。启停字段名 `enabled`。
9. `system_admin` 的 `__init__.py` 已集中 `include_router`；新文件要挂上去。
10. 做完发对接短文（见 rule `http-contract`）。不要贴 OpenAPI JSON。

## 现状注意

- 登录仍是 `core/auth.py` mock（`admin` / `disabled`），与 `users` 表未对齐。新接口不要假设 Token 里的 `id` 一定能在 `users` 查到；session 查询是按 `login_account` 对的。
- 系统管理 CRUD 已挂 `require_menu`。新业务包只许 `from app.modules.system_admin import require_menu`。本地 mock：`admin/admin123` 有系统管理菜单；`pitcher/pitcher123` 没有。
