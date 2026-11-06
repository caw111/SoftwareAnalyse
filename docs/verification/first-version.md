# 第一版验证记录

日期：2026-11-06（Asia/Shanghai）。应用源码提交：`36fe161`。完整机器可读记录见 [results.json](results.json)，界面截图见 [Windows 桌面截图](windows-desktop.png)。

## 已执行

| 项目 | 结果 |
| --- | --- |
| Java 21 / Gradle 9.8 / Spring Boot 4.1.2 构建 | 成功，生成可执行 JAR |
| H2 功能测试 | 17 项领域测试 + 4 项 HTTP 契约测试，21/21 通过 |
| PostgreSQL 17.11 功能测试 | 相同 21 项全部通过，独立 academic_test 数据库 |
| WPF Release 构建 | 成功，0 warning / 0 error |
| Windows x64 自带运行时打包 | 成功，单文件 EXE；SHA-256 见 results.json |
| 打包后 EXE 冒烟 | 实际启动 WPF，加载 20 张成果卡片、学者列表、4 个统计卡片和共著路径；截图人工检查 |
| 跨 API 实例功能 | Windows Java 进程 + Linux Docker 容器共享 PostgreSQL；会话可跨实例使用，角色变更即时生效，证据越权 403 |
| 两请求审核/撤回竞争 | 一个 200、一个 409；最终 WITHDRAWN 时无门户绑定，状态/授权一致 |
| Dockerfile | 实际构建 Linux 镜像成功；非 root、只读文件系统、512 MiB 限制下启动并 readiness=UP；少量功能请求成功 |
| Compose | `docker compose config --quiet` 通过 |
| k3s/HPA | YAML 静态解析通过，7 个 Kubernetes 对象；没有集群执行 |
| PowerShell/JSON/k6 JS | PowerShell 解析、JSON 解析、`node --check` 通过；没有运行 k6 |

领域测试覆盖：DOI 规范化、重复来源和 requestKey 幂等、批次回滚、追加式目录快照、合法空结果与非法条件、人物及同一贡献机构、身份前置、申请证据隔离、材料补充、占用过期、审核/撤回竞争、多人竞争门户、共同贡献及仅撤销本人关联、共著路径证据、去重统计和引用未知、单位奖不生成个人名单。

HTTP 测试覆盖：匿名/普通用户后台拒绝、注册不能提升角色、登出撤销令牌、公开查询、400/404、超大 body 413 和错误 JSON。

## 本机数据与运行状态

演示 PostgreSQL 的 `academic` 数据库初始化了 10,000 条明确标注的模拟成果，发布版本 50；这只是数据初始化，不是压力测试。功能脚本另外登记了少量模拟验证人物/账号/申请，不增加规范成果数量。正常启动脚本的默认值仍为 64 条。

本任务创建的数据库容器名为 `academic-group2-pg`，本机映射 55432，仅供开发；主要 API 在 127.0.0.1:8080。本任务的临时第二 API 检查容器为 `academic-group2-api-check`，功能验证后停止。停止主要 API 使用 `scripts/stop-local.ps1`，不会删除数据库。切换到无需 Docker 的 H2 演示可停止 API 后运行 `scripts/start-local.ps1 -NoBuild`。

## 未执行与适用边界

**用户明确要求不在本机压测。本次没有执行任何持续压力/吞吐测试，也没有计算或宣称 P95 达标。** 两请求竞争检查是正确性验证。普通界面显示的单次请求耗时不是 P95。

服务器 k6 脚本已准备，但服务器冷/热缓存性能、1/2 副本比较、4 核 4 GB 稳定性及 HPA 真实扩缩容均待服务器验证。512 MiB 容器能够启动不代表该内存下并发负载已达标。

当前没有真实外部数据源批量接入，也没有真实资料的人工准确率抽样、CodeArts 流程证据或核心模块覆盖率达标报告。详细范围差异见 [验收映射](../acceptance.md)。桌面 EXE 尚未做代码签名，后续需安装器/签名及 .NET LTS 升级；本次运行测试使用当前 Windows 11 开发机。

## 本轮实际修正

1. Boot 4 模块拆分要求显式使用 Flyway starter；补齐后在 H2/PG 上真实执行迁移。
2. H2 将 YEAR 作为关键字；本地连接和测试连接显式配置 `NON_KEYWORDS=YEAR`，服务器 PG 不需要此选项。
3. 审计增加有序序号，避免同一毫秒的多状态迁移按随机 UUID 排序。
4. 注册始终建立 USER；私有申请检查本人/管理员，撤回和审批带版本并落入同一事务。
5. Windows 启动改为执行带哈希的不可变 JAR 副本，避免构建时覆盖运行中 JAR 导致延迟类加载失败。
6. 单位奖详情补充机构展示；引用覆盖分母为零时显示不适用；修改筛选后点翻页会重新从第一页查询。
