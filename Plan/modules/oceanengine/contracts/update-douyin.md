# 契约：update-douyin

业务id：oceanengine
文档版本：1
方法：PUT
路径：/api/v1/oceanengine/douyin/{id}
作用：修改抖音号资料。启停、分配、回收、删除走各自接口。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。不接收投手列表。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `66` |
| id | path | int | 是 | 本库主键 |
| aweme_id | body | string | 是 | |
| name | body | string | 是 | |
| delivery_mode | body | string | 是 | `uni` 或 `standard`。改为 `standard` 时部门与负责人必须为空 |
| enabled | body | bool | 是 | 从开到关且有执行中计划则 409，规则同启停接口 |
| department_id | body | int \| null | 否 | 标准模式非空则 422 |
| owner_user_id | body | int \| null | 否 | 标准模式非空则 422 |

## 响应

与 [list-douyin.md](list-douyin.md) 的单行字段相同。本接口不改 `pitcher_user_ids`。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 66 | 403 | |
| 不存在或已软删 | 404 | |
| 标准模式带了部门、负责人，或请求体带了投手字段 | 422 | |
| 同一模式下 `aweme_id` 与其它未删除行重复 | 409 | |
| 从开到关时存在 `opt_status=ENABLE` 的广告 | 409 | `message` 带计划名，见启停契约 |

## 业务规则

标准模式拒绝部门、负责人、投手分配。改成标准模式不会自动写入投手；已有全域投手分配若模式改为标准，整次 422，须先处理分配后再改模式。本接口不清除投手分配。

## 被谁调用

抖音号管理页的编辑。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
