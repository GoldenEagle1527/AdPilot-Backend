# 契约：submit-task-draft

业务id：standard-delivery
文档版本：1
方法：POST
路径：/api/v1/standard-delivery/task-drafts/{draft_id}/submit
作用：确认提交当前投手自己的一条草稿。按模板切广告，经已装上的客户端建项目、传商品和主图，并把报文放在返回值里。

不调用 `POST /api/v1/oceanengine/projects`。不上传视频。专辑链接只用草稿上的 `album_url`。地域不限，不传城市，不落库。

作者：
状态：draft
更新日期：2026-10-08

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单随草稿收费模式：免费 `39`，付费 `46` |
| draft_id | path | integer | 是 | 当前投手自己的未删除草稿 |

没有请求体。

## 响应

`data.id` 是草稿 id。`data.aweme_id` 是这条草稿唯一的标准抖音号。`data.accounts` 按草稿里的账户顺序，每项含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| advertiser_id | integer | 巨量广告主 id |
| project_id | integer | 客户端 `create_project` 返回的项目 id |
| product_id | integer | 客户端商品上传返回的商品 id |
| image_id | string | 客户端图片上传返回的主图 id |
| project | object | 准备交给创建项目的报文 |
| promotions | array | 这个账户上的广告报文。视频或标题不够一整块时后面的账户可以是空数组 |

`project.delivery_mode` 取模板的 `ocean_delivery_mode`（`MANUAL` 或 `PROCEDURAL`），不写回模板列 `delivery_mode`。`project.audience` 只有 `district=NONE`。`project.related_product.product_id` 用本次返回的商品 id。

`promotions[].project_id` 用本账户刚返回的项目 id。`promotion_materials.playlet_series_url_list` 只有草稿的 `album_url` 一条。视频素材带素材库 `material_id`，没有巨量视频号时不补 `video_id`。手动投放且模板有 `roi_goal` 时，ROI 在广告上；付费自动投放时 ROI 在项目的 `delivery_setting.roi_goal`。标准行不读 `roi_coefficient`。

视频、标题按草稿保存顺序切。每条广告取 `videos_per_ad` 个视频、`titles_per_ad` 个标题。每个账户最多 `ads_per_account` 条。切完就停，不回头再取。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有草稿所属收费模式的菜单 |
| 404 | `投放草稿不存在` | 草稿不存在、已软删，或不是当前投手的 |
| 400 | `手动投放每个广告最多 10 个视频` | `ocean_delivery_mode=MANUAL` 且 `videos_per_ad` 大于 10 |
| 400 | `标题长度须为 5–30 个字` | 切进广告的标题有一条不在 5–30 个字 |
| 400 | `专辑链接不能为空` | 草稿没有 `album_url` |
| 400 | `模板还不能确认提交` | 模板还缺确认提交要用的字段 |
| 404 | `商品库不存在` | 草稿上的商品库已经没有 |
| 503 | `图片上传接口未定` | 装的是真客户端，主图上传仍未接 |

手动投放视频数超限、标题长度不对时，整单失败，不截断，也不先建项目。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 投放任务 | 确认提交 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-08 | 1 | 否 | 初稿 | |
