# 契约：assign-advertisers

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/advertisers/assign
作用：把若干广告主分给一个投手。已有投手则整批拒绝。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `63`。只有菜单 32 为 403 |
| advertiser_ids | body | int[] | 是 | 至少 1 个。巨量广告主 id，与列表 `account_id` 相同 |
| pitcher_user_id | body | int | 是 | 须为带投手标签、未删除且启用的用户 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| advertiser_ids | int[] | 本次写上投手的 id，与请求相同 |
| pitcher_user_id | int | |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 63（含只有菜单 32） | 403 | |
| 广告主不存在、已解绑，或投手不可用 | 422 | 整批不改 |
| 其中任一户已有投手 | 409 | `message`：`广告主已有投手，须先解绑`。整批不部分成功。`sync_status=missing` 且仍挂着投手时同样 409 |

## 业务规则

- 一个广告主同时只属于一个投手。未分配的投手为空，可以分配。
- 已有投手时必须先走解绑，再调用本接口。本接口不自动解开旧投手。
- 失效户（`missing`）不软删。上面若还挂着投手，再分配仍 409。
- Excel 的 `assign` 与本接口同一条拒绝规则。

## 被谁调用

广告主账户页的分配。拥有菜单 63 的运营管理员。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
