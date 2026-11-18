# 部署与运行（v0.5）

Windows客户端和服务器独立部署，无网页前端。2026-11-18已在 `SoftwareAnalysis` 部署单API与PostgreSQL，当前采用SSH隧道访问；GitHub Actions发布过程和精确验证结果见 [v0.5记录](verification/server-v0.5.md)。历史v0.4本机Docker不可用的记录保留，不代表当前远程服务器状态。

## 连接服务器

本机已配置并信任 `SoftwareAnalysis` SSH主机别名时，在仓库根目录执行：

```powershell
.\scripts\connect-server.ps1
# 只建隧道，不打开客户端：
.\scripts\connect-server.ps1 -NoDesktop
# 关闭由本脚本记录且校验过的隧道，不停止服务器：
.\scripts\connect-server.ps1 -Stop
```

脚本将 `127.0.0.1:18080` 转发至服务器 `127.0.0.1:8080`，公共API可达后以 `ACADEMIC_API_URL=http://127.0.0.1:18080` 打开 `artifacts/windows-x64/AcademicDesktop.exe`。已有隧道可复用；端口被其他程序占用时拒绝覆盖。支持 `-LocalPort` 指定其他回环端口。SSH验证主机密钥、禁止交互认证并设置保活；后台窗口隐藏。首次配置SSH身份和可信主机指纹属于客户端连接准备，不能使用CI专用受限密钥建立隧道。

服务器生产库为 `APP_DEMO=false` 的新PostgreSQL库，首次仅创建 `admin`，没有演示账号/资料。初始管理员密码保存在服务器root可读的 `/opt/academic-platform/secrets.env`（0600），用户可自行通过已有SSH登录以sudo在服务器查看。密码未导出到仓库、桌面配置或本地文档；本轮未使用它完成生产管理员登录验证。`ADMIN_PASSWORD` 只用于空库初始化，修改该环境变量不会重置既有账号密码。桌面会话令牌仅在内存。

## 当前服务器与目录

| 项目 | 当前部署 |
| --- | --- |
| 系统/资源 | Ubuntu24.04，4核，3659MiB内存 |
| 容器环境 | Docker27.5.1 / Compose2.32.4 |
| 部署目录 | root所有的 `/opt/academic-platform` |
| 权威配置 | [server compose](../deploy/server/compose.yml)、服务器 `secrets.env`、`release.env` |
| API / 管理入口 | 宿主 `127.0.0.1:8080` / `127.0.0.1:8081`，不直接暴露公网 |
| 数据库 | PostgreSQL17单实例、持久卷，无宿主端口 |
| 资源预算 | API与PG各768MiB、各1CPU；连接池8、数据库最大40连接 |
| 采集策略 | Crossref/CNIPA/NSFC/MOST启用，LYNU停用，所有定时关闭 |
| 实际编排 | 单副本Compose；未启用k3s/HPA |

API镜像非root、只读根文件系统、临时目录64MiB、去除Linux capabilities。可在服务器查看状态：

```sh
sudo docker compose --env-file /opt/academic-platform/secrets.env --env-file /opt/academic-platform/release.env -f /opt/academic-platform/compose.yml ps
curl --fail http://127.0.0.1:8081/actuator/health/readiness
curl --fail http://127.0.0.1:8080/api/reference
```

不要使用会展开环境变量并打印秘密的完整配置输出做日常日志。`release.env` 只记录镜像摘要与提交号；账号密码留在独立 `secrets.env`。`deploy/server/bootstrap.sh` 安装专用账户、受限公钥及root拥有的部署程序，既有secret和数据卷保留；普通发布不会重新初始化数据库。

## GitHub Actions 与连续部署

[CI工作流](../.github/workflows/ci.yml) 在push Group2、指向Group2/main的PR以及手动触发时执行。全部使用GitHub托管运行器，不允许不可信PR进入服务器runner。

