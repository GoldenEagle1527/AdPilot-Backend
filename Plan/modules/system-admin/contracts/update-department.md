# 契约：update-department

业务id：system-admin
文档版本：1
方法：PUT
路径：/api/v1/system-admin/departments/{id}
作用：改名、改父、排序。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | |
| name | body | string | 是 | |
| parent_id | body | string \| null | 是 | `null` = 挂到根 |
| sort | body | integer | 是 | |

禁止改 `tenant`、`enabled`（启停走 `set-department-status`）。不要传这两项。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| （整个 data） | DepartmentNode | 更新后的本节点 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 成环 | 409 | `CYCLE_NOT_ALLOWED`。`parent_id` 指向自身或子孙 |
| 目标父不存在 | 404 | `parent_id` 非 null 但找不到该部门 |

其余见 [说明.md](说明.md) 共用错误码。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 部门管理 | 修改 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
