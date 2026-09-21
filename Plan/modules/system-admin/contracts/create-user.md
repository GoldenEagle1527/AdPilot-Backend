# 契约：create-user

业务id：system-admin
文档版本：2
方法：POST
路径：/api/v1/system-admin/users
作用：新增用户。

作者：调度者
状态：accepted
更新日期：2026-09-21

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| nickname | body | string | 是 | |
| login_account | body | string | 是 | 用户名或手机号；创建后不可改 |
| short_name | body | string | 否 | |
| password | body | string | 否 | 空或不传 → 使用库内字典默认密码（Q-PERM-5），不写死 `135` |
| phone | body | string | 否 | |
| department_id | body | string | 是 | |
| remark | body | string | 否 | 最多 200 |
| tenant | body | string | 否 | 默认当前登录用户的 `tenant` |

不要传 `role_kind`（新增窗无此字段）：服务端默认 `成员`。`enabled` 默认 `true`。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| （整对象） | UserListItem | 见 [说明.md](说明.md) |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| login_account 已存在 | 409 | `CONFLICT` |
| 部门不存在 | 404 | `NOT_FOUND` |
| 目标部门已停用 | 409 | `DEPARTMENT_DISABLED` |

共用码见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 用户管理 | 新增 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/create-user-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-21 | 2 | 否 | 不能往停用部门加人 | 姜英睿 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
