# 契约：set-douyin-enabled

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/douyin/{id}/enabled
作用：直接改抖音号启停。从开到关之前查投放占用。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `66` |
| id | path | int | 是 | 本库主键 |
| enabled | body | bool | 是 | |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | |
| enabled | bool | 写入后的值 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 66 | 403 | |
| 不存在或已软删 | 404 | |
| 从开到关，且该号有 `opt_status=ENABLE` 且未删除的广告 | 409 | `message` 为 `存在执行中的广告：` 接计划名。名为空时用 `promotion_id` 文本，多个用顿号。整次不改 `enabled` |

从关到开不查占用。

## 业务规则

占用只认广告 `opt_status=ENABLE` 且未删除，并挂在这个抖音号上。

## 被谁调用

抖音号列表上的启停。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
