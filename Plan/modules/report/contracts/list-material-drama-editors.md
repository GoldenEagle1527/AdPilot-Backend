# 契约：list-material-drama-editors

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/materials/drama-editors
作用：短剧素材手统计。一部剧、一个素材手一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

要菜单 19。公共查询：`page`、`page_size`、`date_start`、`date_end`、`sort_order`。日期是消耗日，北京时间，默认今天，起止都含。

`series_name` 模糊。`drama_age` 可重复传 `新剧`、`老剧`。新剧 = 预估可投日落在查询区间内，更早是老剧。不传为全部。`sort_by`：`stat_cost`、`material_count`。

另有 `uploader_id`。剪辑师角色或用户标签「素材手」忽略该参数，只看自己。负责人和运营管理员可筛。

## 响应

短剧统计的字段，再加 `uploader_id`、`uploader_name`。`material_count` 仍是这部剧在视频库的条数。`summary.material_count` 按剧去重，同一部剧多个素材手只计一次。

## 错误

无菜单 19 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材报表，短剧素材手统计 tab（菜单 19） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
