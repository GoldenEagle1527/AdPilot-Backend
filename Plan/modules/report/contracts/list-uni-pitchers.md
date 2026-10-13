# 契约：list-uni-pitchers

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/uni/pitchers
作用：漫剧全域投手报表。一个投手一天一行，只看自己。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | 要菜单 14 |
| page、page_size、date_start、date_end、sort_by、sort_order | query | | 否 | 同 [list-uni-dramas.md](list-uni-dramas.md)。日期是区间，默认今天 |

`series_name` 收但不生效。

当前用户只看到自己（`uni_native_task.pitcher_user_id` 等于自己）的行。

## 响应

`data`：`list` / `total` / `page` / `page_size` / `summary`。`summary` 同 [list-uni-dramas.md](list-uni-dramas.md)「全域指标」。

`list` 每一项：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| pitcher_user_id | integer | 投手用户 id。时速弹框用 |
| pitcher_name | string | 投手姓名 |
| stat_time_day | string | `YYYY-MM-DD`，北京时间 |
| （全域指标） | | 同 [list-uni-dramas.md](list-uni-dramas.md)。`new_project_count` 是当天该投手存下的全域项目数 |
| new_drama_count | integer | 新建新剧数，恒为 0 |

只有当天有快照数据或新建项目的日期才出行。

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 无菜单 14 | 403 | |
| 起日晚于止日、排序字段不支持 | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 漫剧全域报表 / 投手报表 | 列表、排序、顶部汇总 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
