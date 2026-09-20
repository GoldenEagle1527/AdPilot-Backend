---
name: adpilot-change-endpoint
description: Changes an existing AdPilot HTTP API while updating Plan contracts, OpenAPI, and the handoff note. Use when renaming fields, changing path/method/errors, or editing a published system-admin endpoint.
---

# 变更接口

代码与 `Plan/modules/<id>/contracts/<endpoint>.md` 不一致 = 没做完。对外真源是进程上的 `/openapi.json`。  
在 `feat/<business>/<short>` 上改，合入走 PR。

## 步骤

1. 判断破坏性：删字段、改语义、改路径/方法。  
   是 → 先把**改前**契约全文复制到 `contracts/_history/<endpoint>-v<旧文档版本>.md`。
2. 改正文：文档版本 +1；路径只在破坏性时升 `/api/v2`。变更历史**最上行**追加日期/版本/是否破坏/改了什么。
3. 更新 `contracts/最新表.md` 那一行的版本与日期。
4. 改 router / schema。分页、信封、`enabled`、id=string、时间 `Z` 不要私改。
5. 补或更新 `response_model`，使 OpenAPI 与行为一致。只改内部实现且 OpenAPI 不变则不必发对接。
6. 对外 HTTP 有可见变化则发群：

```
【对接】YYYY-MM-DD
类型：变更 / 删除
接口：METHOD /api/v1/...
一句话：……
拉规格：{API基址}/openapi.json
```

禁止在对接文本里贴整份 schema。

## 不要

- 只改代码不改契约、不升版本
- 把信封改成另一套外壳
- 用 Cookie 或 query 传 Token
- 为了「省事」换驱动或把模型搬进 `core`
