# 巨量广告项目批量改预算

`POST /api/v1/ocean-ads/projects/budget`

要有菜单 33。只改当前登录人数据范围内、还没删除的项目。看不了的项目 id 不报错，也不出现在返回里。

正文：

- `project_ids`：项目 id，即 `oe_project.ocean_project_id`，1 到 100 个
- `budget`：目标预算，单位元，大于 0，最多两位小数

这是项目配置里的目标预算，不是剩余金额。通知巨量 `POST /open_api/v3.0/project/budget/update/`，`budget_mode` 为 `BUDGET_MODE_DAY`，一次最多 10 条。巨量返回成功的才把金额写回 `oe_project.template.delivery_setting.budget`。有失败项时，成功的已写入，接口返回 502。

返回 `project_ids`。
