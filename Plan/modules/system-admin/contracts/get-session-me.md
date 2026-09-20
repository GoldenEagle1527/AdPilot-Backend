# 契约：get-session-me

业务id：system-admin
文档版本：1
方法：GET
路径：/api/v1/system-admin/session/me
作用：当前登录用户主档（公开能力 B）。

作者：调度者
状态：accepted
更新日期：2026-09-20

## 请求

无请求体。无 path/query。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>` |

## 响应

`data` 内字段。信封、id、enabled 见 [说明.md](说明.md)。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | |
| nickname | string | |
| login_account | string | |
| short_name | string \| null | |
| phone | string \| null | |
| enabled | boolean | |
| department_id | string | |
| department_name | string | |
| role_kind | string | `负责人` \| `成员` |
| tenant | string | |
| remark | string \| null | |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未带或 Token 无效 / 无对应菜单或组件 / 字段校验失败 | 401 / 403 / 422 | 见说明.md 共用错误码 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 壳 | 取当前用户 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
