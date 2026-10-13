# 契约：list-material-dramas

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/materials/dramas
作用：素材报表的短剧统计。区间内一部有消耗的剧一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

要菜单 19。公共查询：`page`、`page_size`、`date_start`、`date_end`、`sort_order`。日期是消耗日，北京时间，默认今天，起止都含。

`series_name` 模糊。`drama_age` 可重复传 `新剧`、`老剧`。新剧 = 预估可投日落在查询区间内，更早是老剧。不传为全部。`sort_by`：`stat_cost`、`material_count`。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| series_id | integer | 短剧 |
| book_name | string | 剧名。点进素材统计 tab 时带到查询 |
| material_count | integer | 视频库里这部剧的素材数，不是有消耗的条数 |
| stat_cost | number | 消耗 |

`summary`：`material_count`、`stat_cost`。

## 错误

无菜单 19 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 素材报表 / 素材报表，短剧统计 tab（菜单 19） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
