# 契约：update-role

业务id：system-admin
文档版本：2
方法：PUT
路径：/api/v1/system-admin/roles/{id}
作用：改角色名称与备注；不改 enabled。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 角色 id |
| name | body | string | 是 | |
| remark | body | string \| null | 否 | 可 null，清空备注 |

不要传 `enabled`，本接口不改启停。

## 响应

`data` 为更新后的角色对象（字段同 list-roles 的 RoleListItem，含 `updated_by` 与已分配名单）。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | |
| name | string | |
| remark | string \| null | |
| enabled | boolean | 保持原值 |
| created_at | string | |
| updated_at | string | |
| assigned_user_count | integer | 关系计数，不是 Role 表字段 |
| assigned_department_count | integer | 关系计数，不是 Role 表字段 |
| assigned_users | array | |
| assigned_departments | array | |
| updated_by | string \| null | 本次操作者登录账号 |

## 错误

无特有。共用错误码见 [说明.md](说明.md)。角色不存在走 404 `NOT_FOUND`。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 角色管理 | 修改 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 2 | 否 | 响应对齐 RoleListItem | 调度者 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
