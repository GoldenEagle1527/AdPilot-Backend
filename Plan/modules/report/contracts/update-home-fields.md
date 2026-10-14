# 契约：update-home-fields

业务id：report
文档版本：1
方法：PUT
路径：/api/v1/reports/home/fields
作用：整行替换当前账号该表面的三个自选。登录只要 Bearer，不查菜单。

作者：
状态：draft
更新日期：2026-10-14

## 请求

| 字段 | 位置（path/query/body/header） | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| Authorization | header | string | 是 | Bearer。不查菜单 |
| surface | body | string | 是 | `manhua`、`uni_drama`、`uni_pitcher_drama`、`uni_pitcher`、`uni_group` |
| fields | body | string[] | 是 | 恰好三个、互不相同、且都在该表面可选集里，否则 422。可选集与 get-home 相同。全域的展示数、点击率不能选 |

## 响应

`data`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| surface | string | 入参 |
| fields | string[] | 顺序与请求相同 |

## 错误

| 情况 | HTTP 状态 | 说明 |
| --- | --- | --- |
| 未登录 | 401 | |
| 表面或字段不合法 | 422 | |

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 首页 | 替换当前账号该表面的三个自选 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-14 | 1 | 否 | 初稿 | |
