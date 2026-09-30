# 契约：create-promotion-link-rule

业务id：uni-robot
文档版本：2
方法：POST
路径：/api/v1/uni-robot/promotion-link-rules
作用：新增一条按推广链接规则。只保存，不创建任务，也不到点执行。剧条件列留空。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| name | body | string | 是 | 规则名称，去首尾空白，1–128 字。同一类型未删除规则内不重名 |
| template_id | body | integer | 是 | 全域模板 id，≥ 1。线上查未删除的 `delivery_template.delivery_mode=uni`，命中后原样保存 |
| platform_id | body | integer | 是 | 剧场平台 id，≥ 1。线上还没有剧场来源，任何 id 都 400，不写假平台 |
| max_videos_per_series | body | integer | 否 | 每部剧最大视频素材数，1–10000，默认 800 |
| schedule_hour | body | integer | 是 | 每天触发的小时，0–23 |
| schedule_minute | body | integer | 是 | 每天触发的分钟，0–59 |
| is_enabled | body | boolean | 否 | 开关，默认 false |

不收统计时间、消耗区间、回收率区间。多传返回 422。

线上目录已接入。模板没有命中时不再问平台。

## 响应

新建后的整条记录，字段同 [get-promotion-link-rule.md](get-promotion-link-rule.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 400 | `全域模板不存在` | 没有这条未删除的全域模板。此时不再问平台 |
| 400 | `剧场平台不存在` | 线上没有剧场来源，任何平台 id 都拒绝，且不查三方剧场表 |
| 409 | `规则名称已存在` | 未删除的按推广链接规则已有这个名称 |
| 422 | `stat_span: ...` | 多传剧条件字段、时分越界、名称为空 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 保存按推广链接规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 2 | 否 | 线上目录已接入：模板查全域模板表，平台没有来源时 400。去掉 503 | |
| 2026-09-30 | 1 | 否 | 初稿 | |
