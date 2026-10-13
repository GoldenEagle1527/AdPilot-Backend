# 契约：list-editor-stats

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/materials/editor-stats
作用：剪辑师统计。一天一个素材手一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

要菜单 21。公共查询：`page`、`page_size`、`date_start`、`date_end`、`sort_order`。日期是消耗日，北京时间，默认今天，起止都含。

日期是有消耗的统计日。`sort_by`：`new_drama_count`、`drama_count`、`material_count`、`stat_cost`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| uploader_id | integer | 否 | 素材手。剪辑师和素材手忽略，只看自己 |
| department_id | integer | 否 | 素材手所在部门 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| stat_date | string | |
| uploader_id | integer | |
| uploader_name | string | |
| new_drama_count | integer | 预估可投日等于这一天，且这一天有消耗的短剧数 |
| drama_count | integer | 这一天有消耗的短剧数 |
| material_count | integer | 这一天有消耗的素材数 |
| stat_cost | number | |

`summary` 是这四个字段的列合计。点数据详情由前端跳到短剧素材手 tab，把素材手带上。

## 错误

无菜单 21 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 素材报表 / 剪辑师统计（菜单 21） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
