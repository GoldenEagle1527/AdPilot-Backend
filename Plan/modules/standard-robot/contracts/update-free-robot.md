# 契约：update-free-robot

业务id：standard-robot
文档版本：1
方法：PUT
路径：/api/v1/standard-native-robots/free/{rule_id}
作用：整表保存当前投手自己的一条免费机器人。不到点执行。收费模式和所属投手不变。

作者：
状态：draft
更新日期：2026-10-10

## 请求

菜单 `76`。`rule_id` 为路径整数。Body 同 [create-free-robot.md](create-free-robot.md)。

## 响应

字段同 [list-free-robots.md](list-free-robots.md) 的列表项。

## 错误

创建接口的 400/404 同样适用。另外：

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 404 | `规则不存在` | 没有、已软删、不是当前投手、或是付费规则 |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| (免费)漫剧端原生机器人 | 修改 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-10 | 1 | 否 | 初稿 | |
