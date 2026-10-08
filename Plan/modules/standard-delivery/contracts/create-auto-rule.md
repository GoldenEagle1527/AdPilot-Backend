# 契约：create-auto-rule

业务id：standard-delivery
文档版本：1
方法：POST
路径：/api/v1/standard-delivery/auto-rules
作用：新增一条自动投放规则。只保存筛选条件和模板，不到点执行，也不调巨量。

作者：
状态：draft
更新日期：2026-09-29

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。菜单随模板的收费模式：免费 `51`，付费 `52` |
| name | body | string | 是 | 规则名称，1–128 字。同一投手、同一收费模式下不重名 |
| template_id | body | integer | 是 | 未删除的模板。收费模式从模板抄来 |
| accounts_per_series | body | integer | 否 | 每部剧账户数，1–100，默认 3 |
| max_videos_per_series | body | integer | 否 | 每部剧最大视频数，1–500，默认 200 |
| schedule_start | body | string \| null | 否 | 预约开始。与结束成对。都不传表示未预约 |
| schedule_end | body | string \| null | 否 | 预约结束，须晚于开始 |
| cost_min | body | number \| null | 否 | 消耗下限，元。与上限成对，空表示不限 |
| cost_max | body | number \| null | 否 | 消耗上限，元 |
| roi_min | body | number \| null | 否 | 回收率下限。与上限成对 |
| roi_max | body | number \| null | 否 | 回收率上限 |
| publish_start | body | string \| null | 否 | 上架日期下限 `YYYY-MM-DD`。与上限成对。对的是短剧库上架时间，不是报表时间 |
| publish_end | body | string \| null | 否 | 上架日期上限 |
| no_bid_only | body | boolean | 否 | 默认 false。真则记下「只针对最大转化」 |
| series_ids | body | integer[] | 是 | `manhua_series.id`，1–100 个，不重复 |

不收剧场。多传返回 422。

## 响应

新建后的整条记录，字段同 [get-auto-rule.md](get-auto-rule.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 401 | `未带或 Token 无效` | 未登录 |
| 403 | `已登录但无对应菜单或组件` | 没有模板所属收费模式的菜单 |
| 404 | `模板不存在` | 模板不存在或已软删 |
| 404 | `短剧不存在` | 有短剧 id 不存在或已软删 |
| 409 | `规则名称已存在` | 同一投手、同一收费模式下重名 |
| 422 | `series_ids: ...` | 短剧重复、范围只填了一边、数字越界、多传字段 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 自动投放 | 保存规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-29 | 1 | 否 | 初稿 | |
