# 契约：update-promotion-link

业务id：theater
文档版本：1
方法：PATCH
路径：/api/v1/theater/promotion-links/{link_id}
作用：编辑一条端原生推广链。剧名（所属短剧）不可改，其它字段都可改；只改传了的字段。对应「三方剧场/端原生推广链」编辑。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| link_id | path | integer | 是 | 推广链主键 |
| theater_app_id | body | integer \| null | 否 | 剧场，应用 id；传 `null` 清空 |
| is_enabled | body | boolean | 否 | 启用状态：`true` 启用、`false` 停用 |
| recharge_template_name | body | string | 否 | 出价面板，去首尾空白，1–128 字 |
| publish_time | body | string | 否 | 首发时间，北京时间 `YYYY-MM-DD HH:MM:SS` |
| promotion_url | body | string | 否 | 推广链，去首尾空白，1–2048 字 |
| promotion_create_time | body | string | 否 | 创建时间，北京时间 `YYYY-MM-DD HH:MM:SS` |

body 至少传一个字段。除 `theater_app_id` 外其它字段不能传 `null`。多传字段（如 `book_name`、`series_id`）返回 422。需 `Authorization: Bearer`。

## 响应

返回改后的一条 PromotionLinkItem，字段同 [list-promotion-links.md](list-promotion-links.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `推广链不存在` | `link_id` 不存在或已删除 |
| 404 | `剧场不存在` | `theater_app_id` 对应的应用不存在或已删除 |
| 422 | `Value error, 至少修改一项` | body 为空 |
| 422 | `Value error, 不能为空：promotion_url` | 除剧场外的字段传了 `null` |
| 422 | `body.book_name: Extra inputs are not permitted` | 想改剧名等不可改字段 |
| 422 | `body.publish_time: Value error, 时间格式为 YYYY-MM-DD HH:MM:SS` | 时间没带到秒或格式不对 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/端原生推广链 | 编辑 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
