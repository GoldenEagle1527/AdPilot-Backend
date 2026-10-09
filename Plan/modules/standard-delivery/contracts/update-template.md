# 契约：update-template

业务id：standard-delivery
文档版本：5
方法：PUT
路径：/api/v1/standard-delivery/templates/{template_id}
作用：整表保存标准模板。收费模式不可改。标准提交字段与新增相同。

作者：
状态：draft
更新日期：2026-10-09

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单须覆盖这条模板现有的收费模式 |
| template_id | path | integer | 是 | 模板 id |
| name | body | string | 是 | 同新增 |
| subject_id | body | integer | 是 | 同新增。仍须是标准投放，且收费模式与这条模板一致 |
| bid_panels | body | string[] | 否 | 同新增。付费模板保存后不能是空的 |
| ads_per_account | body | integer | 是 | 1–100 |
| ocean_delivery_mode | body | string | 是 | 同新增 |
| bid_type | body | string | 是 | 同新增 |
| schedule_type | body | string | 是 | 同新增 |
| schedule_start_date | body | string \| null | 否 | 同新增 |
| schedule_end_date | body | string \| null | 否 | 同新增 |
| schedule_time | body | string \| null | 否 | 同新增。空表示不限 |
| ad_source | body | string | 是 | 同新增 |
| product_name | body | string | 是 | 同新增，最多 20 字 |
| selling_points | body | string[] | 否 | 同新增 |
| call_to_action_buttons | body | string[] | 否 | 同新增 |
| roi_goal | body | number \| null | 否 | 同新增。不要传 `roi_coefficient` |
| videos_per_ad | body | integer | 是 | 1–30 |
| titles_per_ad | body | integer | 是 | 1–10 |
| placement | body | string \| null | 否 | 同新增 |
| district | body | string \| null | 否 | 同新增 |
| city_codes | body | integer[] | 否 | 同新增 |
| gender | body | string | 否 | 同新增。不传为 `none` |
| age_bands | body | string[] | 否 | 同新增。空数组表示年龄不限，重复则 422 |
| project_budget | body | number \| null | 否 | 同新增。不要传 `roi_coefficient` |
| library_kind | body | string \| null | 否 | 同新增。`video` 或 `novel`，可以不填 |
| product_select | body | string \| null | 否 | 同新增。可以只填这一项 |
| material_boost | body | boolean | 否 | 同新增。不传为关 |
| promotion_operation | body | string \| null | 否 | 同新增。广告开关，不是项目开关 |
| douyin_account_id | body | integer \| null | 否 | 同新增 |
| product_image_id | body | string \| null | 否 | 同新增 |
| title_select_mode | body | string \| null | 否 | 同新增。写入标准列，不占用全域 `title_select_mode` |

不收 `charge_mode`、`product_library_id`、`roi_coefficient`、`aigc_dynamic_creative`、`asset_ids`。多传返回 422。只传 `product_select`、不传商品库行，不再返回「商品库和商品选择须同时填写」。

## 响应

保存后的整条记录，字段同 [list-templates.md](list-templates.md) 的列表项。

## 错误

与 [create-template.md](create-template.md) 相同，另加：

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `模板不存在` | id 不存在或已软删 |

重名检查会排除自己。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 模板管理 | 保存 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 5 | 否 | 可保存 `gender`、`age_bands`。规则与新增相同 | |
| 2026-10-09 | 4 | 是 | 不再接收 `product_library_id`。可只保存 `library_kind` 或 `product_select`，两者都不要求成对 | |
| 2026-10-08 | 3 | 否 | 可保存广告位置、定向、项目预算、商品策略、素材起量、广告状态、抖音号、主图、标题选择模式 | |
| 2026-10-08 | 2 | 是 | 保存时必须带上标准提交字段。快照见 [_history/update-template-v1.md](_history/update-template-v1.md) | |
| 2026-09-29 | 1 | 否 | 初稿 | |
