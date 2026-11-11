# 部署与运行

Windows 客户端与服务器独立部署。客户端自带 .NET 运行时的 EXE 在 `artifacts/windows-x64/`；服务器只运行 API 与 PostgreSQL，不托管网页。后台 Dockerfile 在首版已完成 Linux 镜像构建验证，本轮镜像结果另记。

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
docker build -t academic-platform-api:0.3.0 backend
docker save academic-platform-api:0.3.0 -o artifacts/academic-platform-api.tar
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

## v0.3 采集服务配置

采集执行器随 API 运行，只领取管理员明确启动的任务或已启用计划产生的任务。数据库中 Crossref 来源默认启用，**定时计划默认关闭**；不会在服务启动时自动扫描全库。来源设置、任务、租约、水位和日志均持久化于 PostgreSQL，重启不丢已提交页面。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| CRAWL_WORKER_ENABLED | true | 是否运行该 API 副本的采集执行器；false 时仍可管理/查看任务，但该副本不领取 |
| CRAWL_POLL_MS | 2000 | 任务调度检查间隔，单位毫秒；不是对源站请求频率 |
| CRAWL_CONTACT_EMAIL | 空 | 真实维护者联系邮箱，用于 Crossref User-Agent/mailto；未配置时走公共池，不伪造邮箱 |

手动限制来源频率、启停来源、定时 ISSN、周期、窗口回看和页预算在管理员的“来源采集/来源设置”中配置，修改携带配置 version。单来源默认至少间隔1500ms、最大并发1；响应限流标头和 Retry-After 可以延长等待。定时任务是 INCREMENTAL，限量任务 BOUNDED 不推进完整同步水位。采集范围/数量的解释见 [构件设计](design/component-design.md)。

Compose 模板已将以下三个变量接入 api.environment，deploy/.env.example 已列出默认值。复制为 deploy/.env 后按需要修改；联系邮箱填写真实维护者地址，未配置时保留为空：

```yaml
CRAWL_WORKER_ENABLED: ${CRAWL_WORKER_ENABLED:-true}
CRAWL_POLL_MS: ${CRAWL_POLL_MS:-2000}
CRAWL_CONTACT_EMAIL: ${CRAWL_CONTACT_EMAIL:-}
```

k3s 模板对三个变量均使用 academic-secrets 的同名可选键引用。用 deploy/.env 创建 Secret 时会一起导入；升级旧 Secret 缺少这些键时，应用继续使用 true / 2000 / 空邮箱的默认值。修改 Secret 后需滚动更新 API Pod 才读取新的环境变量。API Pod 需要访问 api.crossref.org 的 HTTPS 和解析 DNS；采集适配器固定域名与路径且不跟随任意重定向，不开放任意 URL 抓取代理。

### 小服务器与扩缩容边界

每个副本都可以调度，但数据库来源租约和 next_request_at 对所有副本生效，同一来源不会因 HPA 从1扩到2副本而翻倍并发。页提交时再次校验任务 attempt、租约令牌和 stop_requested；被缩容的旧执行器不能通过迟到响应写入数据。已提交页保留，未完成任务由租约恢复路径接续。

采集网络等待在事务外，规范入库、修订与倒排在同一页事务中发布。4核4GB初始保留单来源串行、小页和显式预算；不要同时启用大批采集、索引全量补建和性能验收。监测数据库连接池、发布锁等待、原始页/版本/倒排表体积、JVM内存与前台请求延迟，再调整资源。HPA只增加API计算副本，不提高源站额度、不扩数据库，也不替代机器升级。

H2/PostgreSQL 功能测试、桌面与单 DOI 接通结果由最终验证记录单列；它们不证明服务器吞吐、P95或HPA收益。部署模板本次仅做静态解析与 Compose 配置检查，不执行远程部署或集群应用。

有效执行尝试遇到来源访问拒绝、robots 拒绝或验证挑战，且来源配置版本仍匹配时，后台会关闭该来源的定时计划并递增 configVersion；来源 enabled 不变，管理员核实条件后仍可显式创建人工任务或恢复计划。旧执行尝试不能关闭已更新的配置。普通 429 只有限退避，不关闭计划。客户端修改旧配置版本会收到冲突，应先刷新来源设置。
