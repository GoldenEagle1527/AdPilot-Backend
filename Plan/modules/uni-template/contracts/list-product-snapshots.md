# 契约：list-product-snapshots

业务id：uni-template
文档版本：1
方法：GET
路径：/api/v1/uni-templates/product-snapshots
作用：分页列出产品模板。与标准投放共用 `delivery_product_snapshot`，不是某条全域模板上的字段。

作者：
状态：draft
更新日期：2026-10-12

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。全域模板菜单 `60` |
| page | query | integer | 否 | 页码，从 1 起 |
| page_size | query | integer | 否 | 每页条数，默认 20，最大 100 |
| name | query | string | 否 | 模板名称，模糊 |

## 响应

`data.list[]` 与标准投放 [list-product-snapshots.md](../../standard-delivery/contracts/list-product-snapshots.md) 相同：`id`、`name`、`product_name`、`product_image_id`、`selling_points`、`call_to_action_buttons`、`created_at`、`updated_at`。另有 `total`、`page`、`page_size`。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有全域模板菜单 |
| 422 | `page: ...` | 分页越界、多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域模板 | 选择产品模板 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-12 | 1 | 否 | 初稿。对应《OC投放中台》3.3.1 产品信息截图里的「选择产品模版」 | |
