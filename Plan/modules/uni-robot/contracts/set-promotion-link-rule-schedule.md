# 契约：set-promotion-link-rule-schedule

业务id：uni-robot
文档版本：1
方法：PATCH
路径：/api/v1/uni-robot/promotion-link-rules/{rule_id}/schedule
作用：只改一条按推广链接规则每天触发的小时和分钟。不到点执行，也不改开关。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| rule_id | path | integer | 是 | 规则主键 |
| schedule_hour | body | integer | 是 | 每天触发的小时，0–23 |
| schedule_minute | body | integer | 是 | 每天触发的分钟，0–59 |

两个都要传。多传开关或名称返回 422。不问目录。

示例：

```json
{ "schedule_hour": 9, "schedule_minute": 30 }
```

## 响应

改后的整条记录，字段同 [get-promotion-link-rule.md](get-promotion-link-rule.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `规则不存在` | id 不存在、已软删，或这条是按剧条件 |
| 422 | `schedule_minute: Field required` | 时分缺一个、越界，或多传字段 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 改每天触发时分 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
