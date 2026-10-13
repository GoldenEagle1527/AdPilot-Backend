# 契约：list-editor-spend

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/materials/editors
作用：剪辑师消耗。一天一个素材手一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

要菜单 18。公共查询：`page`、`page_size`、`date_start`、`date_end`、`sort_order`。日期是消耗日，北京时间，默认今天，起止都含。

`sort_by`：`stat_cost`、`cost_ex_nobid`、`standard_non_nobid_cost`、`standard_nobid_cost`、`uni_gmv`、`group_avg_roi`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| uploader_id | integer | 否 | 素材手，即视频上传人 |
| department_id | integer | 否 | 素材手所在部门 |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| stat_date | string | |
| uploader_id | integer | |
| uploader_name | string | |
| cost_ex_nobid | number | 总消耗减标准 nobid 消耗 |
| standard_non_nobid_cost | number | 标准、且模板名不含 NB/CBO |
| standard_nobid_cost | number | 标准、且模板名含 NB 或 CBO |
| uni_gmv | number | 全域投放的回收。时间跨度跟查询走 |
| group_avg_roi | number 或 null | 登录人所在部门全部素材手、当前查询区间的回收/消耗。每行相同 |
| stat_cost | number | 总消耗，标准加全域 |

`summary` 同这些金额字段，`group_avg_roi` 为 null。没有上传人的素材不进这张表。

## 错误

无菜单 18 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 素材报表 / 剪辑师消耗（菜单 18） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
