# 契约：list-material-spend

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/materials/spend
作用：素材消耗。一天一条素材一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

Header `Authorization`。要菜单 17。

公共查询：`page`、`page_size`、`date_start`、`date_end`、`sort_order`。日期是消耗日，北京时间，默认今天，起止都含。 `sort_by` 只有 `stat_cost`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| pitcher_user_id | integer | 否 | 视频上分配的投手，或投放账户上的投手 |
| uploader_id | integer | 否 | 上传者 |

## 响应

`summary` 只有 `stat_cost`。`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| stat_date | string | 日期 |
| video_id | integer 或 null | 素材库 id。对不上时为空 |
| ocean_material_id | integer | 头条素材 id |
| material_name | string | 素材名称 |
| file_url | string | 视频地址。封面和悬停预览由前端处理 |
| series_id | integer | 短剧 |
| book_name | string | 剧名 |
| material_type | string | 如 `vertical_video` |
| material_type_name | string | 竖版视频等 |
| ownership | string | `public` / `private` |
| ownership_name | string | 公有 / 私有 |
| uploader_id | integer 或 null | 上传者 |
| uploader_name | string | |
| pitcher_names | string | 多个用顿号连接 |
| stat_cost | number | 消耗 |

## 错误

无菜单 17 为 403。日期不合法为 422。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 素材报表 / 素材消耗（菜单 17） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
