# 契约：list-product-libraries

业务id：oceanengine
文档版本：1
方法：GET
路径：/api/v1/oceanengine/product-libraries
作用：分页列出商品库。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `68` |
| page | query | int | 否 | 从 1，默认 1 |
| page_size | query | int | 否 | 默认 20，上限 100 |
| name | query | string | 否 | 名称模糊 |
| library_kind | query | string | 否 | `novel` 小说库，`video` 视频库 |
| organization_id | query | int | 否 | 授权组织的巨量账户 id |

## 响应

分页：`list` / `total` / `page` / `page_size`。已软删的不返回。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | 本库主键。上传接口 path 的 `library_id` 用这个 id |
| name | string | |
| library_no | int | 巨量商品库 id，未删除行内唯一 |
| library_kind | string | `novel` 或 `video` |
| organization_id | int | 所属组织的巨量账户 id |
| library_role | string | `fallback` 兜底或 `standard` 标准 |
| uploaded_count | int | 已上传短剧数，起始 0 |
| pitcher_user_ids | int[] | 标准库上的投手。兜底库恒为 `[]` |

响应不带投手以外的开放平台字段。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 68 | 403 | |
| 校验失败 | 422 | |

## 业务规则

建库不在本接口完成。列表本身不按投手过滤：菜单 68 看该筛选下的全部库。

## 被谁调用

商品库管理页。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 1 | 否 | 初稿 | |
