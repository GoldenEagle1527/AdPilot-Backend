# 契约：auto-pause

方法：POST  
路径：/api/v1/oceanengine/auto-pause/run  
鉴权：Bearer，菜单节点 `32`  
文档版本：2  
更新日期：2026-10-09

JSON（`extra=forbid`）：`metric`（`stat_cost` 或 `roi`）、`operator`（只允许 `lte`）、`threshold`（float）。

查询：`page`（从 1，默认 1）、`page_size`（默认 20，最大 100）。关停仍按整份报表快照执行。返回的 `paused` 和 `kept` 按同一页截取。不传 `page` 时两个列表都是第一页。

用报表夹具判断，运算符只有小于等于：指标值 `<= threshold` 则把对应广告 `opt_status` 设为 `DISABLE`。`stat_cost` 比 `stat_cost`，`roi` 比 `attribution_micro_game_0d_roi`。默认夹具下，`metric=stat_cost` 且阈值 100 时全量 `paused` 为 `[8002]`、`kept` 为 `[8001]`；`metric=roi` 且阈值 0.5 时全量 `paused` 为 `[8001]`、`kept` 为 `[8002]`。这两条都在第一页。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| paused | int[] | 本页命中的 `promotion_id` |
| kept | int[] | 本页未命中的 `promotion_id` |
| paused_total | int | 命中总数，不是本页条数 |
| kept_total | int | 未命中总数 |
| page | int | 与查询相同 |
| page_size | int | 与查询相同 |

`mock=false` 先拉自定义报表再调状态更新。未配 secret：503，`巨量未配置`。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 2 | 是 | 关停仍跑全量。`paused`、`kept` 改为按 `page` / `page_size` 返回第一页起的一页，并增加 `paused_total`、`kept_total`、`page`、`page_size`。快照 [_history/auto-pause-v1.md](_history/auto-pause-v1.md) | |
| 2026-09-23 | 1 | 否 | 初稿 | |
