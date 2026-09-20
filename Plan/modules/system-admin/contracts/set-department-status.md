# 契约：set-department-status

业务id：system-admin
文档版本：1
方法：PATCH
路径：/api/v1/system-admin/departments/{id}/status
作用：部门启停。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | |
| enabled | body | boolean | 是 | |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | |
| enabled | boolean | 更新后 |

## 错误

无本接口特有。共用错误码见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 部门管理 | 启停 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