| 作业 | 检查或动作 |
| --- | --- |
| backend-h2 | Java21、Gradle wrapper、H2功能测试、bootJar、8项纯mock部署回归；保存JAR及SHA-256 |
| backend-postgres | 独立PostgreSQL17 service运行同套功能测试；不使用生产凭据/数据库 |
| windows-desktop | Windows上WPF Release构建、自带运行时win-x64 EXE与SHA-256产物 |
| publish | 前三项通过后，下载同次运行的测试JAR并核验哈希，用Dockerfile.runtime封装推送GHCR |
| deploy | 将提交号与不可变manifest digest交给服务器受限命令，等待健康门槛 |

只有仓库 `caw111/SoftwareAnalyse` 的 `push refs/heads/Group2` 执行publish/deploy；PR和手动触发仅CI检查。镜像为 `ghcr.io/caw111/softwareanalyse-api@sha256:<digest>`，服务器不按可漂移tag部署。OCI revision必须等于该次40位提交SHA。Actions依赖固定到完整提交SHA，Gradle wrapper验证开启，PR缓存只读。

仓库已配置Secret `DEPLOY_SSH_KEY` 和4个变量 `DEPLOY_HOST`、`DEPLOY_PORT`、`DEPLOY_USER`、`DEPLOY_KNOWN_HOSTS`；不在Git内保存私钥。workflow声明 `environment: production`；本轮没有将环境审批者或分支保护规则记为已配置，应由仓库owner按需要补充。实际发布仍有事件、分支、仓库三项显式限制。

CI专用Ed25519密钥与用户登录密钥分开。服务器authorized_keys限制为 `restrict` + forced-command，唯一接受 `deploy <commitSHA> sha256:<digest>`；一般shell命令、端口转发被拒绝。SSH严格校验预登记主机指纹。短期 `GITHUB_TOKEN` 和本次actor通过标准输入两行传输，不放在命令参数或日志中；服务器使用临时0600 Docker配置拉取私有GHCR镜像，退出时清理。没有长期registry token留在服务器。

部署同时受Actions串行组和服务器 `flock` 保护；Group2正在执行的发布不会因下一次推送被中断。服务器核验镜像标签，已有部署升级前执行 `pg_dump -Fc`，原子切换release配置，再等待Compose健康、readiness及公共API成功。成功写入 `releases/<SHA>.env` 和 `deployments.log`；失败恢复上一应用镜像并再次检查健康，**不自动回滚数据库**。迁移须保持旧应用兼容；不兼容迁移或回滚仍失败时需人工处理。8项mock验证覆盖失败路径，但不等于真实生产故障演练。

## 本机开发与备用模板

```powershell
.\scripts\build.ps1
.\scripts\start-local.ps1 -NoBuild
.\scripts\stop-local.ps1
.\scripts\publish-desktop.ps1
```

本机默认H2/64条模拟数据。构建跑功能测试，运行JAR复制到带哈希的 `artifacts/runtime/`，避免覆盖运行中JAR。更新后端需先停旧进程；本机PostgreSQL用 `DB_URL/DB_USER/DB_PASSWORD` 加 `-UsePostgres`。这些演示账号不用于生产。

`deploy/compose.yml` 和 `deploy/.env.example` 是手工部署模板，与已安装服务器的 `deploy/server/compose.yml` 分开。新服务器手动使用前替换数据库/管理员密码、使用空生产卷，并核对镜像版本；本轮权威发布走上面的摘要流程。需要公开域名时再配置有效TLS反向代理到127.0.0.1:8080，不公开数据库或管理端口。本次选择SSH隧道，没有配置公共域名/HTTPS入口。

## 采集配置与升级

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| CRAWL_WORKER_ENABLED | true | 此API副本是否领取任务，false仍可查看/管理 |
| CRAWL_POLL_MS | 2000 | 调度检查间隔毫秒，不是源站请求频率 |
| CRAWL_CONTACT_EMAIL | 空 | Crossref真实维护者邮箱，未填走公共池、不伪造邮箱 |

