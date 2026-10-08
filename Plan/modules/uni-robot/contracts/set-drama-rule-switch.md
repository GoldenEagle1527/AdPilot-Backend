# 契约：set-drama-rule-switch

业务id：uni-robot
文档版本：1
方法：PATCH
路径：/api/v1/uni-robot/drama-rules/{rule_id}/switch
作用：只改一条按剧条件规则的开关。不改每天的时分，也不创建任务。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| rule_id | path | integer | 是 | 规则主键 |
| is_enabled | body | boolean | 是 | 开关：`true` 开启、`false` 关闭 |

body 只收 `is_enabled`。多传名称、时分、区间等返回 422。不问目录。

示例：

```json
{ "is_enabled": true }
```

## 响应

改后的整条记录，字段同 [get-drama-rule.md](get-drama-rule.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `规则不存在` | id 不存在、已软删，或这条是按推广链接 |
| 422 | `is_enabled: Field required` | 没传 `is_enabled`、不是布尔，或多传字段 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 行内开关 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
