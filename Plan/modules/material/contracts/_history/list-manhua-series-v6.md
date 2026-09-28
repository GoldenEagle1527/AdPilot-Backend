# 契约：list-manhua-series

业务id：material
文档版本：6
方法：GET
路径：/api/v1/material/manhua-series
作用：分页列出已从常读同步落库的短剧/漫剧。各 tab 的筛选和列表字段相同，tab 只按 `tab_text` 的 IAA/IAP 快捷筛选。不做数据范围过滤。

作者：调度者
状态：accepted
更新日期：2026-09-22

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| tab_text | query | string | 否 | tab。`IAA` 或 `IAP`，与落库列相同。不传=全部 |
| book_name | query | string | 否 | 短剧名称，模糊 |
| estimate_publish_time_from | query | string | 否 | 预估可投起，`YYYY-MM-DD HH:MM:SS`，与常读原串直接比，左闭 |
| estimate_publish_time_to | query | string | 否 | 预估可投止，`YYYY-MM-DD HH:MM:SS`，右闭 |
| collected_at_from | query | string | 否 | 采集时间起，`YYYY-MM-DD HH:MM:SS`，北京时间，左闭 |
| collected_at_to | query | string | 否 | 采集时间止，`YYYY-MM-DD HH:MM:SS`，北京时间，右闭 |
| publish_status | query | integer | 否 | 下拉单选：`1` 未发布、`2` 已发布。不传=全部（含已下架 `3`） |
| listed_today | query | boolean | 否 | 是否当天上架。`true` 是、`false` 否。不传=全部。按 `publish_time` 的北京日历日 |
| department_id | query | string | 否 | 部门组织下拉。视频块未开，该列恒空，传入则结果为空 |
| episode_amount_min | query | integer | 否 | 集数下限，含 |
| episode_amount_max | query | integer | 否 | 集数上限，含 |

无请求体。需 `Authorization: Bearer` 且有效菜单含节点 `95`。

常读入参 `publish_status` 是 `0` 未发布 / `1` 已发布，本接口不透传常读 query。常读出参是 `1` 未发布 / `2` 已发布 / `3` 已下架。

时间段只传一边时，另一边不限制。格式不是 `YYYY-MM-DD HH:MM:SS`，或结束早于开始，返回 422。集数上限小于下限同样。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | ManhuaSeriesItem[] | 各 tab 字段相同 |
| total | integer | |
| page | integer | |
| page_size | integer | |

**ManhuaSeriesItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 本库主键（整数自增，JSON 仍为十进制字符串） |
| playlet_id | string | 常读 `playlet_id`（抖音专辑 ID） |
| book_id | string | 常读 `book_id` |
| category_text | string | 常读题材，逗号分隔 |
| tab_text | string | 落库值：`IAA` 或 `IAP` |
| thumb_url | string | 封面 |
| book_name | string | 短剧名称 |
| episode_amount | integer | 集数 |
| department_name | string \| null | 本轮恒 `null` |
| publish_status | integer | 常读出参 |
| delivery_status | boolean | 可投状态 |
| publish_time | string | 常读发布时间原串，北京朴素时间，如 `2026-09-23 09:50:00` |
| estimate_publish_time | string | 常读预估可投原串，同上 |
| create_time | string | 常读创建时间原串，同上 |
| collected_at | string | 本库采集时间，北京时间 `+08:00` |
| douyin_nick_name | string | 抖音号 |

## 错误

无本接口特有错误。共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/漫剧流转剧库 | 列表与筛选 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-22 | 6 | 是 | 预估可投、采集时间的查询改为 `YYYY-MM-DD HH:MM:SS`，按该时刻左闭右闭 | |
| 2026-09-22 | 5 | 否 | 常读 `publish_time` / `estimate_publish_time` / `create_time` 原样返回 | |
| 2026-09-22 | 4 | 是 | tab 查询和返回改为 `tab_text`，取值 `IAA`/`IAP`，不再映射付费/免费 | |
| 2026-09-22 | 3 | 是 | tab 改为 `pay_text`（付费/免费，由单价判断）；`category_text` 只作题材返回；日期改为北京日历日 | |
| 2026-09-21 | 2 | 否 | 主键改为库内整数自增；JSON 仍是 string | |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
