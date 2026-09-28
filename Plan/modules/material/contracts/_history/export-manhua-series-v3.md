# 契约：export-manhua-series

业务id：material
文档版本：3
方法：POST
路径：/api/v1/material/manhua-series/export
作用：按漫剧库列表的同一套筛选，把全部匹配行导出为 xlsx。不分页。不做数据范围过滤。

作者：
状态：accepted
更新日期：2026-09-28

## 请求

查询参数与 [list-manhua-series.md](list-manhua-series.md) 相同。`page`、`page_size` 可传，不参与导出。

无请求体。需 `Authorization: Bearer` 且有效菜单含节点 `95`。

时间格式、区间和集数上下限的校验与列表相同，不合规则 422。

## 响应

成功时 HTTP 200，不是信封。响应体是 xlsx 文件。

| 头 | 值 |
| --- | --- |
| Content-Type | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| Content-Disposition | `attachment; filename="manhua_series.xlsx"` |

工作表名 `漫剧库`。第一行是表头，其后每行一条。单元格都是文本。

| 列 | 来源 | 说明 |
| --- | --- | --- |
| 短剧名称 | book_name | |
| 集数 | episode_amount | |
| 发布状态 | publish_status | `1` 未发布、`2` 已发布、`3` 已下架；其余原样 |
| 预估投放时间 | estimate_publish_time | 常读原串 |
| 是否当天上架 | publish_time | 发布时间落在北京今天为 `是`，否则 `否` |
| 发布时间 | publish_time | 常读原串 |
| 创建时间 | create_time | 常读原串 |
| 采集时间 | collected_at | 北京时间 `YYYY-MM-DD HH:MM:SS` |
| 抖音id | playlet_id | 常读专辑 ID，文本，避免 Excel 科学计数 |
| 抖音名 | douyin_nick_name | |

没有匹配行、或传入了 `department_id` 时，文件只有表头。

失败（401 / 403 / 422 / 500）仍走信封。共用错误见 [说明.md](说明.md)。

## 错误

无本接口特有错误。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 素材管理/漫剧流转剧库 | 按当前筛选导出 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-09-28 | 3 | 是 | 去掉部门列。快照 [_history/export-manhua-series-v2.md](_history/export-manhua-series-v2.md) | |
| 2026-09-28 | 2 | 是 | 导出列改为短剧名称、集数、部门、发布状态、预估投放时间、是否当天上架、发布时间、创建时间、采集时间、抖音id、抖音名。快照 [_history/export-manhua-series-v1.md](_history/export-manhua-series-v1.md) | |
| 2026-09-28 | 1 | 否 | 初稿 | |
