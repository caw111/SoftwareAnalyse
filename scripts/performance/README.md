# 服务器性能验收（尚未执行）

用户明确要求不在本地压测。本目录只有待执行脚本；普通 build、test、启动和打包均不会调用它。当前没有 P95 达标结论。

在隔离的服务器验收环境部署 API + PostgreSQL，准备 ≥10,000 条模拟或真实成果并明确范围。可对**空的验收数据库**设置 `APP_DEMO=true, DEMO_COUNT=10000` 初始化模拟数据。此模式会创建公开文档中的演示密码，只能用在隔离验收环境；生产使用新库和 `APP_DEMO=false`。

安装 [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/)，从独立负载机执行；若负载机和被测服务共机，必须说明竞争 CPU 的偏差。

```sh
BASE_URL=https://academic.example.com \
CONFIRM_SERVER_TEST=yes DATASET=demo CONCURRENCY=20 DURATION_SECONDS=300 \
ENVIRONMENT='server=4cpu/4GB; os=...; postgres=...; jvm=21/...; commit=...; apiReplicas=1; pool=8; client=separate-host; RTT=...' \
k6 run scripts/performance/server-load.js
```

脚本先确认至少 1 万条规范成果，固定发布版本。20 个 VU 预热 30 秒，等待 5 秒结束预热请求，再测量 300 秒。请求混合为 60% 检索、25% 详情、15% 统计；固定 50 组检索条件含合法空集合，其中 10 组非空文本查询使用 relevance 排序，覆盖 v0.3 的倒排与 BM25 路径。测量阶段的独立指标避免将预热混入 P95，慢失败也记入耗时；检验 HTTP 状态、载荷及版本号。阈值为检索 P95 < 2s、详情 < 1s、统计 < 3s、错误率 < 1%；验收报告另列实际错误原因，不能只看阈值绿灯。

输出 `server-load-results.json` 包含参数、查询集、计数、各端点 p50/p95/p99、错误率及元数据。服务端指标来自私有管理端口 `/actuator/prometheus`。生产不暴露 8081 到公网。

需要分别做的服务器试验：

1. 冷启动：重启测试 API，记录启动至 readiness、第一次检索/详情/统计及当时数据库缓存状态，独立成表。脚本 setup 的第一次请求不自动代表冷缓存。
2. 固定 1 副本基线：记录 CPU、RSS、GC、Hikari active/pending、数据库慢查询/连接数、网络 RTT；确认压测器自身没有饱和。
3. 固定 2 副本：保持数据集、请求集和数据库不变，比较吞吐/尾延迟。进程缓存分别预热，不将数据库瓶颈解释为自动扩容失效。
4. HPA：在服务器上观察升至 2 副本、稳定窗口及降回 1 副本，记录 Kubernetes 事件。默认 CPU 指标可能无法捕获数据库等待，应结合连接池和查询耗时判断。
5. 扩展不同查询集、冷缓存、随机/深分页与写入竞争。固定热查询不能证明 10 万条、真实中文相关度、突发流量或持续写入下达标。

可以使用 `kubectl top pods -n academic`、`kubectl get hpa -n academic -w`、`docker stats` 和 PostgreSQL 慢查询日志。结果提交到 `docs/verification/` 时保留硬件配置、测试日期、代码提交、数据来源与模拟占比，勿提交令牌或密码。
