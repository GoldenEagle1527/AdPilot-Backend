# 巨量广告账户列表

`GET /api/v1/ocean-ads/accounts`

要有菜单 32。只返回当前登录人数据范围内的广告账户。传入的 `account_id` 对不上时，这一页是空的，不另报这个户存在。

页签 `delivery_kind`：`standard` 或 `uni`。收费模式 `charge_mode` 可不传。按产品稿 3.5.1「根据广告id关联到我们自己的广告计划表中获取」：广告计划表由研发定为 `oe_promotion`。素材行用 `oe_material_report.advertiser_id`、`cdp_promotion_id` 对 `oe_promotion.advertiser_id`、`promotion_id`，再用 `oe_promotion.ocean_project_id` 对 `oe_project.ocean_project_id`，取项目所挂投放主体 `delivery_subject.delivery_mode`、`delivery_subject.charge_mode`。

账户出现在某个页签，要这个户在 `oe_promotion` 里有一条未删除的广告，它所属项目挂的主体是这个页签。对不上 `oe_promotion` 的素材行、已删除的广告或项目下的素材行，不算进账户的效果数。

`account_id` 是 `advertiser_account.advertiser_id`。

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿。页签和收费模式取素材行项目 id 对上的项目所挂主体 | 李伟峰 |
| 2026-10-14 | 2 | 否 | 按 3.5.1 改为经广告 id 对 `oe_promotion`，再取广告所属项目挂的主体。参数和返回字段不变 | 李伟峰 |
