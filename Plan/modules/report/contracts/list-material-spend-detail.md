# 契约：list-material-spend-detail

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/materials/spend/detail
作用：素材消耗的数据详情。一条广告、一个头条素材一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

要菜单 17。公共查询：`page`、`page_size`、`date_start`、`date_end`、`sort_order`。日期是消耗日，北京时间，默认今天，起止都含。

`video_id` 与 `ocean_material_id` 二选一。`delivery`：`all`（默认）、`standard`、`uni`。

`sort_by`：`stat_cost`、`show_cnt`、`click_cnt`、`convert_cnt`、`ctr`、`cpc`、`cpm`、`conversion_rate`、`conversion_cost`。

## 响应

`summary` 只有 `stat_cost`。`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| promotion_id | integer | 广告 id，页上的创意 |
| promotion_name | string | 广告名称，页上的广告主 |
| project_id | integer | 项目 id，页上的计划 |
| ocean_material_id | integer | 头条素材 id |
| pitcher_name | string | 投放账户上的投手 |
| stat_cost | number | 消耗 |
| show_cnt | integer | 展示数 |
| click_cnt | integer | 点击数 |
| ctr | number | 点击率，百分数，点击/展示×100 |
| cpc | number | 平均点击单价，消耗/点击 |
| cpm | number | 平均千次展示费用，消耗/展示×1000 |
| convert_cnt | integer | 转化数 |
| conversion_rate | number | 转化率，百分数，转化/点击×100 |
| conversion_cost | number | 平均转化成本，消耗/转化 |

分母为 0 时比率为 0。

## 错误

两个素材 id 都缺或都传为 422。无菜单 17 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材消耗的数据详情（菜单 17） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
