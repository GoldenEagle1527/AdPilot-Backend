# 契约：delete-product-library

业务id：oceanengine
文档版本：1
方法：DELETE
路径：/api/v1/oceanengine/product-libraries/{id}
作用：软删商品库。已有投手或已上传短剧时拒绝。

作者：
状态：draft
更新日期：2026-09-23

## 请求

无请求体。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `68` |
| id | path | int | 是 | 本库主键 |

## 响应

成功 `data` 为 null。HTTP 200。行软删后列表不再返回。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 68 | 403 | |
| 不存在或已软删 | 404 | |
| 仍有投手关联，或 `uploaded_count > 0` | 409 | 不软删 |

## 业务规则

删除前只看投手关联和 `uploaded_count`，不对商品表做全表计数。两个条件任一命中即 409。

## 被谁调用

商品库管理页的删除。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
