# ADR 0020：开发测试一律本机 Docker；112.12 只给生产

状态：accepted  
废止：[0017](0017-Docker与共用库.md) 里「开发连 192.168.112.12 共用实例、不要本机再起一套」对**开发/测试**的口径。生产仍可用该共用库。

## 决定

1. 计划正文落在**后端应用仓** `Plan/`。`H:\Projects\drooling\Plan` 已废弃，不再当工作目录。
2. **开发与联调**：PostgreSQL 18.x、Redis 7.2.x、后端进程全部跑在**本机 Docker Compose**。数据卷在本机，不连 192.168.112.12。
3. **生产**：才连计划里写的共用库（192.168.112.12）。配置用 `deployment/prod.yaml`，不要把生产地址写进 `dev.yaml`。
4. 应用镜像仍只打 FastAPI；Postgres / Redis 是 compose 里的旁路容器，不打进 `dockerfile/backend.Dockerfile`。
5. 镜像只从 Harbor `192.168.111.40:88/group-one` 取。