手工模板 `deploy/compose.yml` 已接入这三个环境变量。当前服务器 `deploy/server/compose.yml` 将worker固定为true、poll固定为2000；如需更改，应由管理员更新root管理的Compose文件并重建API容器。服务器仅联系邮箱使用环境变量插值，可在root的 `secrets.env` 维护。k3s模板使用同名可选Secret键，修改Secret后需滚动更新。只允许启用来源的固定HTTPS域名/路径（api.crossref.org、www.cnipa.gov.cn、www.nsfc.gov.cn、www.most.gov.cn），不跟随任意重定向，不提供任意URL代理。LYNU域名自v0.5起不再接受请求。

Crossref默认请求间隔至少1500ms，公告2000ms，同源最大并发1；响应头与Retry-After只能延长等待。来源租约、下一请求时刻、任务attempt和停止标志保存在数据库，多副本不会把来源额度翻倍。网络等待不持有业务事务；规范元数据、修订、倒排、页面与断点同页原子发布。失效执行器回调不能提交。

只有Crossref支持定时INCREMENTAL；必须整窗完成才能推进水位。公告只接受固定批次BOUNDED，无定时/完整同步水位。启用来源不等于启动任务。访问拒绝/robots拒绝/验证挑战在有效执行尝试且配置版本匹配时暂停定时并递增configVersion，管理员复核后再开；普通429仅有限退避。

Flyway V6引入冻结文档和batch_id；V7仅停用LYNU、终止其活动任务并保留已提交历史，不增加表字段。注册HTML/PDF原字节最多8MiB，PDF以Base64存储增加约三分之一体积。首批冻结原文与业务同事务保存，恢复核对URL/行数/parser_version，规则变化需新任务。maxRecords只限制处理行数，不限制全文下载。备份必须包含原文、版本和审计，见 [来源说明](design/sources-v0.5.md) 与 [ER](design/database-er.md)。

NSFC使用独立主机限定PKIX客户端，补充CFCA EV ROOT公有证书；不改全局SSLContext、系统或JDK truststore。主机名、有效期、链校验和固定路径继续生效，没有trust-all。根指纹 `5CC3D78E4E1D5E45547A04E6873E64F90CF9536D1CCC2EF800F355C4C5FD70FD`，有效期至2029-12-31T03:07:01Z；2029-10-01前或源站链/运行时变化时重新核验，详见 [TLS维护](../backend/src/main/resources/tls/README.md)。TLS_VALIDATION_FAILED不可自动/手动重试，修复后新建任务。

## 备份、监控与恢复边界

升级前备份保存在root部署目录 `backups/`，以提交号和UTC时间命名；另将备份加密复制至异机/对象存储，并在独立数据库演练pg_restore。当前尚未完成生产备份恢复演练。数据卷不是备份；普通停机不使用 `docker compose down -v`。数据库含私有申请、会话摘要等，备份权限与数据库一致。

`/actuator/prometheus` 提供HTTP延迟直方图、JVM/GC和连接池指标，管理端口只在回环。监测源文档/版本/倒排体积、PG连接与锁等待、JVM内存和前台请求延迟；4GB机器不默认装重型监控栈，也不在服务器执行Gradle构建。

## k3s/HPA 与性能验收（后续）

[现有k3s模板](../deploy/k3s/app.yaml) 仅作后续迁移方案，未在当前服务器应用或验证自动扩缩容。模板API1–2副本，每副本上限512MiB，PG上限512MiB；HPA CPU目标70%、扩容窗口30秒、缩容300秒，每分钟最多增减1副本。使用前核对实际镜像digest、Secret、StorageClass、metrics-server、TLS及资源余量，不能将旧模板版本当生产release。

[k3s最低配置](https://docs.k3s.io/installation/requirements) 不包含业务负载；[HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) 依赖resource requests与metrics API。HPA只增加API计算副本，不增加物理内存、不扩数据库或来源额度。单实例PG不构成高可用；单副本滚动升级会短暂停机。

按用户要求未运行本机压测。本轮也未执行服务器负载测试，没有P95达标、长期稳定或扩容收益结论。后续按 [服务器压测说明](../scripts/performance/README.md) 执行冷/热缓存、基线和扩缩容对照；跨公网SSH的功能测试耗时不能当服务器延迟基准。
