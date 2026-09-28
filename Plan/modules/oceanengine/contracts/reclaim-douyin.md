# 契约：reclaim-douyin

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/douyin/{id}/reclaim
作用：回收全域抖音号的部门与负责人。投手分配保留。

作者：
状态：draft
更新日期：2026-09-23

## 请求

无请求体。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `66` |
| id | path | int | 是 | 本库主键 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | |
| department_id | null | 已清空 |
| owner_user_id | null | 已清空 |
| pitcher_user_ids | int[] | 与回收前相同，不清除 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 66 | 403 | |
| 不存在或已软删 | 404 | |
| 标准号 | 422 | 标准号没有部门与负责人可回收 |
| 该号有 `opt_status=ENABLE` 且未删除的广告 | 409 | `message` 为 `存在执行中的广告：` 接计划名（空名用 `promotion_id`，顿号分隔）。部门、负责人、投手分配都不改 |

## 业务规则

回收只清 `department_id` 与 `owner_user_id`。`douyin_pitcher` 保留。有执行中的计划则整次 409。

## 被谁调用

全域抖音号的回收。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
