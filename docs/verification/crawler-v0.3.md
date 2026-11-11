# v0.3 采集、版本、检索与桌面验证

日期：2026-11-11；分支：Group2。开始修改前创建了本地附注 tag **v0.2.0**，指向 `d083098089f2387232b99aacbc686c35ec37bf32`。本轮 commit 分为后端构件、桌面采集管理、访问拒绝修正、设计与部署记录。未推送远程。

## 本轮交付

- 管理员“成果数据库管理 → 来源采集”创建、显式启动/停止/重试、按原范围关联新任务、查看原始页/日志/处理计数、配置服务器定时计划。WPF 原生桌面，关闭客户端不停止已启动的服务器任务。
- Crossref DOI 定向、ISSN/关键词、固定索引日期窗及可选出版年；BOUNDED 原始记录预算与 INCREMENTAL 完整窗口语义分开。定时默认关闭。
- 持久化来源租约、attempt/token 校验、跨副本请求间隔、Retry-After、robots/HTTP 缓存、访问拒绝暂停定时计划。原文/规范修订/倒排/游标/发布版本同页事务。
- 稳定成果 ID、来源内容哈希与观测、跨源/过期/规则重处理冲突保留；历史检索、详情、贡献和统计读取不可变修订。
- 同库倒排与加权 TF 的 BM25 变体，精确 DOI 优先、中英词项、稳定分页；按成果去重的热点文档频次、年度分母和质量覆盖率。
- [构件设计](../design/component-design.md)、[数据库 ER](../design/database-er.md)、Mermaid 与三页可编辑 draw.io：31 表、283 字段、43 条真实外键。

## 验证结果

| 检查 | 实际结果 |
| --- | --- |
| Java 21 / Gradle | test、bootJar 成功 |
| H2 功能测试 | 56 项通过，0 失败 |
| PostgreSQL 17 功能测试 | 同一套 56 项通过，0 失败；复用原测试库，V1/V2 升级到 V5，重复执行可用 |
| 数据修订专项 | 9 项：稳定 ID、旧版结果、原文版本、观测、冲突与规则提案、回滚等 |
| 采集专项 | 15 项：双模式预算、逐页断点、429/Retry-After、停止边界、旧租约拒绝、双执行器争用、缓存/304、规则拒绝、稳定不透明游标、坏条目隔离、访问熔断 |
| 检索/统计专项 | 5 项：标题权重、精确 DOI、中文/拉丁单字及 C++、完整候选排序/分页、机构去重、已知零与未知引用、热点分母及未知年份 |
| HTTP/既有业务 | 27 项：登录、角色隔离、申请竞争、撤回、配置错误及新采集/质量接口权限 |
| 桌面自包含发布 | Windows x64 EXE 0.3.0；最终发布成功，无 C# 编译警告 |
| 桌面功能 | public、login、workspace、crawl 通过；crawl 真实点击创建/停止/关联新建/设置往返，未点击 START，未启用定时计划 |
| 窗口 | 200% DPI 下默认最大化、原生标题栏拖动、最大化/还原、最小化、关闭、图标验证通过；960×560 采集设置可滚动访问 |
| 真实来源联通 | 下述单 DOI 两次顺序任务成功；不是批量或负载测试 |
| Docker | 镜像 `academic-platform-api:0.3.0` 构建成功；非 root、只读文件系统、512 MiB 约束连接 PostgreSQL 启动，readiness UP、目录查询成功；检查容器随后停止 |
| 部署模板 | Compose config 验证含 CRAWL 覆盖值；k3s 7 个资源 YAML 及可选 Secret 引用解析通过，未应用到集群 |
| 设计图与压测脚本 | draw.io XML 解析并实际导出通过；k6 脚本仅执行 node --check 语法检查，没有运行 k6 |

H2 与 PostgreSQL 均关闭测试上下文的自动 worker，采集单测显式驱动本机 mock HTTP 来源。两执行器竞争是有界正确性检查，不是压测。重复 PostgreSQL 验证发现旧用例假定某人永远只在一个机构，已改为独立贡献关系 fixture，避免其他测试的历史署名污染断言。

Docker Desktop 本次启动曾出现本地 socket 错误，普通 stop/start 恢复；没有重置 Docker、删除卷或删除数据库。桌面验证中后端被手动关闭导致一次连接失败，重启后重跑采集界面成功，结果文件已更新。

## 单 DOI 真实请求证据

来源：`https://api.crossref.org/works/10.1038/nphys1170`；检查时间：2026-11-11 12:30:56 UTC。

| 顺序 | 状态 | 接收 | 新增 | 更新 | 未变 | 公开版本 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 首次 | SUCCESS / SOURCE_EXHAUSTED | 1 | 1 | 0 | 0 | 2 |
| 复采 | SUCCESS / SOURCE_EXHAUSTED | 1 | 0 | 0 | 1 | 2 |

论文题名 Measured measurement；两次成果 ID 均为 `f1d7b535-7e7a-4861-80d3-5f3b634ad78c`。两次 HTTP 200，响应 SHA-256 均为 `46c9fb57b8bf4a43f41e21ece34a4a79f93a55276fa749a80dbd8fedb939c177`。原始页面在本机任务详情可查；单 DOI 不推进全窗同步水位。当前未配置维护者邮箱，使用真实公共池，没有填写虚构联系地址。

## 本机构建与重现

当前本机产物（不提交 Git）：

- `artifacts/windows-x64/AcademicDesktop.exe`，SHA-256 `6CEBFE481C8774978AF6F64B80D826BB1ABD14FD3DA5E817281F5D863246CF3D`。
- `backend/build/libs/academic-platform-api.jar`，SHA-256 `B8433E04CAF4B36A62D791B13C62BB807F71A4D4DC1C9F2E60217CAAAEF463D1`。
- Docker image ID `sha256:8a202a37d2643033d9f899818194b21e620a24be187a9f5298bb166860fea9fd`。
- `artifacts/verification-v0.3/` 保存 H2/PG 计数、四组桌面 JSON、原生窗口 JSON、截图和 live-crawl.json；重新构建会改变产物哈希。

后端测试：`gradle -p backend test`；PostgreSQL 时设置 TEST_DB_URL/TEST_DB_USER/TEST_DB_PASSWORD 并使用隔离验收库。桌面：`scripts/publish-desktop.ps1`、`scripts/verify-desktop-workspace.ps1 -CheckWindowControls`。单条真实请求脚本：`scripts/verify-crawl-one-doi.ps1`，只允许 loopback 演示 API，两个一条 DOI 的顺序任务，会写入真实元数据；不由普通 build/test 自动执行。

## 仍待服务器或后续迭代验证

本机未运行压测，没有 P95 达标、吞吐、HPA 收益或 4 GB 长期稳定性的结论。服务器脚本仍为 50 条固定查询、至少 10,000 成果、20 并发、预热后测量；文本查询覆盖 relevance，需独立评价相关度与资源消耗。

真实接通的采集来源目前仅 Crossref。OpenAlex、DBLP、专利/项目/获奖来源已写适配契约和字段规则，尚未接通；不能据此声称所有成果类型都有真实爬虫。机构消歧、完整人工冲突裁决、软删除传播、历史版本回收和异步预聚合尚未交付。生产部署前配置真实联系邮箱、凭证和 TLS，并在服务器执行性能/容量验收。
