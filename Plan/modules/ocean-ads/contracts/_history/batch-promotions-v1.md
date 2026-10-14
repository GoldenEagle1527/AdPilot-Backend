# 巨量广告广告批量改状态

`POST /api/v1/ocean-ads/promotions/batch`

要有菜单 34。只改当前登录人数据范围内、还没删除的广告。看不了的广告 id 不报错，也不出现在返回里。传 1 个广告 id 就是列表上的单个开关，传多个就是批量。不改所属项目。

正文：

- `promotion_ids`：广告 id，即 `oe_promotion.promotion_id`，1 到 100 个
- `action`：`开启`、`暂停`、`删除`

开启、暂停会通知巨量：`POST /open_api/v3.0/promotion/status/update/`，`opt_status` 为 `ENABLE` 或 `DISABLE`，一次最多 10 条。巨量返回成功的才改本库 `opt_status`。有失败项时，成功的已写入，接口返回 502。

删除不通知巨量。`oe_promotion.is_deleted` 写成 1，`deleted_at` 记下时间。

返回 `promotion_ids`。
