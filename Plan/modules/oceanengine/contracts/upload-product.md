# 契约：upload-product

业务id：oceanengine
文档版本：3
方法：POST
路径：/api/v1/oceanengine/products
作用：按巨量商品库号上传一条短剧。假客户端不返回 503。

作者：
状态：draft
更新日期：2026-10-08

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `32` |
| advertiser_id | body | int | 是 | 广告账户 |
| library_no | body | int | 是 | `product_library.library_no`。用来定位商品库 |
| book_name | body | string | 是 | 短剧名，1–512 字。写入 `oe_product.drama_name` |

JSON，`extra=forbid`。不再收 `drama_name`、`file_url`。不增加短剧行业字段表。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| advertiser_id | int | 原样 |
| library_no | int | 原样 |
| book_name | string | 原样 |
| product_id | int | 假客户端从 `9001` 起，取自库内序列，不取进程内存 |

`mock=true` 时装上的假客户端返回 `product_id`，本接口把行写入 `oe_product`，`file_url` 为空，并在同一事务把该库 `uploaded_count` 加 1。这条假路径不返回 503。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 32 | 403 | |
| 字段校验失败 | 422 | 含仍传 `drama_name` 或 `file_url` |
| `library_no` 没有未删除的库 | 404 | `商品库不存在` |
| 本次应进兜底库但该组织该类型没有兜底库 | 409 | `message` 固定为 `缺少兜底库`。不上传，不加计数 |
| 库不是本次应写入的那一个库 | 409 | 整次拒绝 |
| 真客户端且开放平台 path 仍未定 | 503 | `商品库上传接口未定`。不发起开放平台请求 |
| 未装客户端或未配 secret | 503 | `巨量未配置` |

## 业务规则

- 库只按 `library_no` 找。找到后再用原来的选库规则：该投手若已挂这条组织、这个类型的一个标准库，短剧只进那一个库。
- 没挂标准库的，进该组织该类型的兜底库。没有兜底库则 409，文案 `缺少兜底库`。
- 视频库与小说库分开算。只写一条上传记录。
- 不建短剧行业字段表。

## 被谁调用

投放上传商品。确认提交测试走这条假路径。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 3 | 是 | 路径改为 `/products`。正文改为 `advertiser_id`、`library_no`、`book_name`。不再要求 `drama_name`、`file_url`。假客户端不 503。快照见 [_history/upload-product-v2.md](_history/upload-product-v2.md) | |
| 2026-09-23 | 2 | 否 | 写明选库规则。没有兜底库时 409，文案「缺少兜底库」。请求字段与成功体字段名不变，`library_id` 仍原样回显。路径仍为 v1 | |
| 2026-09-23 | 1 | 否 | 初稿 | |

## 内部

真客户端仍不打开放平台。假客户端发号并允许写入 `oe_product`。
