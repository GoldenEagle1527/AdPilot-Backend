# 契约：oauth-callback

方法：GET  
路径：/api/v1/oceanengine/oauth/callback  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

Query：`auth_code`（空则 422）、`state`（可空）。

`mock=true` 时写入夹具：`access_token=mock-access-token`，`refresh_token=mock-refresh-token`，并作为 `data` 返回。`mock=false` 走 `POST /open_api/oauth2/access_token/`。未配 secret：503，`巨量未配置`。
