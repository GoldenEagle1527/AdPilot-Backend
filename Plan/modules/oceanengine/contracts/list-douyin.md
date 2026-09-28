# 契约：list-douyin

业务id：oceanengine
文档版本：1
方法：GET
路径：/api/v1/oceanengine/douyin
作用：按投放模式分页列出抖音号。全域与标准分两次查。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `66` |
| delivery_mode | query | string | 是 | `uni` 全域或 `standard` 标准 |
| aweme_id | query | string | 否 | 抖音号精确 |
| name | query | string | 否 | 名称模糊 |
| department_id | query | int | 否 | 部门。仅 `uni`。`standard` 时若传入则 422 |
| page | query | int | 否 | 从 1，默认 1 |
| page_size | query | int | 否 | 默认 20，上限 100 |

## 响应

分页：`list` / `total` / `page` / `page_size`。已软删的不返回。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | 本库主键 |
| aweme_id | string | 抖音号。同一 `delivery_mode` 下未删除行唯一 |
| name | string | |
| delivery_mode | string | `uni` 或 `standard` |
| enabled | bool | |
| department_id | int \| null | 仅全域有值。标准号恒为 null |
| owner_user_id | int \| null | 部门负责人。仅全域。标准号恒为 null |
| pitcher_user_ids | int[] | 已分配投手。标准号恒为 `[]` |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 66 | 403 | |
| 缺少 `delivery_mode`，或标准模式带了 `department_id` | 422 | |

## 业务规则

- 标准号全员投手共用，没有投手分配，也没有部门与负责人。
- 全域号可以有部门和部门负责人，并分配多个投手。分配见单独接口，菜单 `67` 或 `66`。
- 本阶段不从巨量拉号。号是中台录入的 `aweme_id`。

## 被谁调用

抖音号管理页、全域抖音号分配页。两页各带自己的 `delivery_mode`。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
