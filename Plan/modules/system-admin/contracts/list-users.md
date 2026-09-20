# 契约：list-users

业务id：system-admin
文档版本：1
方法：GET
路径：/api/v1/system-admin/users
作用：分页列出用户，可按部门树（含子树）与主档条件筛选。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| department_id | query | string | 否 | 所属部门过滤 |
| include_descendants | query | boolean | 否 | 默认 `true`。按树筛人时是否含该部门子孙；无 `department_id` 时忽略 |
| nickname | query | string | 否 | |
| login_account | query | string | 否 | |
| enabled | query | boolean | 否 | |
| page | query | integer | 否 | 从 1；缺省按全站分页约定 |
| page_size | query | integer | 否 | 默认 20、上限 100 |

无请求体。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | UserListItem[] | 见 [说明.md](说明.md) |
| total | integer | |
| page | integer | |
| page_size | integer | |

## 错误

无本接口特有错误。共用码见 [说明.md](说明.md)。

## 被谁调用

| 页面卡片 | 页面动作 |
| --- | --- |
| 用户管理 | 按部门树筛人 / 列表 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/list-users-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
