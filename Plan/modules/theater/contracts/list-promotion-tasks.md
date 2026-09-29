# 契约：list-promotion-tasks

业务id：theater
文档版本：1
方法：GET
路径：/api/v1/theater/promotion-tasks
作用：分页列出番茄推广链同步任务，一次采集一行。只返回爬虫处理中、成功、失败三种；没到执行时间（pending）和排队中（queued）的任务不出现。按执行时间倒序。对应「三方剧场/番茄推广链同步」。

作者：
状态：draft
更新日期：2026-09-28

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | 从 1；缺省 1 |
| page_size | query | integer | 否 | 默认 20、上限 100 |
| book_name | query | string | 否 | 短剧名称，模糊，去首尾空白。不传=全部 |
| status | query | string | 否 | `running` 爬虫处理中、`success` 成功、`failed` 失败。不传=三种全部 |
| execute_at_from | query | string | 否 | 执行时间起，北京时间 `YYYY-MM-DD HH:MM:SS`，左闭 |
| execute_at_to | query | string | 否 | 执行时间止，北京时间 `YYYY-MM-DD HH:MM:SS`，右闭，不能早于起 |

无请求体。需 `Authorization: Bearer`。接口层不校验菜单节点，登录即可调。多传别的 query 参数返回 422。

排序固定 `execute_at` 倒序、同秒按 `id` 倒序，不接受排序入参。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | PromotionTaskItem[] | |
| total | integer | |
| page | integer | |
| page_size | integer | |

**PromotionTaskItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 本库主键（十进制字符串） |
| series_id | string | 漫剧流转剧库主键（十进制字符串） |
| book_name | string | 短剧名称，取剧库 |
| collector_name | string | 采集人昵称；自动触发为 `系统` |
| tab_text | string | 付费类型：`IAA`、`IAP`，取剧库 |
| category_text | string | 短剧类型，常读题材逗号分隔，取剧库 |
| status | string | `running` 爬虫处理中、`success` 成功、`failed` 失败 |
| reason | string | 原因，常读响应 `message` 或本地失败原因；成功一般为空串 |
| execute_at | string | 执行时间，北京时间 `+08:00`，精确到秒 |
| finished_at | string \| null | 完成时间，北京时间 `+08:00`，精确到秒；爬虫处理中为 null |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 422 | `query.status: Input should be 'running', 'success' or 'failed'` | `status` 传了 `pending`/`queued` 等不认识的值 |
| 422 | `query.execute_at_from: Value error, 时间格式为 YYYY-MM-DD HH:MM:SS` | 时间没带到秒或格式不对 |
| 422 | `Value error, 执行结束时间不能早于开始时间` | 止早于起 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/番茄推广链同步 | 列表与筛选 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-28 | 1 | 否 | 初稿 | |
