# 契约：list-organizations

业务id：oceanengine
文档版本：2
方法：GET
路径：/api/v1/oceanengine/organizations
作用：列出授权组织，不分页。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `64` |

无 query、无请求体。

## 响应

成功：`success({"items": [...]})`。已有键名保持。下列后四列为兼容新增，旧调用方可忽略。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| advertiser_id | int | 巨量账户 id。种子 `1872115109920903` |
| advertiser_name | string | 组织名称。种子「深圳发行中心」 |
| account_role | string | 角色，原样保存。种子 `CUSTOMER_ADMIN` |
| ocean_version | string | 巨量版本。种子「升级版组织」 |
| id | int | 本库主键 |
| channel | string | 认证方式：`self` 自研，`third` 三方。由该组织所属应用的 channel 映射 |
| status | string | `active` 有效，`invalid` 失效。授权收回或令牌失效时标失效，不物理删除 |
| token_valid | bool | 当前令牌是否有效。刷新失败时为 false，名称与角色仍为上次成功值 |

`mock=true` 时 `items` 来自库内种子，不读进程内存。列表不返回令牌、secret、`raw_payload`。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 64 | 403 | 只有菜单 32、没有 64 的投手调用本接口为 403 |
| 其它校验失败 | 422 | |

列表读库。未配 secret 不对本接口返回 503；上次同步成功的列照常 200。

## 业务规则

- 页面不能通过本接口新增组织。
- 拥有菜单 64 的人看全部组织，不套部门数据权限。
- 只有菜单 32 的投手不能调本接口。广告主列表仍走菜单 63 或 32。

## 被谁调用

授权组织页。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 2 | 是 | 鉴权由仅菜单 32 改为菜单 64。只有菜单 32 的投手再调组织列表会 403。响应已有字段名保持，并增加可选列 `id`、`channel`、`status`、`token_valid`。列表改为读库，未配 secret 不再 503。路径仍为 `/api/v1/oceanengine/organizations`。快照 [_history/list-organizations-v1.md](_history/list-organizations-v1.md) | |
| 2026-09-23 | 1 | 否 | 初稿 | |

## 内部

开放平台拉组织的 path、query 名和嵌套字段只在 Gateway 映射里。映射可替换，本接口响应键不变。巨量 `code != 0` 或超时写入同步错误，不变成新的响应字段。原文进 `raw_payload`，列表不返回。
