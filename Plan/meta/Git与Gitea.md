# Git 与内网 Gitea

状态：accepted  
ADR：0002、0016、0018、0019。

产品名 **AdPilot**。**两个** Git 仓库：后端、前端。`Plan/` 只是现在写计划，**不单独建远程**。远程预定 <http://git.73oc.local/>。**现在：本工作区已本地 init；两个应用仓实现期再 init。都不加 origin、不 push。**

大文件放云盘，小文件进 git。

对接：[architecture/两仓通信.md](../architecture/两仓通信.md)。

## 两个仓

| 仓 | 预定远程名 | 分支习惯 |
| --- | --- | --- |
| 后端 | AdPilot | `main`、`feat/<business>/<short>`（框架：`feat/framework`） |
| 前端 | AdPilot-Frontend | 同上 |

一个分支不要混两个业务。不要把前端文件推进后端仓。

生产密钥不准进仓。开发库口令写在**该应用仓**的 `deployment/dev.yaml`。
