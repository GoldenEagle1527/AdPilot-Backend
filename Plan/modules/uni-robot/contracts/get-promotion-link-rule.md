# 契约：get-promotion-link-rule

业务id：uni-robot
文档版本：3
方法：GET
路径：/api/v1/uni-robot/promotion-link-rules/{rule_id}
作用：取一条未删除的按推广链接规则。按剧条件不在这条路径上。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| rule_id | path | integer | 是 | 规则主键 |

## 响应

**LinkRuleItem**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | string | 规则 id，十进制字符串 |
| name | string | 规则名称 |
| template_id | string | 全域批量模板 id。不透明，保存时由目录端口确认 |
| platform_id | string | 剧场平台 id。不透明，保存时由目录端口确认 |
| max_videos_per_series | integer | 每部剧最大视频素材数 |
| schedule_kind | string | 时间调度：`daily` 每天、`cycle` 周期 |
| schedule_hour | integer | 每天触发的小时，0–23。本接口不到点执行 |
| schedule_minute | integer | 每天触发的分钟，0–59。每天开始时间的分钟 |
| schedule_end_hour | integer \| null | 每天结束小时。没填为空 |
| schedule_end_minute | integer \| null | 每天结束分钟。与结束小时成对 |
| cycle_minutes | integer \| null | 周期分钟。选周期时用，如 10、30、60 |
| sort_order | integer | 排序，小的在前。列表按这个升序。旧行为 0 |
| is_enabled | boolean | 开关 |
| created_at | string | 创建时间，北京时间 `+08:00`，精确到秒 |
| updated_at | string | 更新时间，北京时间 `+08:00`，精确到秒 |

不出统计时间、消耗区间、回收率区间。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `规则不存在` | id 不存在、已软删，或这条是按剧条件 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 打开一条按推广链接规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 3 | 否 | 增加 `cycle_minutes`、每天结束时分 | |
| 2026-10-13 | 2 | 否 | 增加 `schedule_kind`、`sort_order` | |
| 2026-09-30 | 1 | 否 | 初稿 | |
