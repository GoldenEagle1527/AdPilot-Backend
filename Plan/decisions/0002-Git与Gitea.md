# ADR 0002：用 Git 做版本与沟通，远程预定内网 Gitea

状态：accepted

## 决定

- 项目版本管理使用 Git。
- 远程预定 `http://git.73oc.local/`。
- 远程预定 `http://git.73oc.local/`。后端仓已加 origin（`AdPilot-Backend`）。
- 合入：Issue / PR 作为跨人通信面（`feat/<business>/<short>` → `main`）。
- 产品名与「一个仓」的旧口径见 [0016](0016-未决收口.md)；**两个应用仓**见 [0018](0018-前后端两个Git仓库.md)。对接见 [0019](0019-后端OpenAPI对接.md)。

## 后果

生产凭证不得进入仓库。开发共用库连接按 [0017](0017-Docker与共用库.md) 写在各应用仓 `deployment/dev.yaml`。分支按业务切开。不建第三计划远程。
