# 契约：update-product-library

业务id：oceanengine
文档版本：1
方法：PUT
路径：/api/v1/oceanengine/product-libraries/{id}
作用：修改商品库。不接收投手。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。不接收投手。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `68` |
| id | path | int | 是 | 本库主键 |
| name | body | string | 是 | |
| library_no | body | int | 是 | 未删除行内唯一 |
| library_kind | body | string | 是 | `novel` 或 `video` |
| organization_id | body | int | 是 | 组织的巨量账户 id |
| library_role | body | string | 是 | `fallback` 或 `standard` |

本接口不改 `uploaded_count`，也不改已分配投手。把已有投手的标准库改成 `fallback` 时 409（兜底库不能挂投手）。

## 响应

与 [list-product-libraries.md](list-product-libraries.md) 的单行字段相同。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 68 | 403 | |
| 不存在或已软删 | 404 | |
| 组织不存在，或请求体带了投手 | 422 | |
| `library_no` 与其它未删除行重复 | 409 | |
| 改完后同一组织同一类型会出现第二个 `fallback` | 409 | |
| 改成 `fallback` 时该库仍有投手 | 409 | 兜底库不能分配投手。须先把投手名单改空 |

## 业务规则

修改与创建一样不接收投手。第二个同组织同类型兜底库 409。视频库与小说库各自计兜底名额。

## 被谁调用

商品库管理页的编辑。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
