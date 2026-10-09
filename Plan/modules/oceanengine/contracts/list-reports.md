# 契约：list-reports

方法：GET  
路径：/api/v1/oceanengine/reports  
鉴权：Bearer，菜单节点 `32`  
文档版本：2  
更新日期：2026-10-09

查询：`page`（从 1，默认 1）、`page_size`（默认 20，最大 100）。不传 `page` 返回第一页，不是全表。

`data` 为分页体：`list`、`total`、`page`、`page_size`。列表字段是 `list`，不是 `items`。元素字段不变：

| promotion_id | stat_cost | attribution_micro_game_0d_roi | advertiser_id |
| --- | --- | --- | --- |
| 8001 | 120.0 | 0.3 | 1873916032590219 |
| 8002 | 10.0 | 1.2 | 1873916032590219 |

`mock=true` 时上述两行在第一页。`mock=false` 先走 `GET /open_api/v3.0/report/custom/get/` 再按页读快照。未配 secret：503，`巨量未配置`。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-09 | 2 | 是 | 改为分页。不传 `page` 只返回第一页。`data.items` 改为 `data.list`，并增加 `total`、`page`、`page_size`。快照 [_history/list-reports-v1.md](_history/list-reports-v1.md) | |
| 2026-09-23 | 1 | 否 | 初稿 | |
