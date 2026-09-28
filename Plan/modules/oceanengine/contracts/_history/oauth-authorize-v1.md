# 契约：oauth-authorize

方法：GET  
路径：/api/v1/oceanengine/oauth/authorize  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

Query：`channel` 只允许 `third` 或 `self`，其它 422。不请求开放平台。

`data.authorize_url`：

- third：`https://open.oceanengine.com/audit/oauth.html?app_id=1870857293665690&state={%22agentId%22:%221%22}&material_auth=1&rid=tg29ccnkpzm`
- self：`https://open.oceanengine.com/audit/oauth.html?app_id=1870855836080240&state={%22agentId%22:%221%22,%22agency%22:true}&material_auth=1&rid=c9lb3o12qhm`
