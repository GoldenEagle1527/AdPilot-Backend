# 契约：update-promotion-link-rule

业务id：uni-robot
文档版本：2
方法：PUT
路径：/api/v1/uni-robot/promotion-link-rules/{rule_id}
作用：整表保存一条按推广链接规则。条件列保持为空。不到点执行。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| rule_id | path | integer | 是 | 规则主键 |
| name | body | string | 是 | 同 [create-promotion-link-rule.md](create-promotion-link-rule.md)。自己原来的名字不算重名 |
| template_id | body | integer | 是 | 再次确认未删除的全域模板。没有则不写库，也不再问平台 |
| platform_id | body | integer | 是 | 线上还没有剧场来源，任何 id 都 400，不写假平台 |
| max_videos_per_series | body | integer | 否 | 默认 800 |
| schedule_hour | body | integer | 是 | 0–23 |
| schedule_minute | body | integer | 是 | 0–59 |
| is_enabled | body | boolean | 否 | 默认 false |

这是整表替换，不是补丁。多传剧条件字段返回 422。规则类型不能改成按剧条件。

## 响应

保存后的整条记录，字段同 [get-promotion-link-rule.md](get-promotion-link-rule.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 400 | `全域模板不存在` | 没有这条未删除的全域模板。此时不写库，也不再问平台 |
| 400 | `剧场平台不存在` | 线上没有剧场来源，任何平台 id 都拒绝，且不查三方剧场表 |
| 404 | `规则不存在` | id 不存在、已软删，或这条是按剧条件 |
| 409 | `规则名称已存在` | 别的未删除按推广链接规则已用这个名称 |
| 422 | `name: Field required` | 缺必填、时分越界、多传字段 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 整表保存按推广链接规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 2 | 否 | 线上目录已接入：模板查全域模板表，平台没有来源时 400。去掉 503 | |
| 2026-09-30 | 1 | 否 | 初稿 | |
