# 契约：update-promotion-status

方法：POST  
路径：/api/v1/oceanengine/promotions/status  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

JSON（`extra=forbid`）：`advertiser_id`、`promotion_ids`（int 列表）、`opt_status`（只允许 `DISABLE`、`ENABLE`）。`DISABLE` 表示暂停。

`mock=true` 时更新夹具 `PROMOTIONS`；没有的 id 先建再改。`data.items` 为 `promotion_id`、`opt_status`。`mock=false` 走 `POST /open_api/v3.0/promotion/status/update/`。未配 secret：503，`巨量未配置`。
