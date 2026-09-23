# 契约：list-advertisers

方法：GET  
路径：/api/v1/oceanengine/advertisers  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

Query：`page`（从 1，默认 1）、`page_size`（默认 20，上限 100）、可选 `account_name` 模糊、`account_id` 精确。

分页体：`list` / `total` / `page` / `page_size`。`mock=true` 时 list 为夹具一条。

| 字段 | 类型 | mock |
| --- | --- | --- |
| account_id | int | 1873916032590219 |
| account_name | string | 番茄漫剧测试户 |
| valid_balance | float | 100.5（元） |
| adv_company_name | string | 番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2 |
| organization_id | int | 1872115109920903 |

成功只用 `success()`。`mock=false` 且未配 secret：503，`巨量未配置`。
