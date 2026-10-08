# 契约：create-task-draft

业务id：standard-delivery
文档版本：1
方法：POST
路径：/api/v1/standard-delivery/task-drafts
作用：新增一条投放任务草稿。只落本系统字段，不调用创建项目或创建单元。

一次草稿只有一个抖音号。`advertiser_ids` 里的多个账户共用这一个 `aweme_id`。抖音号不按投手过滤，只要求已启用的标准号。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单随模板的收费模式：免费 `39`，付费 `46` |
| template_id | body | integer | 是 | 未删除的模板。收费模式从模板抄到草稿上 |
| schedule_start | body | string \| null | 否 | 预约开始。与结束同时空或同时有值。无时区按北京时间 |
| schedule_end | body | string \| null | 否 | 预约结束，须晚于开始 |
| advertiser_ids | body | integer[] | 是 | 巨量广告主 id，与账户列表的 `account_id` 相同。1–100 个，不重复。须是当前投手名下 `sync_status=active` 且未删除的户 |
| douyin_account_id | body | integer | 是 | 一个 `douyin_account.id`。须 `delivery_mode=standard` 且 `enabled=true`。传数组会 422 |
| series_id | body | integer | 是 | 一部 `manhua_series.id` |
| video_ids | body | integer[] | 是 | `material_videos.id`，1–200 个，不重复。须属于这部短剧，且当前用户能看见 |
| title_ids | body | integer[] | 是 | `material_titles.id`，1–100 个，不重复。只收当前用户自己上传的 |
| placement | body | string | 是 | `aweme`、`aweme_feed`、`universal` |
| project_budget | body | number | 是 | 项目预算，元，大于 0，最多两位小数 |
| ad_budget | body | number | 是 | 广告预算，元，大于 0，最多两位小数 |
| optimize_goal | body | string | 是 | 免费只能 `AD_CONVERT_TYPE_ACTIVE`，付费只能 `AD_CONVERT_TYPE_PAY` |
| library_no | body | integer | 是 | `product_library.library_no`。标准库须已分给当前投手；兜底库可用 |

不收推广链、产品主图、卖点、行动号召、事件资产、地域、巨量商品 id、巨量视频 id。多传返回 422。

## 响应

新建后的整条记录，字段同 [get-task-draft.md](get-task-draft.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有模板所属收费模式的菜单 |
| 404 | `模板不存在` | 模板不存在或已软删 |
| 404 | `短剧不存在` | 短剧不存在或已软删 |
| 404 | `商品库不存在` | `library_no` 没有未删除的库 |
| 400 | `抖音号不是已启用的标准号` | 号不存在、未启用，或不是标准号 |
| 400 | `优化目标与模板收费模式不一致` | 目标和 IAA/IAP 对不上 |
| 400 | `账户不存在、未分配给当前投手或已失效` | 有账户不在当前投手的有效户里 |
| 400 | `视频不存在、不属于该短剧或当前账号不可见` | 视频校验失败 |
| 400 | `标题不存在或不属于当前账号` | 标题不是自己的或已删 |
| 400 | `商品库未分配给当前投手` | 标准库没分给当前用户 |
| 422 | `douyin_account_id: ...` | 抖音号传了数组、列表重复、预约只填了一边、金额不合法 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 投放任务 | 保存草稿。确认提交不走这个接口 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
