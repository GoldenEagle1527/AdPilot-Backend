# 契约：list-uni-groups

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/uni/groups
作用：漫剧全域组报表。一个部门一天一行。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | 要菜单 15 |
| page、page_size、date_start、date_end、sort_by、sort_order | query | | 否 | 同 [list-uni-dramas.md](list-uni-dramas.md)。日期是区间，默认今天 |

`series_name` 收但不生效。

可见部门 = 当前用户的数据范围（勾选部门，含下级）；数据范围为空（仅本人）时只看自己所在部门。

每个投手自己的全域项目只计入该投手当前所在部门（`users.department_id`）。一部剧的投手分属两个部门时，各自的消耗只进各自部门，不把整部剧合计复制到每个部门。对不上中台任务的巨量项目不计入任何部门。

## 响应

`data`：`list` / `total` / `page` / `page_size` / `summary`。`summary` 同 [list-uni-dramas.md](list-uni-dramas.md)「全域指标」。

`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| department_id | integer | 部门 id。时速弹框用 |
| department_name | string | 部门名 |
| stat_time_day | string | `YYYY-MM-DD`，北京时间 |
| （全域指标） | | 同 [list-uni-dramas.md](list-uni-dramas.md)。`new_project_count` 是当天该部门投手存下的全域项目数 |
| new_drama_count | integer | 新建新剧数，恒为 0 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 15 | 403 | |
| 起日晚于止日、排序字段不支持 | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 漫剧全域报表 / 组报表 | 列表、排序、顶部汇总 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
