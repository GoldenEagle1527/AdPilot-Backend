# 契约：oauth-authorize

业务id：oceanengine
文档版本：2
方法：GET
路径：/api/v1/oceanengine/oauth/authorize
作用：按渠道返回巨量授权链接。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `64` |
| channel | query | string | 是 | 只允许 `third` 或 `self`，其它 422 |

不新增其它必填 query。`oe_app_id` 不是本接口参数。无请求体。本接口不请求开放平台。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| authorize_url | string | 授权页地址。键名保持 |

种子各渠道一行时：

- `third`：`https://open.oceanengine.com/audit/oauth.html?app_id=1870857293665690&state={%22agentId%22:%221%22}&material_auth=1&rid=tg29ccnkpzm`
- `self`：`https://open.oceanengine.com/audit/oauth.html?app_id=1870855836080240&state={%22agentId%22:%221%22,%22agency%22:true}&material_auth=1&rid=c9lb3o12qhm`

同一 `channel` 有多套有效应用时，取该渠道 `status=active` 且本库 id 最小的一套拼 `authorize_url`。链接来自库内应用行，不来自进程内存。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 64 | 403 | 只有菜单 32、没有 64 的投手调用本接口为 403 |
| `channel` 不是 `third` 或 `self` | 422 | |
| 该渠道没有有效应用 | 404 | |

## 业务规则

- 只有菜单 32 的投手不能换授权链接。广告主列表仍可用。
- 授权页本身不打开放平台业务接口。

## 被谁调用

授权组织页的「去授权」。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 2 | 是 | 鉴权由仅菜单 32 改为菜单 64。只有菜单 32 的投手再调授权链接会 403。query 仍只有必填 `channel=third\|self`，响应键仍为 `authorize_url`。路径仍为 v1。快照 [_history/oauth-authorize-v1.md](_history/oauth-authorize-v1.md) | |
| 2026-09-23 | 1 | 否 | 初稿 | |

## 内部

拼进 `authorize_url` 的开放平台入口、state 里的应用行 id 与 HMAC 方式可替换。响应只有 `authorize_url` 这一个键。
