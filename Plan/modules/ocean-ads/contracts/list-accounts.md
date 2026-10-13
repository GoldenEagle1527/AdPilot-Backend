# 巨量广告账户列表

`GET /api/v1/ocean-ads/accounts`

要有菜单 32。只返回当前登录人数据范围内的广告账户。传入的 `account_id` 对不上时，这一页是空的，不另报这个户存在。

页签 `delivery_kind`：`standard` 或 `uni`。收费模式 `charge_mode` 可不传。这两个值取自项目所挂投放主体 `delivery_subject.delivery_mode`、`delivery_subject.charge_mode`。素材行用 `oe_material_report.cdp_project_id` 对 `oe_project.ocean_project_id`。

`account_id` 是 `advertiser_account.advertiser_id`。
