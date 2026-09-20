# 契约：set-user-status

业务id：system-admin
文档版本：1
方法：PATCH
路径：/api/v1/system-admin/users/{id}/status
作用：启停用户。

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
| enabled | boolean | 写入后的值 |

## 错误

无本接口特有错误。共用码见 [说明.md](说明.md)。

## 被谁调用

| 页面卡片 | 页面动作 |
| --- | --- |
| 用户管理 | 启停（列表开关；若页面卡片未单独列，仍登记此契约） |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/set-user-status-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
