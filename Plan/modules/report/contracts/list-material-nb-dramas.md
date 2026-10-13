# 契约：list-material-nb-dramas

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/materials/nb-dramas
作用：未上 NB 新剧。日期是预估可投日。

作者：
状态：draft
更新日期：2026-10-13

## 请求

要菜单 19，并且要组件 20。剪辑师没有组件 20。

`date_start`、`date_end` 筛的是短剧预估可投日，不是消耗日。`series_name` 模糊。`sort_by`：`material_count`、`estimate_publish_date`。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| series_id | integer | |
| book_name | string | |
| estimate_publish_date | string | 预估可投日 |
| material_count | integer | 模板名含 NB 或 CBO 的计划里，这部剧用到的视频数。可以为 0 |

`summary` 只有 `material_count`。

## 错误

无菜单 19 或无组件 20 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材报表，未上 NB 新剧 tab（菜单 19，还要组件 20） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
