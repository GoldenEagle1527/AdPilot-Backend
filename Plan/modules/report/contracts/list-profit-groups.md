# 契约：list-profit-groups

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/profit/groups
作用：组利润。所选区间一个部门一行。

作者：
状态：draft
更新日期：2026-10-13

## 请求

Header `Authorization`。要菜单 29。查询同 [list-profit-pitchers.md](list-profit-pitchers.md)。

## 响应

`list` 每一项：`department_id`、`department_name`，加四个利润字段。`summary` 同概览。

## 错误

无菜单 29 为 403。其余同概览。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 利润报表 / 组利润统计（菜单 29） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
