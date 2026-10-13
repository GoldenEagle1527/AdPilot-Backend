# 契约：submit-task

业务id：uni-native-task
文档版本：3
方法：POST
路径：/api/v1/uni-native-tasks/{task_id}/submit
作用：确认提交当前投手自己的一条端原生任务。每个账户行一个抖音号、一个项目、一条广告。假客户端执行期间状态为 `running`（执行中），结束后为 `done`（完成）。`materials_uploaded` 仍是 false，不表示巨量已经收下素材。

作者：
状态：draft
更新日期：2026-10-12

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可 |
| task_id | path | integer | 是 | 当前投手自己的未删除任务 |

没有请求体。

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 任务 id |
| status | string | 提交过程中为 `running`（执行中），假客户端结束后为 `done`（完成）。不是巨量真上传 |
| executed_at | string \| null | 假客户端结束的北京时间。未跑完为空 |
| materials_uploaded | boolean | 固定 `false`。这次不上传视频 |
| promotion_links | array | 任务上已保存的推广链。`link_text` 不写入 `playlet_series_url_list` |
| accounts | array | 与任务账户行一一对应 |

`accounts[]` 含 `douyin_account_id`、`aweme_id`、`advertiser_id`、`project_id`、`product_id`、`image_id`、`project`、`promotions`。`promotions` 只有一条。`project_id`、`product_id`、`image_id` 来自已装上的客户端。视频素材只带素材库 `material_id`。没有巨量视频号时不补 `video_id`。

`project.delivery_mode` 取模板 `ocean_delivery_mode`。不写回模板列 `delivery_mode`。`project.audience` 只有 `district=NONE`，`project.delivery_range` 仍是 `UNIVERSAL_SMART`。

`project.delivery_setting` 有 `budget_mode=BUDGET_MODE_DAY`、`budget`（任务项目预算）、`roi_goal`（任务 ROI 系数）。模板存了投放时间时带 `schedule_type`（`SCHEDULE_FROM_NOW` 或 `SCHEDULE_START_END`）；选了起止时再带 `start_time`、`end_time`（`yyyy-MM-dd`）。模板 `schedule_time` 有值时带上这串 336 位 `0/1`，不限时不带。不带 `deep_bid_type`。

`project.aigc_dynamic_creative_switch`：模板 `aigc_dynamic_creative` 为真时 `ON`，否则 `OFF`。

`promotions[].promotion_materials.product_info` 有 `image_ids`、`selling_points`（模板产品卖点）。模板填了 `product_name` 时带 `titles`（只有这一个名称）；没填就不带，不用剧名代替。`promotion_materials.call_to_action_buttons` 是模板行动号召。广告不带 `source`。上传商品时的书名仍用剧名。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 404 | `投放任务不存在` | 任务不存在、已软删，或不是当前投手的 |
| 404 | `模板不存在` | 全域模板已经没有 |
| 404 | `商品库不存在` | 当前投手没有已分配的商品库，也没有兜底库 |
| 400 | `短剧库不存在` | 当前库没有 `manhua_series` |
| 400 | `标题长度须为 5–30 个字` | 标题库标题或临时标题有一条不在 5–30 个字 |
| 503 | `图片上传接口未定` | 装的是真客户端，主图上传仍未接 |

标题长度不对时整单失败，不调用客户端。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧全域投放 / 端原生投放任务 | 确认提交 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-12 | 3 | 否 | 项目报文带模板排期、时段和 AIGC 动态创意开关；广告报文带模板产品名称、卖点和行动号召 | |
| 2026-10-09 | 2 | 是 | 假客户端执行中为 `running`，结束后为 `done` 并写 `executed_at`。`materials_uploaded` 仍为 false | |
| 2026-10-08 | 1 | 否 | 初稿 | |
