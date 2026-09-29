# 契约：get-task-draft

业务id：standard-delivery
文档版本：1
方法：GET
路径：/api/v1/standard-delivery/task-drafts/{draft_id}
作用：取当前投手自己的一条任务草稿。别人的按不存在。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单 `39` 或 `46` |
| draft_id | path | integer | 是 | 草稿 id |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 草稿 id |
| charge_mode | string | 从模板抄来的 `IAA` / `IAP` |
| template_id | string | 模板 id |
| template_name | string | 模板名称 |
| subject_id | string | 模板上的主体 |
| subject_name | string | 主体名称 |
| bid_panels | string[] | 模板上的出价面板 |
| ads_per_account | integer | 模板上的每账户广告条数 |
| pitcher_user_id | string | 创建人 |
| schedule_start | string \| null | 预约开始。空表示未预约 |
| schedule_end | string \| null | 预约结束 |
| douyin_account_id | string | 唯一的抖音号行 id |
| aweme_id | string | 这个号的 aweme_id。全草稿只有这一个 |
| douyin_name | string | 抖音号名称 |
| series_id | string | 短剧 id |
| book_name | string | 短剧名 |
| accounts | object[] | `advertiser_account_id`、`advertiser_id`（巨量广告主 id）、`name` |
| videos | object[] | `id`、`name` |
| titles | object[] | `id`、`title` |
| placement | string | `aweme` 抖音、`aweme_feed` 抖音加头条、`universal` 通投智能选 |
| project_budget | string | 项目预算，元，两位小数 |
| ad_budget | string | 广告预算，元，两位小数 |
| optimize_goal | string | 免费 `AD_CONVERT_TYPE_ACTIVE`，付费 `AD_CONVERT_TYPE_PAY` |
| product_library_id | string | 商品库行 id |
| library_no | integer | 巨量商品库 id |
| library_name | string | 商品库名称 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有这条草稿所属收费模式的菜单 |
| 404 | `投放草稿不存在` | 不存在、已软删，或不是当前投手的 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 投放任务 | 打开一条草稿 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
