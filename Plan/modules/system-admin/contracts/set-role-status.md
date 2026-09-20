# 契约：set-role-status

业务id：system-admin
文档版本：1
方法：PATCH
路径：/api/v1/system-admin/roles/{id}/status
作用：启停角色。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 角色 id |
| enabled | body | boolean | 是 | |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | |
| enabled | boolean | 写入后的值 |

## 错误

无特有。共用错误码见 [说明.md](说明.md)。角色不存在走 404 `NOT_FOUND`。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 角色管理 | 启停 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
