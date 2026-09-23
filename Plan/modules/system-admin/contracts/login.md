# 契约：login

业务id：auth
文档版本：5
方法：POST
路径：/api/v1/auth/login
作用：密码登录。查 `users` 表（仅 `login_account`），签发 HS256 JWT；会话按 `jti` 写入 Redis。同一账号只保留最新一次登录，旧会话标为冲突。HTTP 路由在 core，验密走 `system_admin` 窄口。本阶段不支持手机号登录。

作者：调度者
状态：accepted
更新日期：2026-09-22

## 请求

无 Header Token。无 path/query。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| login_account | body | string | 是 | 登录账号，不是手机号 |
| password | body | string | 是 | |

## 响应

`data` 内字段。信封见 [说明.md](说明.md)。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| token | string | HS256 JWT。之后放 `Authorization: Bearer`。验签后按 `jti` 查 Redis 会话 |
| token_type | string | 固定 `bearer` |
| user | object | 当前登录用户摘要 |
| user.id | string | |
| user.nickname | string | |
| user.login_account | string | |
| user.tenant | string | |

JWT 身份 claims：`sub`（用户 id）、`login_account`、`nickname`、`tenant`、`jti`、`iat`、`exp`。授权缓存（如 `menu_ids`）只在 Redis，不进 JWT。同一账号再次登录成功后，只保留新 `jti`；旧 `jti` 的会话键删除，并写入 `adpilot:session-conflict:{jti}`，值为 `{"reason":"login_elsewhere"}`，TTL 等于被顶掉会话的剩余时间。之后用旧 Token 访问任意需登录接口：HTTP 401，`message` 为「账号已在其他地方登录」。停用/改密/删用户只删会话、不写冲突，仍是「未带或 Token 无效」。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 账号或密码不对 | 401 | `INVALID_CREDENTIALS` |
| 账号停用 | 403 | `ACCOUNT_DISABLED` |
| 字段校验失败 | 422 | 见说明.md 共用错误码 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 壳 | 登录提交 |

## 变更历史

新记录插在最上行。破坏性变更须先把本文快照到 `_history/<endpoint>-v<旧版本>.md`。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-22 | 5 | 否 | 同账号再次登录顶掉旧会话；冲突状态进 Redis。旧 Token 再访问为 401「账号已在其他地方登录」 | 姜英睿 |
| 2026-09-21 | 4 | 否 | 登录只认 `login_account`，不再用手机号命中用户 | 姜英睿 |
| 2026-09-21 | 3 | 否 | Token 改为 JWT；Redis 按 jti 存会话。HTTP 字段不变 | 调度者 |
| 2026-09-20 | 2 | 否 | 查库验密；Token 进 Redis。新建用户可登录 | 调度者 |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
