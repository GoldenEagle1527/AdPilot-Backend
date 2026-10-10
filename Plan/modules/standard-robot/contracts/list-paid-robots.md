# 契约：list-paid-robots

业务id：standard-robot
文档版本：1
方法：GET
路径：/api/v1/standard-native-robots/paid
作用：分页列出当前登录投手自己的付费（IAP）漫剧端原生机器人。不执行。

作者：
状态：draft
更新日期：2026-10-10

## 请求

同 [list-free-robots.md](list-free-robots.md)，菜单改为 `77`。结果只含 `charge_mode=IAP`。

## 响应

同免费列表。`charge_mode` 为 `IAP`。

## 错误

同免费列表，403 对应没有菜单 77。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 标准自动投放策略 / (付费)漫剧端原生机器人 | 列表 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-10 | 1 | 否 | 初稿 | |
