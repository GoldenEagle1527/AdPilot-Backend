# 契约：list-reports

方法：GET  
路径：/api/v1/oceanengine/reports  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

不分页。`data.items`。`mock=true` 时两条，`advertiser_id=1873916032590219`：

| promotion_id | stat_cost | attribution_micro_game_0d_roi |
| --- | --- | --- |
| 8001 | 120.0 | 0.3 |
| 8002 | 10.0 | 1.2 |

`mock=false` 走 `GET /open_api/v3.0/report/custom/get/`。未配 secret：503，`巨量未配置`。
