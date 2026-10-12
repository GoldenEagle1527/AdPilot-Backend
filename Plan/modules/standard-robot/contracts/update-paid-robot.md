# 契约：update-paid-robot

业务id：standard-robot
文档版本：1
方法：PUT
路径：/api/v1/standard-native-robots/paid/{rule_id}
作用：整表保存当前投手自己的一条付费机器人。不到点执行。

作者：
状态：draft
更新日期：2026-10-10

## 请求

菜单 `77`。Body 同 [create-paid-robot.md](create-paid-robot.md)。

## 响应

字段同免费列表项，`charge_mode` 为 `IAP`。

## 错误

创建接口的 400/404 同样适用。免费规则、别人的规则、已删规则返回 404 `规则不存在`。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| (付费)漫剧端原生机器人 | 修改 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-10 | 1 | 否 | 初稿 | |
