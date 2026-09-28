# 契约：create-douyin

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/douyin
作用：录入抖音号。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。不接收投手列表。投手分配走 `/douyin/{id}/assign`。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `66` |
| aweme_id | body | string | 是 | 抖音号 |
| name | body | string | 是 | |
| delivery_mode | body | string | 是 | `uni` 或 `standard` |
| enabled | body | bool | 否 | 默认 true |
| department_id | body | int \| null | 否 | 仅全域。标准模式若非空则 422 |
| owner_user_id | body | int \| null | 否 | 仅全域。标准模式若非空则 422 |

## 响应

与 [list-douyin.md](list-douyin.md) 的单行字段相同。新建时 `pitcher_user_ids` 为 `[]`。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 66 | 403 | |
| 标准模式带了部门、负责人，或请求体带了投手字段 | 422 | 标准模式拒绝部门、负责人、投手分配 |
| 同一 `delivery_mode` 下 `aweme_id` 重复 | 409 | |
| 其它校验失败 | 422 | |

## 业务规则

标准号这两列必须为空，且不能在创建时写入投手。全域号可以写部门与负责人，投手仍只走分配接口。

## 被谁调用

抖音号管理页的新建。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
