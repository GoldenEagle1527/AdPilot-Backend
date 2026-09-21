# 契约：set-user-status

业务id：system-admin
文档版本：2
方法：PATCH
路径：/api/v1/system-admin/users/{id}/status
作用：启停用户。停用成功后踢掉该用户全部会话。

作者：调度者
状态：accepted
更新日期：2026-09-21

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

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 停用当前登录账号 | 409 | `CANNOT_DISABLE_SELF` |
| 完成后无人再持有用户管理菜单 | 409 | `LAST_ADMIN_REQUIRED` |

共用码见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 用户管理 | 启停（列表开关；仍登记此契约） |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/set-user-status-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-21 | 2 | 否 | 停用踢会话；禁止自停用；保留最后一名用户管理员 | 姜英睿 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
