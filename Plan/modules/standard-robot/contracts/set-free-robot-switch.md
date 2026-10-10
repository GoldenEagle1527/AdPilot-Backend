# 契约：set-free-robot-switch

业务id：standard-robot
文档版本：1
方法：PATCH
路径：/api/v1/standard-native-robots/free/{rule_id}/switch
作用：只改当前投手自己的免费机器人开关。不改其它字段，也不在这次请求里提交投放。关掉后到点循环跳过。

作者：
状态：draft
更新日期：2026-10-10

## 请求

菜单 `76`。

| 字段 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| rule_id | path | integer | 是 | 自己的免费规则 |
| is_enabled | body | boolean | 是 | true 开启、false 关闭 |

多传 422。

## 响应

字段同 [list-free-robots.md](list-free-robots.md) 的列表项。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `规则不存在` | 没有、已软删、不是当前投手、或是付费规则 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| (免费)漫剧端原生机器人 | 行内开关 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-10 | 1 | 否 | 初稿 | |
