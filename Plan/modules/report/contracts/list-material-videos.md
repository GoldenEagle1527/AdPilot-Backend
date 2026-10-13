# 契约：list-material-videos

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/materials/videos
作用：素材统计。一条有消耗的素材一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

同短剧素材手：菜单 19，日期、剧名、新老剧、`uploader_id`。剪辑师和素材手只看自己。公共查询：`page`、`page_size`、`date_start`、`date_end`、`sort_order`。日期是消耗日，北京时间，默认今天，起止都含。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| video_id | integer 或 null | 素材库 id |
| ocean_material_id | integer | 头条素材 id |
| file_url | string | 悬停预览用，前端播 |
| series_id | integer | |
| book_name | string | |
| uploader_id | integer 或 null | 素材手 |
| uploader_name | string | |
| material_name | string | |
| stat_cost | number | |

`summary.material_count` 是行数，`summary.stat_cost` 是消耗合计。

## 错误

无菜单 19 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材报表，素材统计 tab（菜单 19） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
