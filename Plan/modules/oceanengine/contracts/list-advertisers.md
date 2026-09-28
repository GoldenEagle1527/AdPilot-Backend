# 契约：list-advertisers

业务id：oceanengine
文档版本：2
方法：GET
路径：/api/v1/oceanengine/advertisers
作用：分页列出广告主。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单 `63` 或 `32` |
| page | query | int | 否 | 从 1，默认 1 |
| page_size | query | int | 否 | 默认 20，上限 100 |
| account_name | query | string | 否 | 模糊。同时匹配本地展示名与巨量账户名 |
| account_id | query | int | 否 | 广告主 id 精确。字段名保持，不另设 `advertiser_id` |
| pitcher_user_id | query | int | 否 | 投手用户 id。只有菜单 32 时忽略此参数 |
| organization_id | query | int | 否 | 组织的巨量账户 id，与响应 `organization_id` 相同 |

无请求体。

## 响应

分页体：`list` / `total` / `page` / `page_size`。成功只用 `success()`。已有字段名与类型保持。后三列为本版增加的可选列，旧调用方可忽略。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| account_id | int | 巨量广告主 id。种子 `1873916032590219` |
| account_name | string | 展示名。有本地改名时用本地名，否则用巨量账户名。种子「番茄漫剧测试户」 |
| valid_balance | float | 可用余额，单位元。必填 float，不用可空类型。尚未同步成功时为 `0`。种子 `100.5` |
| adv_company_name | string | 公司名。种子「番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2」 |
| organization_id | int | 所属组织的巨量账户 id。种子 `1872115109920903` |
| pitcher_nickname | string \| null | 投手昵称。未分配为 null |
| manager_name | string | 管家名，即所属授权组织名称 |
| sync_status | string | `active` 或 `missing`。页面显示有效 / 失效 |

列表不返回 `raw_payload`。`is_deleted=1` 的广告主不出现。取消投手分配后账户仍在列表里，`pitcher_nickname` 为空。`mock=true` 时行来自库内种子，不读进程内存。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 63 且无菜单 32 | 403 | |
| 其它校验失败 | 422 | |

本列表读库。未配 secret 不返回 503；有上次成功列则 200。

## 业务规则

- 有菜单 63：看全部未解绑广告主，含 `sync_status=missing`，不套部门数据权限。可与菜单 32 同时拥有，仍按 63。
- 只有菜单 32：服务端强制 `pitcher_user_id` 为当前用户，且只返回 `sync_status=active`。调用方传入别人的 `pitcher_user_id` 也忽略。看不到失效户，也不能靠本接口做分配、改名、解绑、导入。
- 巨量同步不再返回的广告主标 `missing`，不软删，已有投手保留。失效户若仍挂着投手，再分配仍 409，须先解绑（见分配契约）。

## 被谁调用

广告主账户页；只有菜单 32 的投手看自己的有效户。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 2 | 否 | 在现有字段上增加可选列 `pitcher_nickname`、`manager_name`、`sync_status`（`active`\|`missing`）。`valid_balance` 仍为必填 float。鉴权改为菜单 63 或 32。只有菜单 32 时列表强制本人且 `sync_status=active`；菜单 63 可见 `missing`。路径仍为 v1 | |
| 2026-09-23 | 1 | 否 | 初稿 | |

## 内部

余额与公司名的开放平台 path、以及从 `account_valid` 还是上游 `valid_balance` 取值，只写在 Gateway 映射里，结果落入 `valid_balance` 与 `adv_company_name`。映射可替换，响应键名与 `valid_balance` 的 float 类型不变。巨量错误不进入本响应。
