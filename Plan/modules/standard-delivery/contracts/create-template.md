# 契约：create-template

业务id：standard-delivery
文档版本：3
方法：POST
路径：/api/v1/standard-delivery/templates
作用：新增一条标准投放模板。写入确认提交要用的巨量字段。不向巨量提交。全域模板不收这些字段。

作者：
状态：draft
更新日期：2026-10-08

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。免费菜单 `45`，付费菜单 `50` |
| name | body | string | 是 | 模板名称，去首尾空白，1–128 字。同一收费模式下未删除的不重名 |
| charge_mode | body | string | 是 | `IAA` 免费、`IAP` 付费。创建后不可改 |
| subject_id | body | integer | 是 | `delivery_subject.id`。须未删除、`delivery_mode=standard`，且 `charge_mode` 与模板相同 |
| bid_panels | body | string[] | 否 | 出价面板，从主体 `bid_panel` 按逗号、顿号、分号拆出的项里多选。付费至少 1 条，最多 20 条。免费可空数组或不传 |
| ads_per_account | body | integer | 是 | 每账户广告条数，1–100。这是每个账户建几条广告 |
| ocean_delivery_mode | body | string | 是 | `MANUAL` 手动、`PROCEDURAL` 自动。不是列 `delivery_mode` |
| bid_type | body | string | 是 | `CUSTOM` 稳定成本、`NO_BID` 最大转化 |
| schedule_type | body | string | 是 | `SCHEDULE_FROM_NOW` 或 `SCHEDULE_START_END` |
| schedule_start_date | body | string \| null | 否 | `yyyy-MM-dd`。只有 `SCHEDULE_START_END` 才填，且须与结束成对 |
| schedule_end_date | body | string \| null | 否 | `yyyy-MM-dd`。不能早于开始 |
| schedule_time | body | string \| null | 否 | 空表示不限。有值则为 336 位、48×7 的 `0/1` 串 |
| ad_source | body | string | 是 | 广告来源，1–100 字 |
| product_name | body | string | 是 | 产品名称，1–20 字 |
| selling_points | body | string[] | 否 | 产品卖点，最多 10 条，每条 1–20 字。不传为空数组 |
| call_to_action_buttons | body | string[] | 否 | 行动号召，最多 10 条，每条 1–20 字。不传为空数组 |
| roi_goal | body | number \| null | 否 | ROI 目标。标准模板不要传 `roi_coefficient` |
| videos_per_ad | body | integer | 是 | 每个广告使用视频数，1–30。巨量手动投放单条广告最多用 10 个 |
| titles_per_ad | body | integer | 是 | 每个广告使用标题数，1–10 |
| placement | body | string \| null | 否 | `aweme` 抖音、`aweme_feed` 抖音加头条、`universal` 通投智选。手动时含抖音信息流 |
| district | body | string \| null | 否 | `NONE` 不限、`REGION` 行政区域。不限不能带 `city_codes` |
| city_codes | body | integer[] | 否 | 城市编码。`REGION` 时至少 1 个，不重复。不传为空数组 |
| project_budget | body | number \| null | 否 | 项目预算，单位元，大于 0。不要传 `roi_coefficient` |
| product_library_id | body | integer \| null | 否 | `product_library.id`。须未删除，类型是视频库或小说库。与 `product_select` 成对 |
| product_select | body | string \| null | 否 | `this_series` 本剧、`other_series` 非本剧、`manual` 手动选择 |
| material_boost | body | boolean | 否 | 素材一键起量。产品说明没有这一项，不传为 `false` |
| promotion_operation | body | string \| null | 否 | 广告开关 `ENABLE` 或 `DISABLE`。不是项目开关 |
| douyin_account_id | body | integer \| null | 否 | 一个已启用的标准抖音号。不写全域投手分配表 |
| product_image_id | body | string \| null | 否 | `POST /api/v1/oceanengine/images` 返回的图片 id，`img-` 前缀 |
| title_select_mode | body | string \| null | 否 | `manual` 或 `auto`。写入标准列 `standard_title_select_mode`，不占用全域列 |

多传字段返回 422。不收 `roi_coefficient`、`aigc_dynamic_creative`、`asset_ids`。

示例：

```json
{
  "name": "免费模板",
  "charge_mode": "IAA",
  "subject_id": 1,
  "bid_panels": [],
  "ads_per_account": 2,
  "ocean_delivery_mode": "MANUAL",
  "bid_type": "CUSTOM",
  "schedule_type": "SCHEDULE_FROM_NOW",
  "ad_source": "来源",
  "product_name": "产品甲",
  "selling_points": ["卖点一"],
  "call_to_action_buttons": ["立即观看"],
  "videos_per_ad": 3,
  "titles_per_ad": 2
}
```

## 响应

新建后的整条记录，字段同 [list-templates.md](list-templates.md) 的列表项。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有该收费模式的菜单 |
| 404 | `主体不存在` | 主体 id 不存在或已软删 |
| 400 | `主体不是标准投放` | 主体是全域 |
| 400 | `主体收费模式与模板不一致` | 主体的 IAA/IAP 和模板不同 |
| 400 | `付费模板至少选一个出价面板` | 付费没选出价面板 |
| 400 | `主体没有出价面板` | 选了面板，但主体 `bid_panel` 为空 |
| 400 | `出价面板不在该主体上：…` | 选项不是主体面板拆出来的 |
| 409 | `模板名称已存在` | 同一收费模式下重名 |
| 400 | `抖音号不是已启用的标准号` | `douyin_account_id` 不是已启用的标准号 |
| 404 | `商品库不存在` | `product_library_id` 不存在或已软删 |
| 400 | `商品库类型须为视频库或小说库` | 商品库类型不是 video 或 novel |
| 422 | `name: ...` | 名称空白、超长、枚举不认识、面板重复、广告条数越界、多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 模板管理 | 新增 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 3 | 否 | 可保存广告位置、定向、项目预算、商品策略、素材起量开关、广告状态、抖音号、产品主图、标题选择模式。不传仍能保存旧字段 | |
| 2026-10-08 | 2 | 是 | 新增必填的巨量投放模式、竞价、投放时间、广告来源、产品名称、每广告视频数和标题数。旧请求缺这些字段会 422。快照见 [_history/create-template-v1.md](_history/create-template-v1.md) | |
| 2026-09-29 | 1 | 否 | 初稿 | |
