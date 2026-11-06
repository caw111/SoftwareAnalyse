# 部署与运行

Windows 客户端与服务器独立部署。客户端自带 .NET 运行时的 EXE 在 `artifacts/windows-x64/`；服务器只运行 API 与 PostgreSQL，不托管网页。后台 Dockerfile 已实际构建为 Linux 镜像。

## 本机开发

仓库根目录：

```powershell
.\scripts\build.ps1
.\scripts\start-local.ps1 -NoBuild
.\scripts\stop-local.ps1
.\scripts\publish-desktop.ps1
```

`build.ps1` 默认跑功能测试。`start-local.ps1` 默认使用 H2/64 条模拟数据，日志在 `artifacts/api.*.log`。运行 JAR 会复制到带哈希的 `artifacts/runtime/`，避免重新构建覆盖运行中 JAR 造成延迟类加载失败。启动脚本检测到已有 API 时直接打开客户端；更新后端代码需先停止旧进程再启动。

使用本机 PostgreSQL 时先设置 `DB_URL`、`DB_USER`、`DB_PASSWORD`，再加 `-UsePostgres`。会话不在客户端落盘，重新启动需重新登录。服务断开时桌面保留筛选条件并显示错误。

## Docker Compose（4 核 4 GB 首次部署可先使用）

在 Linux 服务器仓库目录执行；下面是操作说明，本次没有部署到远程服务器。

```sh
cd deploy
cp .env.example .env
# 编辑 .env：替换 DB_PASSWORD 和 ADMIN_PASSWORD，后者至少 16 字符。
chmod 600 .env
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8081/actuator/health/readiness
```

生产使用新的 PostgreSQL 卷；`APP_DEMO=false`，首次只建 admin，不插入演示资料。ADMIN_PASSWORD 只在空库初始化时生效，不是已有账号的密码重置功能。不要复用开发演示库。

API 与 PostgreSQL 各限制 768 MiB；API 非 root、只读根文件系统、临时目录限 64 MiB。数据库未暴露宿主端口。API 8080 和管理端口 8081 只绑定服务器回环。

给域名配置有效 TLS，反向代理到 127.0.0.1:8080；例如已有 Caddy 服务可使用：

```caddyfile
academic.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

桌面端填 `https://academic.example.com`。不将管理端口或 PostgreSQL 暴露公网。生产防火墙只开放实际需要的入口，域名和证书准备好后再开放服务。

## k3s 与自动扩缩容

[k3s 官方基线](https://docs.k3s.io/installation/requirements) 的 server 最低 2 核/2 GB 不含业务负载。4 核 4 GB 下采用小规格模板：API 每副本最高 512 MiB，数据库最高 512 MiB，最多 2 个 API，余下资源留给系统与控制面。该预算仍需服务器测量；不能把 HPA 当作增加物理资源。若 OOM、频繁 GC 或数据库等待上升，先限制 1 副本，必要时升级机器。不要在 4 GB 服务器同时运行 Gradle 构建和验收负载；在开发机/CI 构建镜像后上传。

准备已安装的 k3s、可用的 local-path StorageClass、metrics-server 与 Traefik。HPA 使用 CPU utilization，需要 resource requests 和 metrics API（见 [Kubernetes HPA 文档](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)）。

```sh
# 开发机或 CI 构建/导出；也可推送到自己的镜像仓库。
docker build -t academic-platform-api:0.1.0 backend
docker save academic-platform-api:0.1.0 -o artifacts/academic-platform-api.tar
# 将 tar 与部署文件复制到服务器；在服务器导入。
sudo k3s ctr images import academic-platform-api.tar
kubectl create namespace academic
kubectl -n academic create secret generic academic-secrets --from-env-file=deploy/.env
kubectl apply --dry-run=server -f deploy/k3s/app.yaml
kubectl apply -f deploy/k3s/app.yaml
kubectl -n academic rollout status deployment/postgres
kubectl -n academic rollout status deployment/api
kubectl -n academic get pods,hpa,pvc
```

如果使用镜像仓库，修改 deployment 的 image 为带版本或摘要的实际地址。k3s 文件目前仅完成 YAML 静态检查，**没有运行集群部署或 HPA 实测**。

HPA：1–2 副本，目标 CPU 为 request 的 70%，扩容稳定窗口 30 秒，每分钟最多加 1 个；缩容稳定窗口 300 秒，每分钟最多减 1 个。每副本数据库连接上限 8，数据库 max_connections=40。令牌在数据库中，事务/唯一约束在数据库中，公共缓存按发布版本分开，因此不要求会话粘滞。

滚动更新 `maxSurge=0,maxUnavailable=1` 防止额外副本挤占内存；只有 1 副本时更新会短暂停机。若要无中断更新，需至少 2 个健康副本并验证资源余量。PostgreSQL 是单实例 PVC，自动扩 API 不会自动扩数据库，也不构成高可用集群。

编辑 `deploy/k3s/ingress.example.yaml` 中的域名，并创建 TLS Secret：

```sh
kubectl -n academic create secret tls academic-tls --cert=fullchain.pem --key=privkey.pem
kubectl apply -f deploy/k3s/ingress.example.yaml
```

Ingress 只转发 `/api`，不发布管理端口。内部集群还应按实际拓扑应用网络隔离策略；模板没有假设用户的监控命名空间或 CNI。

## 监控、备份与恢复

`/actuator/prometheus` 导出 HTTP 延迟直方图、JVM、GC、连接池等指标。k3s 中可临时 `kubectl -n academic port-forward deployment/api 8081:8081`，或配置内部 Prometheus。HPA 依赖 metrics-server 的 CPU 数据，不要求安装完整 Prometheus；4 GB 机器不默认安装重型监控栈。

备份示例（Linux，生成新文件，不覆盖既有备份）：

```sh
mkdir -p backups
docker compose -f deploy/compose.yml exec -T db pg_dump -U academic -d academic -Fc > "backups/academic-$(date +%Y%m%d-%H%M%S).dump"
```

将备份加密复制到不同机器/对象存储，并在独立新数据库中演练 `pg_restore`。PVC 不是备份；不要把 `docker compose down -v` 用作普通停止命令。数据库包含账号摘要、会话与私有证明，备份访问权限应与数据库一致。

## 服务器压测

严格按 [服务器压测说明](../scripts/performance/README.md) 在服务器环境执行。本机未运行压测。当前交付不含低 P95、扩容收益或 4 GB 长期稳定性的实测结论。
