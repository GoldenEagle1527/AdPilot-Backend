# 契约：upload-product

方法：POST  
路径：/api/v1/oceanengine/product-libraries/{library_id}/products  
鉴权：Bearer，菜单节点 `32`  
文档版本：1  
更新日期：2026-09-23

JSON（`extra=forbid`）：`drama_name`、`file_url`。`library_id` 原样回显。

`mock=true` 时追加夹具 `PRODUCTS`，`product_id` 从 `9001` 起，返回该条。开放平台 path 未定：`mock=false` 且已配 secret 时 503，`商品库上传接口未定`；未配 secret 时 503，`巨量未配置`。客户端不发起请求。
