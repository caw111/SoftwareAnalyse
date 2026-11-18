# v0.5 服务器、CI/CD与桌面验证

日期：2026-11-18。分支：Group2。当前范围包括LYNU弃用、已有应用回归、首次生产Compose部署、SSH隧道和GitHub Actions发布。来源语义见 [v0.5来源说明](../design/sources-v0.5.md)，运行步骤见 [部署说明](../deployment.md)。[v0.4记录](sources-v0.4.md) 保留原日期与四源真实任务事实，不复写历史结论。

## 结果与证据范围

| 层次 | 结果 | 范围/证据 |
| --- | --- | --- |
| H2功能回归 | 83通过，0失败/错误/跳过 | `artifacts/verification-v0.5/h2-tests/`，9个JUnit XML |
| PostgreSQL功能回归 | 83通过，0失败/错误/跳过 | 同目录 `postgres-tests/`；独立测试容器/库，非生产库 |
| 部署脚本模拟 | 8/8通过 | `scripts/test-deployment.py`；假的docker/curl，无真实故障注入或数据库恢复 |
| WPF业务 | public/login/workspace/crawl全部通过 | 同目录四份JSON及截图；本机8080功能API |
| 原生Windows窗口 | 通过 | `native-window.json`：0.5.0.0、192DPI/200%、最大化/还原/拖动/最小化/关闭/图标 |
| 生产Compose | API与PostgreSQL健康 | Ubuntu服务器真实容器、readiness与公共API |
| 生产数据库 | V1–V7迁移成功 | APP_DEMO=false新库，仅1个admin、0演示数据 |
| SSH访问 | 18080隧道公共API通过 | `scripts/connect-server.ps1 -NoDesktop`，回环转发 |
| 生产管理员登录 | 未验证 | 初始密码只留服务器root配置；未导出或用于此项测试 |
| GitHub Actions检查 | 五个作业全部通过，运行completed/success | [运行44222517334](https://github.com/caw111/SoftwareAnalyse/actions/runs/44222517334) |
| GHCR镜像发布 | 通过 | 同次CI测试JAR封装镜像，manifest digest见下表 |
| Actions远程部署 | 通过 | release摘要/提交与OCI标签一致，API/PG健康、readiness UP、公共API通过 |

PostgreSQL回归经SSH跨公网隧道运行，用时约8分46秒是测试执行总耗时，不是吞吐、响应延迟或P95证据。测试后已清理独立容器 `academic-platform-verify` 及15432测试隧道，生产库未用于功能测试。汇总文件为 `artifacts/verification-v0.5/backend-tests.json`。产物与日志保存在本地artifacts，不提交到Git。

### 后端测试分项

| 测试类 | H2 | PostgreSQL |
| --- | ---: | ---: |
| CatalogRevisionIntegrationTest | 9 | 9 |
| CnipaPatentParserTest | 3 | 3 |
| CrawlIntegrationTest | 15 | 15 |
| HttpContractTest | 8 | 8 |
| PlatformIntegrationTest | 19 | 19 |
| RegisteredHtmlParserTest | 9 | 9 |
| RegisteredSourceIntegrationTest | 12 | 12 |
| RegisteredSourceTransportTest | 3 | 3 |
| SearchStatisticsTest | 5 | 5 |
| 合计 | 83 | 83 |

LYNU专项包括弃用目录标记、禁止新任务/设置/启动与重试、活动任务停止、提交/回调拒绝和历史保留。既有固定批次解析、冻结原文、幂等、TLS边界、事务与检索统计继续回归。本轮功能测试不代表新一轮外站批量采集，历史真实来源低量验证见v0.4记录。

### 桌面验证

使用本次发布的真实WPF EXE，公共页面、注册/登录/访客、角色工作区和管理员采集页面均通过。workspace有9项检查，crawl有19项检查，包含三个有效公告源的Create→STOP、来源设置隔离、LYNU从新建/设置隐藏、历史任务仍可读且不可重启；历史检查实际执行，不是缺数据后跳过。采集UI测试未发送START，不访问外部来源、不执行压测。

原生窗口验证使用真实标题栏鼠标拖动及系统按钮，确认前台窗口和指针命中目标；默认最大化、还原、拖动、再次最大化、最小化、关闭和图标均通过。桌面测试连接本机功能API，不等于生产管理员登录。新版EXE哈希与下表一致。

## 服务器状态

| 项目 | 已核实值 |
| --- | --- |
| SSH配置别名 | SoftwareAnalysis |
| 操作系统 | Ubuntu24.04 |
| CPU / 内存 | 4核 / 3659MiB |
| Docker / Compose | 27.5.1 / 2.32.4 |
| 部署根目录 | /opt/academic-platform，root所有 |
| 应用/管理监听 | 宿主127.0.0.1:8080 / 127.0.0.1:8081 |
| 用户入口 | SSH隧道，本机127.0.0.1:18080 |
| 数据库 | PostgreSQL17、独立持久卷、无宿主端口 |
| 生产演示开关 | APP_DEMO=false |
| 来源 | Crossref/CNIPA/NSFC/MOST启用；LYNU停用；定时均关闭 |

管理员初始密码仅保存在服务器root可读 `secrets.env`；本轮没有密码导出、没有将生产密码写入本地文件，也没有管理员登录成功声明。一般使用者不应把本机演示账号用于生产。

## CI/CD与发布标识

| 标识 | 值 |
| --- | --- |
| 来源弃用阶段提交 | `01aa22d` |
| 部署/CI阶段提交 | `ac496cc0fc459e192a065ffea1dcf85286293136` |
| Actions运行 | [44222517334](https://github.com/caw111/SoftwareAnalyse/actions/runs/44222517334) |
| 镜像仓库 | `ghcr.io/caw111/softwareanalyse-api` |
| 镜像manifest digest | `sha256:c17cdaf287430e38ee5c14a88eb98f0d694458f85aa5b7041207d8045710bb94` |
| 本机v0.5 EXE SHA-256 | `B8FD98B07EFD380F20C5883C6B40EEBF0B9EE2B07A41590EF03DE459FE6EA7F7` |
| 本机v0.5 API JAR SHA-256 | `6D76AD42A77749B8C3174DC21AC0635281235251EC151DE2DF390F783DD9EFFB` |

本机EXE/JAR哈希不冒充CI运行器构建产物哈希；CI各自保存SHA-256，镜像使用同次CI H2作业生成并校验的JAR。以manifest digest和OCI提交标签关联远程发布。

最终机器核验时间为2026-11-18T02:37:49Z（上海时间10:37:49）。`release.env` 的镜像digest与上表一致，RELEASE_SHA与OCI revision均为本次CI提交；API与PG容器均healthy，readiness为UP。记录分别保存在 `artifacts/verification-v0.5/github-actions.json` 和 `server-release.json`。

升级前备份 `pre-ac496cc0fc459e192a065ffea1dcf85286293136-20261118T023610Z.dump` 为76,975字节、权限0600，PGDMP归档头有效；此检查只证明归档文件存在及头部格式有效，未执行恢复演练。部署结束后临时 `.registry-auth` 目录数量为0，未留下本次GHCR临时认证目录。

仓库专用DEPLOY_SSH_KEY及4个非秘密变量已配置；服务器专用密钥forced-command测试拒绝 `id`。私钥与临时GHCR凭据不写入仓库或日志，CI密钥不可当作普通SSH登录或隧道密钥。环境production被workflow引用，本轮未验证额外环境审批/分支保护规则已配置。部署串行、升级前备份、应用回滚和无自动数据库回滚的实现见 [部署说明](../deployment.md)。

## 未验证与后续验收

本轮未进行本机或服务器压测，没有P95达标声明；未运行k3s/HPA、长期稳定性、公开HTTPS入口、生产管理员登录、真实生产回滚/数据库备份恢复演练。8项模拟故障测试不能替代恢复演练；健康检查通过不证明全部业务或来源长期可用。后续压测仅按服务器计划执行，见 [性能说明](../../scripts/performance/README.md)。
