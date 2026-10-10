# 契约：create-promotion-task

业务id：theater
文档版本：1
方法：POST
路径：/api/v1/theater/promotion-tasks
作用：番茄推广链同步的手动批量采集。选一部漫剧流转剧库短剧、执行时间和付费类型，写入一条来源为 manual 的初始任务。这次请求不调常读。到点后由既有任务按 book_id 拉推广链；mock 时走假客户端，不发外部 HTTP。

作者：
状态：draft
更新日期：2026-10-10

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单 `86` 番茄推广链接同步 |
| series_id | body | integer | 是 | 短剧，漫剧流转剧库主键，≥ 1。book_id 从剧库取，调用方不传 |
| execute_at | body | string | 是 | 执行时间，北京时间 `YYYY-MM-DD HH:MM:SS`，到点才拉 |
| charge_type | body | string | 否 | `all` 全部、`paid` 付费、`free` 免费。缺省 `all`。对应常读 `media_config_type`：付费 2、免费 3；全部两者都收 |

多传字段返回 422。

落库：`source=manual`，`status=pending`，`collector_id` 为当前用户，`charge_filter` 为 `all` / `IAP` / `IAA`。不改短剧的 `promotion_triggered`。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 任务主键 |
| series_id | string | 短剧主键 |
| book_name | string | 短剧名称 |
| collector_name | string | 当前用户昵称 |
| charge_type | string | 回显 `all` / `paid` / `free` |
| status | string | `pending`。列表接口仍不返回没到点的任务 |
| execute_at | string | 北京时间 `+08:00`，精确到秒 |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 400 | `短剧没有 book_id` | 剧库这一行没有可用 book_id |
| 404 | `短剧不存在` | 主键不存在或已删除 |
| 422 | `时间格式为 YYYY-MM-DD HH:MM:SS` | 执行时间没带到秒 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 三方剧场/番茄推广链同步 | 批量采集 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-10 | 1 | 否 | 初稿 | |
