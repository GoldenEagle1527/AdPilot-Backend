# Git 与 GitHub

状态：accepted  
ADR：0002、0018、0019、0021。  
Agent 必守：`.cursor/rules/git-branch-pr.mdc`。

产品名 **AdPilot**。本仓是后端应用仓。`Plan/` 跟本仓走，不单独建远程。远程是 GitHub，不再使用内网 Gitea。文件名仍是 `Git与Gitea.md`，避免已有入口断掉。

| 仓 | 远程 | 分支 |
| --- | --- | --- |
| 本仓（后端） | `https://github.com/GoldenEagle1527/AdPilot-Backend` | `main` 受保护；`feat/<business>/<short>` |

本机 `origin` 指向上面这个地址。不要再加 Gitea 远程，也不要往 `git.73oc.local` 拉取或推送。

大文件放云盘。对接：[architecture/两仓通信.md](../architecture/两仓通信.md)。

## 怎么开分支、怎么合

1. 从最新 `main` 拉 `feat/<business>/<short>`。
2. 一个分支只做一个业务。不要往本仓塞前端工程。
3. 合入：GitHub **Pull Request → `main`**。不要直推 `main`。
4. 一人多个接口：仍宜一接口一 PR。
5. 改对外 HTTP：同一 PR 改契约、变更历史、`contracts/最新表.md`；破坏性带 `_history/`。合入后发群对接短文。

生产密钥不准进仓。开发库口令写在本机 `deployment/dev.yaml`（不入库；从 `deployment/dev.yaml.example` 复制）。
