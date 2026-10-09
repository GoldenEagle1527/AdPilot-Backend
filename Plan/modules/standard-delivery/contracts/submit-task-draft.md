# 契约：submit-task-draft

业务id：standard-delivery
文档版本：4
方法：POST
路径：/api/v1/standard-delivery/task-drafts/{draft_id}/submit
作用：确认提交当前投手自己的一条草稿。按模板切广告，经已装上的客户端建项目、传商品和主图，并把报文放在返回值里。

不调用 `POST /api/v1/oceanengine/projects`。不上传视频。专辑链接只用草稿上的 `album_url`，不把剧场 IAA 推广链抄进 `album_url`。

草稿没写的广告位置、项目预算、广告状态、抖音号，用标准模板上的值。商品库：草稿写了就用草稿；没写且模板有 `library_kind` 时，用当前投手在该账户所属组织、这个类型上的标准库，没有则用该组织这个类型的兜底库。不读模板上的 `product_library_id`。模板没填类型时不另找一个库。用户定向、商品选择方式、产品主图、标题选择模式在模板上。草稿自己的标题列表视为对标题模式的覆盖。模板存了 `img-` 主图时不再新上传。

作者：
状态：draft
更新日期：2026-10-09

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
| image_id | string | 模板上的 `product_image_id`（`img-` 前缀）。模板没有时才是本次图片上传返回的 id |
| project | object | 准备交给创建项目的报文 |
| promotions | array | 这个账户上的广告报文。视频或标题不够一整块时后面的账户可以是空数组 |

`project.delivery_mode` 取模板的 `ocean_delivery_mode`（`MANUAL` 或 `PROCEDURAL`），不写回模板列 `delivery_mode`。`project.audience`：模板 `district=REGION` 且有城市编码时为 `district=REGION` 加 `city`；否则 `district=NONE`，不带城市。`gender` 为 `male` 时带 `GENDER_MALE`，`female` 时带 `GENDER_FEMALE`，`none` 或不填则不带 `gender`。`age_bands` 非空时写成 `age`：`18_23`→`AGE_BETWEEN_18_23`，`24_30`→`AGE_BETWEEN_24_30`，`31_40`→`AGE_BETWEEN_31_40`，`41_49`→`AGE_BETWEEN_41_49`，`50_plus`→`AGE_ABOVE_50`。空数组不带 `age`。`project.delivery_setting.budget` 用草稿项目预算，草稿没写则用模板 `project_budget`。`project.related_product.product_id` 用本次返回的商品 id。商品库用草稿的库；草稿没写则按模板 `library_kind` 解析，不读模板 `product_library_id`。广告 `operation` 用草稿广告开关，草稿没写则用模板 `promotion_operation`。`promotion_materials.playlet_series_url_list` 只用草稿 `album_url`，不把剧场 IAA 推广链抄进去。

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
| 400 | `广告位置不能为空` | 草稿和模板都没有版位 |
| 400 | `项目预算不能为空` | 草稿和模板都没有项目预算 |
| 400 | `广告开关不能为空` | 草稿和模板都没有广告状态 |
| 400 | `抖音号不能为空` | 草稿和模板都没有抖音号 |
| 400 | `模板还不能确认提交` | 模板还缺确认提交要用的字段 |
| 404 | `商品库不存在` | 草稿没写商品库，模板也没填 `library_kind`，或解析出来的库已经没有 |
| 409 | `缺少兜底库` | 模板填了库类型，当前投手在该账户组织上没有这个类型的标准库，该组织也没有这个类型的兜底库 |
| 503 | `图片上传接口未定` | 装的是真客户端，主图上传仍未接 |

手动投放视频数超限、标题长度不对时，整单失败，不截断，也不先建项目。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 投放任务 | 确认提交 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 4 | 否 | 项目 `audience` 在非不限时带上模板的性别和年龄。不限则省略 `gender`、`age` | |
| 2026-10-09 | 3 | 是 | 草稿没写商品库时按模板 `library_kind` 解析投手标准库或组织兜底库。不再读模板 `product_library_id`。类型为空时不另选库。专辑链接仍只用草稿 | |
| 2026-10-08 | 2 | 否 | 草稿未覆盖时读取模板的广告位置、定向、项目预算、商品库、广告状态、抖音号、主图。有 `img-` 主图则不再上传。专辑链接仍只用草稿 | |
| 2026-10-08 | 1 | 否 | 初稿 | |
