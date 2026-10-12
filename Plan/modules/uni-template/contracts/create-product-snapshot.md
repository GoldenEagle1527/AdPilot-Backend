# 契约：create-product-snapshot

业务id：uni-template
文档版本：1
方法：POST
路径：/api/v1/uni-templates/product-snapshots
作用：保存一份产品模板。字段与标准投放的产品快照相同，写入同一张表。没有厂商同步。

作者：
状态：draft
更新日期：2026-10-12

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。全域模板菜单 `60` |
| name | body | string | 是 | 弹框里的产品模板名称，1–128 字。未删除的不重名 |
| product_name | body | string | 是 | 产品名称，1–20 字 |
| product_image_id | body | string | 是 | 产品主图 id，`img-` 前缀 |
| selling_points | body | string[] | 否 | 卖点，最多 10 条，每条 6–9 个字，字母和数字算半个字 |
| call_to_action_buttons | body | string[] | 否 | 行动号召，最多 10 条，每条 2–6 个字，字母和数字算半个字 |

多传返回 422。

## 响应

新建后的整条记录，字段同 [list-product-snapshots.md](list-product-snapshots.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有全域模板菜单 |
| 409 | `产品快照名称已存在` | 未删除的同名模板 |
| 422 | `产品主图须为 img- 开头的图片 id` | 主图号不合格，或卖点、行动号召字数不对 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域模板 | 保存模板 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-12 | 1 | 否 | 初稿。对应 3.3.1 产品信息截图里的「保存模版」，以及标准投放第 12 条「弹框输入产品模版名称」 | |
