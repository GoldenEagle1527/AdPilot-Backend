# 契约：create-product-library

业务id：oceanengine
文档版本：1
方法：POST
路径：/api/v1/oceanengine/product-libraries
作用：创建商品库。不接收投手。

作者：
状态：draft
更新日期：2026-09-23

## 请求

JSON，`extra=forbid`。请求体没有投手字段，传入 `pitcher_user_ids` 等则 422。

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `68` |
| name | body | string | 是 | |
| library_no | body | int | 是 | 巨量商品库 id，未删除行内唯一 |
| library_kind | body | string | 是 | `novel` 或 `video` |
| organization_id | body | int | 是 | 授权组织的巨量账户 id，组织须存在且未删除 |
| library_role | body | string | 是 | `fallback` 或 `standard` |

## 响应

与 [list-product-libraries.md](list-product-libraries.md) 的单行字段相同。`uploaded_count` 为 0。`pitcher_user_ids` 为 `[]`。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 68 | 403 | |
| 组织不存在 | 422 | |
| 缺少 `library_role`，或取值不是 `fallback`\|`standard` | 422 | |
| 请求体带了投手 | 422 | 创建不接收投手 |
| `library_no` 与未删除行重复 | 409 | |
| 同一 `organization_id`、同一 `library_kind` 下已有未删除的 `fallback` | 409 | 第二个兜底库。整次不创建 |

## 业务规则

- `library_role` 创建时必填。同一组织、同一类型只允许一个兜底库。
- 标准库可以有多条。未分配投手前不接上传；没挂标准库的投手走兜底库。没有兜底库时上传 409，文案 `缺少兜底库`（见上传契约）。
- 兜底库不能分配投手。分配是后来的接口，不在创建体里。

## 被谁调用

商品库管理页的新建。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
