# ADR 0017：开发部署用 Docker；配置用 yaml；库用共用实例

状态：accepted

## 决定

- 应用用 **Docker** 部署。项目 **Dockerfile 放在仓库 `dockerfile/`**，不把 Redis、PostgreSQL 打进本项目镜像。
- Redis、PostgreSQL 使用已经在 Docker 里跑着的**共用实例**，应用只连接。
- 配置用 **yaml**，不用 dotenv。配置文件统一放仓库 **`deployment/`**。
- 开发环境连接（团队公布）：

| 服务 | 主机 | 端口 | 其它 |
| --- | --- | --- | --- |
| PostgreSQL | 192.168.112.12 | 5432 | 库/用户 `ad_pilot`，密码见 `deployment/dev.yaml` |
| Redis | 192.168.112.12 | 6379 | 无密码 |

版本仍须满足 Redis 7.2.x、PostgreSQL 18.x（ADR 0013/0014）。连上后用 `ready` 检查核对。

生产密钥不得用这份开发口令。开发共用库口令按团队约定写在 `deployment/dev.yaml`。

细则：[architecture/部署.md](../architecture/部署.md)。
