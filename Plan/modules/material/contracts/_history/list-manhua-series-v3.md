# 契约：list-manhua-series

业务id：material
文档版本：3
方法：GET
路径：/api/v1/material/manhua-series
作用：分页列出已从常读同步落库的短剧/漫剧。各 tab 的筛选和列表字段相同，tab 只是付费/免费的快捷筛选。不做数据范围过滤。

作者：调度者
状态：accepted
更新日期：2026-09-22

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| pay_text | query | string | 否 | tab。`付费` 或 `免费`。`single_price` 能解析且大于 0 为付费，否则免费。不传=全部 |
| book_name | query | string | 否 | 短剧名称，模糊 |
| estimate_publish_time_from | query | string | 否 | 预估可投起，`YYYY-MM-DD`，北京日历日，左闭 |
| estimate_publish_time_to | query | string | 否 | 预估可投止，`YYYY-MM-DD`，北京日历日，右闭 |
| collected_at_from | query | string | 否 | 采集日起，`YYYY-MM-DD`，北京日历日，左闭 |
| collected_at_to | query | string | 否 | 采集日止，`YYYY-MM-DD`，北京日历日，右闭 |
| publish_status | query | integer | 否 | 下拉单选：`1` 未发布、`2` 已发布。不传=全部（含已下架 `3`） |
| listed_today | query | boolean | 否 | 是否当天上架。`true` 是、`false` 否。不传=全部。按 `publish_time` 的北京日历日 |
| department_id | query | string | 否 | 部门组织下拉。视频块未开，该列恒空，传入则结果为空 |
| episode_amount_min | query | integer | 否 | 集数下限，含 |
| episode_amount_max | query | integer | 否 | 集数上限，含 |
| page | query | integer | 否 | 从 1；缺省按全站分页约定 |
| page_size | query | integer | 否 | 默认 20、上限 100 |

无请求体。需 `Authorization: Bearer` 且有效菜单含节点 `95`。

常读入参 `publish_status` 是 `0` 未发布 / `1` 已发布，本接口不透传常读 query。常读出参是 `1` 未发布 / `2` 已发布 / `3` 已下架。

日期段只传一边时，另一边不限制。结束早于开始返回 `VALIDATION_ERROR`。集数上限小于下限同样。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| items | ManhuaSeriesItem[] | 各 tab 字段相同 |
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
| pay_text | string | `single_price` 大于 0 为 `付费`，否则 `免费` |
| thumb_url | string | 封面 |
| book_name | string | 短剧名称 |
| episode_amount | integer | 集数 |
| department_name | string \| null | 本轮恒 `null` |
| publish_status | integer | 常读出参 |
| delivery_status | boolean | 可投状态 |
| publish_time | string | 发布时间；能解析则为北京时间 `+08:00`，否则原串 |
| estimate_publish_time | string | 预估可投；同上 |
| create_time | string | 常读创建时间；同上 |
| collected_at | string | 本库采集时间，北京时间 `+08:00` |
| douyin_nick_name | string | 抖音号 |

## 错误

无本接口特有错误。共用码见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/漫剧流转剧库 | 列表与筛选 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-22 | 3 | 是 | tab 改为 `pay_text`（付费/免费，由单价判断）；`category_text` 只作题材返回；日期改为北京日历日 | |
| 2026-09-21 | 2 | 否 | 主键改为库内整数自增；JSON 仍是 string | |
| 2026-09-20 | 1 | 否 | 初稿 | 调度者 |
