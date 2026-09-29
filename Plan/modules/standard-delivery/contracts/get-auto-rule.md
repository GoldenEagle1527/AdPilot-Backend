# 契约：get-auto-rule

业务id：standard-delivery
文档版本：1
方法：GET
路径：/api/v1/standard-delivery/auto-rules/{rule_id}
作用：取当前投手自己的一条自动规则。别人的按不存在。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单 `51` 或 `52` |
| rule_id | path | integer | 是 | 规则 id |

## 响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 规则 id |
| name | string | 规则名称 |
| charge_mode | string | 从模板抄来的 `IAA` / `IAP` |
| template_id | string | 模板 id |
| template_name | string | 模板名称 |
| ads_per_account | integer | 模板上的每账户广告条数 |
| pitcher_user_id | string | 创建人 |
| accounts_per_series | integer | 每部剧账户数 |
| max_videos_per_series | integer | 每部剧最大视频数。本轮只保存，不截取素材 |
| schedule_start | string \| null | 预约开始。空表示未预约 |
| schedule_end | string \| null | 预约结束 |
| cost_min | string \| null | 消耗下限，元。空表示不限 |
| cost_max | string \| null | 消耗上限，元 |
| roi_min | string \| null | 回收率下限。空表示不限 |
| roi_max | string \| null | 回收率上限 |
| publish_start | string \| null | 上架日期下限 `YYYY-MM-DD` |
| publish_end | string \| null | 上架日期上限 |
| no_bid_only | boolean | 真则只针对最大转化。本轮不拉报表 |
| series | object[] | `id`、`book_name` |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

剧场不在出参里。短剧表没有剧场外键。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有这条规则所属收费模式的菜单 |
| 404 | `自动规则不存在` | 不存在、已软删，或不是当前投手的 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 自动投放 | 打开一条规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
