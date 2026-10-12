# 契约：list-templates

业务id：standard-delivery
文档版本：5
方法：GET
路径：/api/v1/standard-delivery/templates
作用：按收费模式分页列出投放模板。免费、付费分两次查。

作者：
状态：draft
更新日期：2026-10-09

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。免费菜单 `45`，付费菜单 `50` |
| charge_mode | query | string | 是 | `IAA` 免费、`IAP` 付费 |
| name | query | string | 否 | 模板名称，模糊 |
| subject_id | query | integer | 否 | 投放主体 id |
| page | query | integer | 否 | 从 1 起，默认 1 |
| page_size | query | integer | 否 | 默认 20，最大 100 |

## 响应

分页。`list` 每项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 模板 id |
| name | string | 模板名称 |
| charge_mode | string | `IAA` 或 `IAP` |
| subject_id | string | 主体 id |
| subject_name | string | 主体名称 |
| bid_panels | string[] | 出价面板 |
| ads_per_account | integer | 每账户广告条数，1–100 |
| ocean_delivery_mode | string \| null | 巨量投放模式 `MANUAL` 或 `PROCEDURAL`。不是本表列 `delivery_mode` |
| bid_type | string \| null | `CUSTOM` 稳定成本、`NO_BID` 最大转化 |
| schedule_type | string \| null | `SCHEDULE_FROM_NOW` 或 `SCHEDULE_START_END` |
| schedule_start_date | string \| null | `yyyy-MM-dd`。只有自选起止才有 |
| schedule_end_date | string \| null | `yyyy-MM-dd`。只有自选起止才有 |
| schedule_time | string \| null | 空表示不限。有值则为 48×7 的 `0/1` 串 |
| ad_source | string \| null | 广告来源 |
| product_name | string \| null | 产品名称，最多 20 字 |
| selling_points | string[] | 产品卖点 |
| call_to_action_buttons | string[] | 行动号召 |
| roi_goal | string \| null | ROI 目标，三位小数。标准模板不用 `roi_coefficient` |
| videos_per_ad | integer \| null | 每个广告视频数，1–30 |
| titles_per_ad | integer \| null | 每个广告标题数，1–10 |
| placement | string \| null | 广告位置：`aweme` 抖音、`aweme_feed` 抖音加头条、`universal` 通投智选。手动时含抖音信息流 |
| district | string \| null | 用户定向：`NONE` 不限、`REGION` 行政区域 |
| city_codes | integer[] | 城市编码。不限时为 `[]` |
| gender | string | 用户定向性别：`none` 不限、`male` 男、`female` 女。旧行按 `none` 返回 |
| age_bands | string[] | `18_23`、`24_30`、`31_40`、`41_49`、`50_plus`。空数组表示年龄不限 |
| project_budget | string \| null | 项目预算，元，两位小数。标准模板可以保存 |
| library_kind | string \| null | `video` 视频库、`novel` 小说库。不是某一行商品库 |
| product_select | string \| null | `this_series` 本剧、`other_series` 非本剧、`manual` 手动选择。可以和 `library_kind` 各自为空 |
| material_boost | boolean | 素材一键起量。产品说明没有这一项，空行按关返回 |
| promotion_operation | string \| null | 广告开关 `ENABLE` 或 `DISABLE`。不是项目开关 |
| douyin_account_id | string \| null | 一个标准抖音号 id。不是全域按投手分配的那张表 |
| product_image_id | string \| null | 产品主图 id，`img-` 前缀 |
| title_select_mode | string \| null | 标题选择 `manual` 或 `auto`。存在 `standard_title_select_mode`，不占用全域列 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有该收费模式的菜单 |
| 422 | `charge_mode: ...` | 收费模式不认识，或分页越界 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 免费/付费端原生模板管理 | 打开列表 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 5 | 否 | 列表项增加 `gender`、`age_bands`。不传性别按 `none`，年龄空数组表示不限 | |
| 2026-10-09 | 4 | 是 | 列表项去掉 `product_library_id`，改为 `library_kind`。`product_select` 仍在 | |
| 2026-10-08 | 3 | 否 | 列表项增加广告位置、定向、项目预算、商品策略、素材起量开关、广告状态、抖音号、产品主图、标题选择模式。旧行可以为空 | |
| 2026-10-08 | 2 | 否 | 列表项增加巨量投放模式、竞价、投放时间、时段、广告来源、产品名称、卖点、行动号召、ROI、每广告视频数和标题数。旧行这些字段可以为空 | |
| 2026-09-29 | 1 | 否 | 初稿 | |
