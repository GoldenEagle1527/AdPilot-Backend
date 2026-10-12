# 契约：upload-product

业务id：oceanengine
文档版本：2
方法：POST
路径：/api/v1/oceanengine/product-libraries/{library_id}/products
作用：向商品库上传一条短剧。

作者：
状态：draft
更新日期：2026-09-23

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单节点 `32` |
| library_id | path | int | 是 | 调用方传入的商品库 id |
| drama_name | body | string | 是 | |
| file_url | body | string | 是 | |

JSON，`extra=forbid`。不增加其它请求字段。

## 响应

成功体字段名保持。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| library_id | int | path 上的 `library_id` 原样回显 |
| product_id | int | `mock=true` 时从 `9001` 起，取自库内序列，不取进程内存 |
| drama_name | string | 原样 |
| file_url | string | 原样 |

`mock=true` 时把行写入商品表，并在同一事务把该库 `uploaded_count` 加 1。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 32 | 403 | |
| 字段校验失败 | 422 | |
| 本次应进兜底库但该组织该类型没有兜底库 | 409 | `message` 固定为 `缺少兜底库`。不上传，不加计数 |
| path 上的库不是本次应写入的那一个库 | 409 | 整次拒绝 |
| `mock=false` 且已配 secret，但开放平台 path 仍未定 | 503 | `商品库上传接口未定`。客户端不发起开放平台请求 |
| `mock=false` 且未配 secret | 503 | `巨量未配置` |

## 业务规则

- 选库只看当前用户、组织、`library_kind`。该投手若已挂这条组织、这个类型的一个标准库，短剧只进那一个库；path 的 `library_id` 必须就是它。
- 没挂标准库的，进该组织该类型的兜底库；path 的 `library_id` 必须就是这个兜底库。没有兜底库则 409，文案 `缺少兜底库`。
- 视频库与小说库分开算。只写一条上传记录。
- 成功体不增加字段。`library_id` 仍回显 path。

## 被谁调用

投放上传商品。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-23 | 2 | 否 | 写明选库规则。没有兜底库时 409，文案「缺少兜底库」。请求字段与成功体字段名不变，`library_id` 仍原样回显。路径仍为 v1 | |
| 2026-09-23 | 1 | 否 | 初稿 | |

## 内部

开放平台上传 path 未定，不出现在请求字段里。path 定了只改 Gateway 映射：503 `商品库上传接口未定` 改为成功体，成功体键仍是 `library_id` 与 `product_id`。映射可替换，响应键不变。
