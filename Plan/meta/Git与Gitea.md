# Git 与内网 Gitea

状态：accepted  
ADR：0002、0018、0019。  
Agent 必守：`.cursor/rules/git-branch-pr.mdc`。

产品名 **AdPilot**。本仓是后端应用仓。`Plan/` 跟本仓走，不单独建远程。远程：<http://git.73oc.local/>。

| 仓 | 远程 | 分支 |
| --- | --- | --- |
| 本仓（后端） | `GoldeneaglePersonal/AdPilot-Backend` | `main` 受保护；`feat/<business>/<short>` |

大文件放云盘。对接：[architecture/两仓通信.md](../architecture/两仓通信.md)。

## 怎么开分支、怎么合

1. 从最新 `main` 拉 `feat/<business>/<short>`。
2. 一个分支只做一个业务。不要往本仓塞前端工程。
3. 合入：Gitea **Pull Request → `main`**。不要直推 `main`。
4. 一人多个接口：仍宜一接口一 PR。
5. 改对外 HTTP：同一 PR 改契约、变更历史、`contracts/最新表.md`；破坏性带 `_history/`。合入后发群对接短文。

生产密钥不准进仓。开发库口令写在 `deployment/dev.yaml`。
