# 契约：rename-advertisers

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/advertisers/rename
作用：批量改广告主的本地展示名。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `63`。只有菜单 32 为 403 |
| items | body | object[] | 是 | 至少 1 条 |
| items[].advertiser_id | body | int | 是 | 巨量广告主 id，与列表 `account_id` 相同 |
| items[].name | body | string | 是 | 新的本地展示名。列表的 `account_name` 优先显示它 |

## 响应

`data.list` 为改完后的行，不是分页。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| advertiser_id | int | |
| account_name | string | 新的本地展示名 |

每个户记一行改名审计（旧名、新名、操作人、时间），审计不在本响应里。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 63 | 403 | |
| 任一广告主不存在或已解绑，或 `name` 为空 | 422 | 整批不改 |

## 业务规则

先写本地展示名。列表通过已有字段 `account_name` 显示本地名，不新增响应键。

## 被谁调用

广告主账户页的改名。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |

## 内部

是否把本地名回写开放平台，只在 Gateway 映射里决定，且仅当该户所属应用是自研代理时尝试。失败只记同步错误，本地名保留，本接口仍按成功返回。三方应用只改本地名。开放平台 path 不是请求字段。映射可替换，响应键仍是 `advertiser_id` 与 `account_name`。
