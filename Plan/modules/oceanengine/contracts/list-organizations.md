# 契约：list-organizations

方法：GET  
路径：/api/v1/oceanengine/organizations  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

不分页。`mock=true` 时 `data.items` 为夹具一条。

| 字段 | 类型 | mock |
| --- | --- | --- |
| advertiser_id | int | 1872115109920903 |
| advertiser_name | string | 深圳发行中心 |
| account_role | string | CUSTOMER_ADMIN |
| ocean_version | string | 升级版组织 |

成功：`success({"items": [...]})`。`mock=false` 且未配 secret：503，`巨量未配置`。
