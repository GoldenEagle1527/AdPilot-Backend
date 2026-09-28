# 契约：oauth-callback

业务id：oceanengine
文档版本：2
方法：GET
路径：/api/v1/oceanengine/oauth/callback
作用：用授权码换票，并同步该应用下的组织与广告主。

作者：
状态：draft
更新日期：2026-09-23

## 请求

免登录白名单。不读 `Authorization`，不要求菜单 32 或 64。巨量浏览器直接打开本路径。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| auth_code | query | string | 是 | 空则 422 |
| state | query | string | 否 | 可空。非空时须通过 HMAC，否则 422 |

无请求体。不接受其它 query 作为业务字段。

## 响应

键名保持。成功 `data`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| access_token | string | `mock=true` 时为 `mock-access-token`，写入 `oe_token`，不写进程内存 |
| refresh_token | string | `mock=true` 时为 `mock-refresh-token` |

不返回 secret。不增加新的响应键。换票成功后立刻同步该应用的组织与广告主；同步结果不另起字段，组织与广告主列表仍用各自契约。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| `auth_code` 为空 | 422 | |
| `state` 非空但 HMAC 失败或对不上应用行 | 422 | |
| `mock=false` 且未配 secret | 503 | `巨量未配置` |

不因缺少菜单返回 403。只有菜单 32 的投手再调组织列表或授权链接会 403，那两个接口见各自契约；本回调不查菜单。

## 业务规则

- 本路径是账户管理里唯一免登录口。只认 `auth_code` 与 `state`。
- `state` 用来认出是哪一行应用。非空时用 `jwt_secret` 做 HMAC，防止伪造应用行 id。
- 令牌写入该应用的 `oe_token`，换票成功覆盖这一行。

## 被谁调用

巨量授权页回调。中台页面不带 Bearer 打开。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 2 | 是 | 鉴权由菜单 32 改为免登录白名单，只接受 `auth_code` 与 `state`。响应字段名仍为 `access_token`、`refresh_token`。组织列表与授权链接改为菜单 64：只有菜单 32 的投手再调那两个接口会 403。令牌改写入库。路径仍为 v1。快照 [_history/oauth-callback-v1.md](_history/oauth-callback-v1.md) | |
| 2026-09-23 | 1 | 否 | 初稿 | |

## 内部

换票所用开放平台 path 只在 Gateway 映射里，可替换。成功体键名不变。未配 secret 时对外仍是 503，文案 `巨量未配置`。巨量 `message` 不成为新的响应字段。
