# ADR 0021：后端仓远程改为 GitHub，废止 Gitea

状态：accepted  
废止：[0002](0002-Git与Gitea.md) 与 [0016](0016-未决收口.md) 里「远程预定 `http://git.73oc.local/`」。Git、分支名、Pull Request 合入仍按 0002。两个应用仓仍按 [0018](0018-前后端两个Git仓库.md)。

## 决定

1. 本后端仓的唯一远程是 GitHub：`https://github.com/GoldenEagle1527/AdPilot-Backend`。本机远程名是 `origin`。
2. 内网 Gitea（`http://git.73oc.local/`，含 `GoldeneaglePersonal/AdPilot-Backend`）不再使用。不拉取、不推送、不在那里开 Pull Request。
3. 合入仍是 `feat/<business>/<short>` 的 GitHub Pull Request 进 `main`。不要直推 `main`。
4. 这条只定本后端仓。前端仓 `AdPilot-Frontend` 的远程不在这里改。

## 后果

日常 `git pull` / `git push` 只对 GitHub `origin`。规格正文在 [meta/Git与Gitea.md](../meta/Git与Gitea.md)（文件名保留，正文已改）。
