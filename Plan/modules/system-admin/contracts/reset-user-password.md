# 契约：reset-user-password

业务id：system-admin
文档版本：3
方法：POST
路径：/api/v1/system-admin/users/{id}/password-reset
作用：管理员直接写入新密码（不发短信）。两次输入必须一致。成功后踢掉该用户全部会话。

作者：调度者
状态：accepted
更新日期：2026-09-21

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | path | string | 是 | 用户 id |
| password | body | string | 是 | 新密码 |
| password_confirm | body | string | 是 | 须与 password 相同 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| reset | boolean | 成功时为 `true` |

不回传明文密码。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 两次密码不一致 | 422 | `VALIDATION_ERROR` |

用户不存在 404。共用码见 [说明.md](说明.md)。

## 被谁调用

用户管理 · 重置密码

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-21 | 3 | 否 | 成功后删 Redis `jti`，未过期 JWT 也 401 | 姜英睿 |
| 2026-09-20 | 2 | 是 | 改为请求体写新密码，不再套字典默认密码、不再回传明文。快照 [_history/reset-user-password-v1.md](_history/reset-user-password-v1.md) | 调度者 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
