# 契约：auto-pause

方法：POST  
路径：/api/v1/oceanengine/auto-pause/run  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

JSON（`extra=forbid`）：`metric`（`stat_cost` 或 `roi`）、`operator`（只允许 `lte`）、`threshold`（float）。

用报表夹具判断，运算符只有小于等于：指标值 `<= threshold` 则把对应广告 `opt_status` 设为 `DISABLE`。`stat_cost` 比 `stat_cost`，`roi` 比 `attribution_micro_game_0d_roi`。默认夹具下，`metric=stat_cost` 且阈值 100 时 `paused` 为 `[8002]`、`kept` 为 `[8001]`；`metric=roi` 且阈值 0.5 时 `paused` 为 `[8001]`、`kept` 为 `[8002]`。

`data.paused` 为命中的 `promotion_id` 列表，`data.kept` 为未命中。`mock=false` 先拉自定义报表再调状态更新。未配 secret：503，`巨量未配置`。
