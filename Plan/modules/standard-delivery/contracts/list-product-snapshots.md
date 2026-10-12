# 契约：list-product-snapshots

业务id：standard-delivery
文档版本：1
方法：GET
路径：/api/v1/standard-delivery/product-snapshots
作用：分页列出产品快照。

作者：
状态：draft
更新日期：2026-10-09

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。模板菜单 `45` 或 `50` |
| page | query | integer | 否 | 页码，从 1 起 |
| page_size | query | integer | 否 | 每页条数，默认 20，最大 100 |
| name | query | string | 否 | 快照名称，模糊 |

## 响应

`data.list[]`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 快照 id |
| name | string | 快照名称 |
| product_name | string | 产品名称 |
| product_image_id | string | 主图 id |
| selling_points | string[] | 卖点 |
| call_to_action_buttons | string[] | 行动号召 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

另有 `total`、`page`、`page_size`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有模板菜单 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 标准模板 | 选择产品模板 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 1 | 否 | 初稿 | |
