# 契约：update-drama-rule

业务id：uni-robot
文档版本：1
方法：PUT
路径：/api/v1/uni-robot/drama-rules/{rule_id}
作用：整表保存一条按剧条件规则。统计时间和两个区间一并改写。不到点执行。

作者：
状态：draft
更新日期：2026-09-30

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `Bearer <token>`。登录即可，不校验菜单 |
| rule_id | path | integer | 是 | 规则主键 |
| name | body | string | 是 | 同 [create-drama-rule.md](create-drama-rule.md)。自己原来的名字不算重名 |
| template_id | body | integer | 是 | 再次经目录端口确认 |
| platform_id | body | integer | 是 | 再次经目录端口确认 |
| max_videos_per_series | body | integer | 否 | 默认 800 |
| schedule_hour | body | integer | 是 | 0–23 |
| schedule_minute | body | integer | 是 | 0–59 |
| is_enabled | body | boolean | 否 | 默认 false |
| stat_span | body | string | 是 | `today` 或 `yesterday` |
| cost_min | body | number | 是 | 消耗下限，单位元 |
| cost_max | body | number | 是 | 消耗上限，单位元 |
| recovery_min | body | number | 是 | 回收率下限，百分比数值 |
| recovery_max | body | number | 是 | 回收率上限，百分比数值 |

这是整表替换，不是补丁。缺区间或多传字段返回 422。规则类型不能改成按推广链接。

## 响应

保存后的整条记录，字段同 [get-drama-rule.md](get-drama-rule.md)。

## 错误

| HTTP | message 示例 | 何时 |
| --- | --- | --- |
| 400 | `全域模板不存在` | 目录里没有这个模板 id。此时不写库，也不再问平台 |
| 400 | `剧场平台不存在` | 目录里没有这个平台 id |
| 404 | `规则不存在` | id 不存在、已软删，或这条是按推广链接 |
| 409 | `规则名称已存在` | 别的未删除按剧条件规则已用这个名称 |
| 422 | `recovery_max: Field required` | 缺必填、区间颠倒、时分越界、多传字段 |
| 503 | `全域目录尚未接入` | 进程没有注入目录实现 |

其余共用错误见 [说明.md](说明.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 全域自动投放策略 / 漫剧机器人 | 整表保存按剧条件规则 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-30 | 1 | 否 | 初稿 | |
