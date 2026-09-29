# 契约：list-promotion-links

业务id：theater
文档版本：1
方法：GET
路径：/api/v1/theater/promotion-links
作用：分页列出端原生推广链，一条推广链一行。按创建时间倒序。对应「三方剧场/端原生推广链」列表。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| publish_date_from | query | string | 否 | 首发日期起，北京时间 `YYYY-MM-DD`，左闭（含当天 00:00:00） |
| publish_date_to | query | string | 否 | 首发日期止，北京时间 `YYYY-MM-DD`，右闭（含当天整天），不能早于起 |
| theater_app_id | query | integer | 否 | 剧场，应用 id，下拉选项取 [list-apps.md](list-apps.md)。不传=全部 |
| series_id | query | integer | 否 | 剧名，漫剧流转剧库主键，下拉搜索单选。不传=全部 |
| is_enabled | query | boolean | 否 | 启用状态：`true` 启用、`false` 停用。不传=全部 |

无请求体。需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。多传别的 query 参数返回 422。

排序固定 `created_date` 倒序、同秒按 `id` 倒序，不接受排序入参。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | PromotionLinkItem[] | |
| total | integer | |
| page | integer | |
| page_size | integer | |

**PromotionLinkItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 本库主键（十进制字符串） |
| theater_app_id | string \| null | 剧场，应用主键；还没对应上剧场为 null |
| theater_app_name | string \| null | 剧场名称，取应用列表；没对应上为 null |
| series_id | string | 漫剧流转剧库主键 |
| book_name | string | 剧名，取漫剧流转剧库 `book_name`，不可编辑 |
| is_enabled | boolean | 启用状态：`true` 启用、`false` 停用 |
| recharge_template_name | string | 出价面板，常读 `delivery.recharge_template_name` |
| publish_time | string \| null | 首发时间，常读 `book_info.publish_time`，北京时间 `+08:00`，精确到秒 |
| promotion_url | string | 推广链，常读 `promotion_info.promotion_url` |
| promotion_create_time | string \| null | 创建时间，常读 `promotion_info.create_time`，北京时间 `+08:00`，精确到秒 |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `query.publish_date_from: Input should be a valid date ...` | 日期格式不对 |
| 422 | `Value error, 首发结束日期不能早于开始日期` | 止早于起 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/端原生推广链 | 列表与筛选 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
