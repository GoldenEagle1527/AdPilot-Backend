# 契约：create-project

方法：POST  
路径：/api/v1/oceanengine/projects  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

JSON（`extra=forbid`）：`advertiser_id`、`name`、`landing_type`、`marketing_goal`、`ad_type`、`delivery_mode`（只允许 `MANUAL`、`PROCEDURAL`，其它 422）、`subject_id`（int，原样保存）、`template`（object，可选，原样保存）。

`mock=true` 时追加夹具 `PROJECTS`，`project_id` 从 `7000000000000001` 递增，返回该条。`mock=false` 走 `POST /open_api/v3.0/project/create/`。未配 secret：503，`巨量未配置`。

`template` 仍原样落库。提交开放平台时，除 `delivery_range`、`delivery_setting` 外，template 里有则一并带上 `optimize_goal`、`related_product`、`audience`、`micro_promotion_type`。没有这些键就不填。`subject_id` 不传给开放平台。
