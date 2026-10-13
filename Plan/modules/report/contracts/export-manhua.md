# 契约：export-manhua

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/manhua/export
作用：漫剧报表导出 Excel。行与对应列表同筛选、同权限、同排序，不分页。

作者：
状态：draft
更新日期：2026-10-13

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | `IAP` 要菜单 9，`IAA` 要菜单 5 |
| level | query | string | 是 | `drama` 剧目页、`project` 项目页、`promotion` 计划页 |
| 其余 | query | | | 与 `level` 对应列表相同：`drama` 见 [list-manhua-dramas.md](list-manhua-dramas.md)，`project` / `promotion` 见 [list-manhua-projects.md](list-manhua-projects.md)。`page`、`page_size` 收但不生效 |

## 响应

成功时不是信封：HTTP 200，`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，`Content-Disposition: attachment; filename*=UTF-8''漫剧报表-<charge_mode>-<level>-<起>_<止>.xlsx`。

一个工作表。第一行中文表头，之后一行一条。列：

- `drama`：剧目名称、投放媒体、剧目类型、剧目渠道、投放类型、面板类型、新/老剧、团队、优化师、有消耗计划数，然后指标。
- `project`：项目名称、项目ID、剧目名称、优化师、项目创建时间、项目开始有消耗时间、项目预算、ROI系数，然后指标。
- `promotion`：计划名称、计划ID、剧目名称、优化师、计划创建时间、计划开始有消耗时间、项目预算、ROI系数，然后指标。

指标列顺序：消耗、付费金额、回收ROI、当日付费金额、当日广告变现LTV、7日付费金额、7日广告变现LTV、当日付费ROI、当日广告变现ROI、7日付费ROI、7日广告变现ROI、展示数、平均千次展现成本、点击数、点击成本、激活数、激活成本、转化数、转化成本、点击率(%)、激活率(%)、转化率(%)。数值口径同列表。没有行时只有表头。

## 错误

失败仍走信封。

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 缺本收费模式对应的菜单 | 403 | |
| 筛选不合法（同对应列表） | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 漫剧报表各页「导出 Excel」 | 下载文件 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
