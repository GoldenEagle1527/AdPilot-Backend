# 契约：list-profit-group-pitchers

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/profit/groups/pitchers
作用：组利润点开一个部门，看该部门每个投手。

作者：
状态：draft
更新日期：2026-10-13

## 请求

同组利润，另有必填 `department_id`。部门不在可见范围里时列表为空。

## 响应

同 [list-profit-pitchers.md](list-profit-pitchers.md)。

## 错误

缺 `department_id` 为 422。无菜单 29 为 403。


## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 组利润统计，点部门（菜单 29） | 页面 |

## 变更历史

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
