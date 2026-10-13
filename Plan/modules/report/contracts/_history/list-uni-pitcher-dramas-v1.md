# 契约：list-uni-pitcher-dramas

业务id：report
文档版本：1
方法：GET
路径：/api/v1/reports/uni/pitcher-dramas
作用：漫剧全域短剧报表 tab2「投手短剧收益」。所选区间内一部剧一行，多一格投手。读快照，不调巨量。

作者：
状态：draft
更新日期：2026-10-13

## 请求

与 [list-uni-dramas.md](list-uni-dramas.md) 相同，菜单 13。

口径按 [口径.md](../../../product/数据报表/口径.md)「剧目页」：一部剧一行，投手放一个格子用 `、` 连接，指标是这几个投手之和；当前用户须在投手里。

## 响应

同 [list-uni-dramas.md](list-uni-dramas.md)，`list` 每一项多一个字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| pitchers | string | 该剧在区间内有数据或新建项目的投手姓名，`、` 连接 |

## 错误

同 [list-uni-dramas.md](list-uni-dramas.md)。

## 被谁调用

| 调用方 | 动作 |
| --- | --- |
| 数据报表 / 漫剧全域报表 / 短剧报表 tab2 | 列表、排序、顶部汇总 |

## 变更历史

新记录插在最上行。破坏性变更须先快照到 `_history/`。规则见 [../../../architecture/契约版本.md](../../../architecture/契约版本.md)。

| 日期 | 文档版本 | 破坏？ | 变更 | 作者 |
| --- | --- | --- | --- | --- |
| 2026-10-13 | 1 | 否 | 初稿 | |
