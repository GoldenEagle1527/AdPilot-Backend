# 契约：update-user

业务id：system-admin
文档版本：1
方法：PUT
路径：/api/v1/system-admin/users/{id}
作用：整集替换用户可改主档（不含账号、密码、启停、租户）。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | |
| nickname | body | string | 是 | |
| short_name | body | string | 否 | |
| phone | body | string | 否 | |
| department_id | body | string | 是 | |
| role_kind | body | string | 是 | `负责人` \| `成员` |
| remark | body | string | 否 | 最多 200 |

禁止改 `login_account`、`password`、`enabled`、`tenant`；请求体不要带这些字段。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| （整对象） | UserListItem | 见 [说明.md](说明.md) |

## 错误

无本接口特有错误。用户或部门不存在走共用 `404 NOT_FOUND`。共用码见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 用户管理 | 修改 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/update-user-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
