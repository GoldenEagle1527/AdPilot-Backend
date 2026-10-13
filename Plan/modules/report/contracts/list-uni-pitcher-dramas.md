# 契约：list-uni-pitcher-dramas

业务id：report
文档版本：2
方法：GET
路径：/api/v1/reports/uni/pitcher-dramas
作用：漫剧全域短剧报表 tab2「投手短剧收益」。一个投手一部剧一天一行，只看自己。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

与 [list-uni-dramas.md](list-uni-dramas.md) 相同，菜单 13。

- 行键：（`pitcher_user_id`，`series_id`，`stat_time_day`）。
- 指标只算该投手自己的全域项目（`uni_native_task.pitcher_user_id`）。同一部剧同一天两个投手出两行。
- 当前用户只看到投手是自己的行。
- 日期既是筛选（区间），也是列 `stat_time_day`。

## 响应

`data`：`list` / `total` / `page` / `page_size` / `summary`。`summary` 同 [list-uni-dramas.md](list-uni-dramas.md)「全域指标」，按本接口可见的行合计。

`list` 每一项：[list-uni-dramas.md](list-uni-dramas.md) 的行字段（`series_id`、`book_name`、`platform_name`、`stat_time_day`、全域指标），另加：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| pitcher_user_id | integer | 投手用户 id |
| pitcher_name | string | 投手姓名，单个，不拼接 |

`new_project_count` 是该投手当天在这部剧上存下的全域项目数。

## 错误

同 [list-uni-dramas.md](list-uni-dramas.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 漫剧全域报表 / 短剧报表 tab2 | 列表、排序、顶部汇总 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 2 | 是 | 行粒度改为一个投手一部剧一天一行；去掉 `pitchers`，改为单个 `pitcher_user_id`、`pitcher_name`，加 `stat_time_day`；只看自己。v1 快照见 `_history/list-uni-pitcher-dramas-v1.md` | |
| 2026-10-13 | 1 | 否 | 初稿 | |
