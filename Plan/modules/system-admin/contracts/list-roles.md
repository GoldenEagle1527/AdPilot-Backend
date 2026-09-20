# 契约：list-roles

业务id：system-admin
文档版本：2
方法：GET
路径：/api/v1/system-admin/roles
作用：分页列出角色主数据，并带上已分配用户（登录账号）与已分配部门。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| name | query | string | 否 | 角色名模糊匹配 |
| enabled | query | boolean | 否 | 启停筛选 |
| page | query | integer | 否 | 默认 1 |
| page_size | query | integer | 否 | 默认 20 |

无请求体。

## 响应

`data` 为分页对象。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | RoleListItem[] | 当前页 |
| total | integer | 符合筛选的总条数 |
| page | integer | 当前页 |
| page_size | integer | 每页条数 |

**RoleListItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | |
| name | string | |
| remark | string \| null | 最多 200 |
| enabled | boolean | |
| created_at | string | |
| updated_at | string | |
| updated_by | string \| null | 最后一次改名称/备注/启停/菜单的登录账号 |
| assigned_user_count | integer | 等于 `assigned_users.length` |
| assigned_department_count | integer | 等于 `assigned_departments.length` |
| assigned_users | `{ id, login_account, nickname }[]` | 已挂该**用户角色**的未删除用户 |
| assigned_departments | RoleName[] | 已挂该角色的未删除部门 |

## 错误

无特有。共用错误码见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 角色管理 | 加载/筛选 |
| 部门管理 / 用户管理 | 分配弹窗若需角色目录可改调本接口；弹窗主数据仍用 list-department-roles / list-user-roles |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 2 | 否 | 增加 `updated_by`、已分配用户/部门名单 | 调度者 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
