# 契约：create-project

方法：POST  
路径：/api/v1/oceanengine/projects  
鉴权：Bearer，菜单节点 `32`  
文档版本：2  
更新日期：2026-10-12

JSON（`extra=forbid`）：`advertiser_id`、`name`、`landing_type`、`marketing_goal`、`ad_type`、`delivery_mode`（只允许 `MANUAL`、`PROCEDURAL`，其它 422）、`subject_id`（int，原样保存）、`template`（object，可选，原样保存）。

`mock=true` 时追加夹具 `PROJECTS`，`project_id` 从 `7000000000000001` 递增，返回该条。`mock=false` 走 `POST /open_api/v3.0/project/create/`。未配 secret：503，`巨量未配置`。

`template` 仍原样落库。提交开放平台时，除 `delivery_range`、`delivery_setting` 外，template 里有则一并带上 `optimize_goal`、`related_product`、`audience`、`micro_promotion_type`、`aigc_dynamic_creative_switch`。没有这些键就不填。`aigc_dynamic_creative_switch` 是巨量创建项目的 AIGC 动态创意开关，`ON` 开启、`OFF` 关闭（[创建项目](https://open.oceanengine.com/labels/7/docs/1740868093375503)）。巨量要求同时带 `related_product`，行业白名单才生效。`subject_id` 不传给开放平台。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-12 | 2 | 否 | template 里的 `aigc_dynamic_creative_switch` 一并提交开放平台 | |
| 2026-09-23 | 1 | 否 | 初稿 | |
