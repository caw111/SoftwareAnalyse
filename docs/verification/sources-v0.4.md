# v0.4 固定公告采集与桌面验证

日期：2026-11-17；分支：Group2。本轮功能与低量来源验证结果如下；PostgreSQL和Docker运行验证明确未完成，不视为通过。已有阶段commit：f21a71b（固定来源后端）、ef3101b（结构/TLS修正）、cdbc553（桌面与验证/发布脚本）。文档提交单独进行，未在此声称已推送远程。

设计与范围见 [固定公告来源说明](../design/sources-v0.4.md)、[构件设计](../design/component-design.md)、[数据库 ER](../design/database-er.md)。v0.3 历史结果保留在 [上一轮记录](crawler-v0.3.md)，不能代替本轮代码回归。

## 1. 交付与验证范围

本轮保留 Crossref 论文链路，增加四个固定批次：

| sourceId | batchId | 内容 |
| --- | --- | --- |
| lynu-patents | lynu-grants-2025 | 2025 年授权专利 HTML 清单 |
| nsfc-projects | nsfc-life-key-2019 | 2019 年生命科学部重点项目 HTML 清单 |
| most-awards | most-natural-science-2023 | 2023 年国家自然科学奖 HTML 目录 |
| cnipa-patents | cnipa-25-gold-2025 | 第二十五届中国专利金奖 PDF 附件 |

公告任务仅 BOUNDED、明确创建后启动；预算限制处理的原始行数，仍会下载整份文件。首批事务冻结原文与 parser_version，后续按同一文档分批恢复；不开放任意 URL、其他年度/附件、全站检索、非论文定时或完整日期水位。字段缺失、科学部编号、提名者与完成人、专利权人与发明人保持独立语义。

## 2. 最终验收状态

下表区分已通过、环境原因未验证及未执行的规模验收。中间失败和修正仅保留与结果解释有关的事实。

| 检查 | 最终结果 | 验证证据与范围 |
| --- | --- | --- |
| Java 21 / Gradle / 最终 JAR | 通过 | test与bootJar成功；最终JAR哈希见下表 |
| H2 全套功能测试 | 80项通过，0失败/错误/跳过 | 最终9个套件，包含新增MOST缺表与TLS检查 |
| HTML / PDF 解析专项 | 12项通过 | HTML9项、PDF3项，包含MOST缺表保护 |
| 注册来源任务 / 传输专项 | 12项通过 | 任务集成9项、传输3项，包含TLS拒绝及专用信任边界 |
| PostgreSQL 迁移与功能回归 | 本轮未验证 | Docker引擎pipe不可用、55432未监听；未执行本轮PG测试 |
| WPF Release 编译 | 通过 | 0.4.0最终重发布成功 |
| 自包含 Windows EXE | 通过 | 最终EXE版本0.4.0.0，SHA-256见产物表 |
| 桌面 public / login / workspace / crawl | 四组通过 | 在仅版本文案修正前的0.4 EXE执行；crawl20项，不调用START、不启用定时 |
| 原生窗口及采集小窗口布局 | 通过 | 最终EXE在200%DPI下默认最大化、还原/拖动/最大化/最小化/关闭/图标通过；采集小窗口滚动已过 |
| 四源真实单条及复采 | 8个顺序任务全部通过 | 每任务处理1条，均SUCCESS/LIMIT_REACHED；复采稳定ID、未变1条 |
| Docker 镜像构建/启动/readiness | 本轮未验证 | 引擎pipe仍不可用；停止恢复尝试，未重置/删除卷，不沿用v0.3结论 |
| Compose / k3s 静态检查 | 通过 | Compose config 镜像 0.4.0、三项 CRAWL 变量；k3s 7 资源 YAML 解析通过 |
| ER / 文档检查 | 通过 | V1–V6 对应 32 表、297 字段、44 真实 FK；XML、可编辑图导出、本地链接与 diff 检查通过 |
| 服务器压测、P95、HPA | 未执行 | 按用户要求不在本机压测；保留服务器脚本与验收目标 |

最终H2报告位于artifacts/verification-v0.4/h2-tests.json，生成时间2026-11-17T06:50:59Z。首轮75项为中间结果；末轮增加结构和TLS检查后共80项，不能累加两轮测试次数。

| 测试套件 | 通过项数 |
| --- | ---: |
| CatalogRevisionIntegrationTest | 9 |
| CnipaPatentParserTest | 3 |
| CrawlIntegrationTest | 15 |
| HttpContractTest | 8 |
| PlatformIntegrationTest | 19 |
| RegisteredHtmlParserTest | 9 |
| RegisteredSourceIntegrationTest | 9 |
| RegisteredSourceTransportTest | 3 |
| SearchStatisticsTest | 5 |

桌面本轮四组JSON已生成：public.json、login.json、workspace.json、crawl.json，均为ok=true。采集界面20项检查包括四源Create→STOP、关联新任务回填来源、独立来源设置及小窗口滚动；6条未启动任务最终STOPPED，未调用START，未启用计划，各源间隔已还原。初次原生还原脚本误点了覆盖窗口；修正测试脚本，先确认前台窗口和鼠标目标后，在最终EXE重新执行原生点击/拖动并全部通过，没有为该问题修改产品窗口。四组业务smoke执行后，产品仅修正XAML版本文案v0.3→v0.4并重新发布；未重复业务smoke，最终EXE单独完成原生窗口验证。

## 3. 真实来源证据

### 3.1 页面访问与传输层

2026-11-17 用本机普通 HTTPS 请求核验四个来源页及 CNIPA 金奖附件，均 HTTP 200；四个根 robots.txt 均 HTTP 404。原始 PDF 与 HTML 等价快照、字段样本和哈希保存在 artifacts/source-audit/2026-11-17/，详情及精确官方链接见 [来源说明](../design/sources-v0.4.md)。

这是页面/附件层证据，不能独立证明 Java 信任链、解析、入库、发布和桌面操作全部成功。后续四源各两次真实任务均成功，形成下面的解析、冻结文档、入库与幂等证据。

### 3.2 单条任务与重复采集

每源每任务处理一条，并做一次顺序重复采集；这是低量正确性核验，不是批量抓取或性能测试。下载正文行数与入库预算分开：即使只处理一条，源端返回整份公告。

最终记录时间：2026-11-17T06:52:00Z，结果文件artifacts/verification-v0.4/registered-live.json。八个任务均HTTP200、SUCCESS/LIMIT_REACHED，updated=0、conflicts=0；受BOUNDED预算限制，不推进完整同步水位。

| 来源 | 轮次 | received | inserted | unchanged | 文档总行数 | 业务年 | 公开版本 |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| LYNU | 1 | 1 | 0 | 1 | 28 | 2025 | 3 |
| LYNU | 2 | 1 | 0 | 1 | 28 | 2025 | 3 |
| NSFC | 1 | 1 | 1 | 0 | 115 | 2019 | 4 |
| NSFC | 2 | 1 | 0 | 1 | 115 | 2019 | 4 |
| MOST | 1 | 1 | 1 | 0 | 49 | 2023 | 5 |
| MOST | 2 | 1 | 0 | 1 | 49 | 2023 | 5 |
| CNIPA | 1 | 1 | 1 | 0 | 30 | 未知 | 6 |
| CNIPA | 2 | 1 | 0 | 1 | 30 | 未知 | 6 |

LYNU在先前排查时已入库，因此本轮run1即为unchanged=1；不能把它写成首次新增。其余三个源本轮首次各新增1条；所有run2均未变1条且成果ID稳定。

| 来源 | 规范标识 | 两次相同的成果 ID |
| --- | --- | --- |
| LYNU | CN202420753596.1 | 3898e1be-a2da-4add-9be9-b4fc9c7614a4 |
| NSFC | 3193000529 | 8ede377e-faa2-49eb-8096-1c9e5bf59460 |
| MOST | Z-102-1-01 | ac3c7e30-8c79-4ef8-97b7-b60cf34a8d9c |
| CNIPA | CN202111257655.3 | 2af83ca6-d72c-4af4-94a8-f045c78d9e4f |

| 来源 | 下载原始字节 SHA-256（两次一致） |
| --- | --- |
| LYNU | c2aaa105bab480f1d31a862fe0fd76fbf82f85a39b9188f57b25f8354f16560e |
| NSFC | fc657b7eb9df2e9a6dc3c98f7ba8ecff06742df935d2d29d5c2928d4a95de337 |
| MOST | 31381f40170382d9982a833e34a5a35f4d0fdff211b7b6f91ac21825450567b5 |
| CNIPA | 465df4b59b7cd19a9938de94679dd0ef8364a67c650d470ee985d4ca7db3ff74 |

三个HTML使用registered-html-v1/utf-8，CNIPA使用cnipa-gold-pdf-v1/base64。PDF原字节哈希与保存的Base64文本哈希不同：后者responseChecksum为41fb85c46dea5293c78a1d398f051a24cbb63b87ca93f86847cdbd3ba1da4ebc；脚本对解码原字节重新求SHA-256核对byteChecksum。完整任务ID、HTTP证据与哈希保留于JSON和后台原始页。

首轮 NSFC 任务失败记录在 artifacts/verification-v0.4/registered-live-failure.json：committedPages=0、received=0，未把网络失败解释为有效空表或成功。本机 JDK 的默认证书集合未包含该站证书链需要的 CFCA EV ROOT，已补仅 NSFC 客户端使用的 PKIX 信任锚，相关功能测试与真实NSFC两次任务均通过；不修改系统/JDK truststore，不关闭证书/主机名校验。修正保留正常证书校验，最终NSFC任务均HTTP200、SUCCESS。根证书从Windows已有公有根库导出，按Mozilla官方CCADB指纹核对；DER SHA-256为5CC3D78E4E1D5E45547A04E6873E64F90CF9536D1CCC2EF800F355C4C5FD70FD。实现只用于已登记www.nsfc.gov.cn批次/robots，仍启用HTTPS主机名、PKIX链和有效期校验；TLS_VALIDATION_FAILED为不可重试失败，修复后创建新任务。来源、有效期与维护规则见 [TLS说明](../../backend/src/main/resources/tls/README.md)。

四个解析器当前 sourceUpdatedAt 为 null，抓取时刻不冒充来源修订时间。CNIPA 专利授权日/年未知，NSFC 编号仍为科学部编号；真实结果确认CNIPA year=null、NSFC year=2019，未用网页发布年填充。

## 4. 恢复、权限和一致性验收

本轮80项H2功能测试及对应专项覆盖以下契约；真实低量任务补充了实际文档、日期、哈希和幂等证据，不能替代PostgreSQL或负载验证：

- 参数：未知批次、来源/批次不匹配、公告混入 Crossref 日期条件、公告 INCREMENTAL 或定时设置应拒绝。
- 结构：HTML 必须完整匹配预期数据表；MOST 两个等级表缺一不能成功。PDF 标题、表头、30项结构与解析资源限制检查。
- 预算：recordCount 是整份文件行数，received 是实际处理行数，inserted 是规范新增数；排除、未变与冲突不伪装为新增。
- 原文：首批冻结文档与业务发布同事务；失败回滚，后续恢复不重新抓取更新后的文件；解析器版本、行数或注册地址变化应拒绝混用。
- 发布：稳定成果 ID、原文/规范哈希、旧版可见性、元数据/关系/倒排/目录指针同事务；无可信更晚修订时序的变化进入复核。
- 权限：任务/原始文档仅 ADMIN；公开来源姓名不自动绑定账号、门户或成果；原始 HTML 只以文本查看，不执行网页脚本。
- 来源限制：robots、429与Retry-After、验证码/登录页拒绝、白名单地址、TLS正常校验；不绕过站点限制。

## 5. 产物与重现入口

当前本机路径（构建产物及源文档不提交 Git）：

| 产物 | 路径/结果 |
| --- | --- |
| 最终 EXE | artifacts/windows-x64/AcademicDesktop.exe；SHA-256 479E0C12C4D7E48DDBFA8A76393470D8EDF8CF369DA9C8AD97C3AA6F74CF090B |
| 最终 API JAR | backend/build/libs/academic-platform-api.jar；SHA-256 0430A9880613F4C22CE95408BB8ABB7AE242A116290C9E4D127B6F3069E1DD61 |
| 末轮 H2 报告 | artifacts/verification-v0.4/h2-tests.json，80项全过；本轮没有PG报告 |
| 桌面 JSON / 截图 | artifacts/verification-v0.4/{public,login,workspace,crawl,native-window}.json及对应PNG |
| 四源低量核验 | scripts/verify-registered-sources.ps1；artifacts/verification-v0.4/registered-live.json，8任务通过 |
| Docker 镜像 | 配置目标academic-platform-api:0.4.0；本轮未构建/运行，不提供image ID |

后端使用 Java21 / Gradle 功能测试；PostgreSQL 验证须使用隔离数据库并配置 TEST_DB_URL/TEST_DB_USER/TEST_DB_PASSWORD。桌面通过发布与 workspace 验证脚本检查。真实来源脚本需显式执行，不由普通 build/test 自动联网采集；任务会写入少量真实元数据。

Docker引擎pipe最终仍不可用，本机55432未监听；本轮不继续恢复，不重置Docker、不删除卷或数据库。v0.4的镜像构建/运行和PostgreSQL回归明确未验证；旧版本成功记录不代替本轮结果。

## 6. 未宣称完成的事项

**本机没有运行压测。** 未提供 P95达标、吞吐、4核4GB长期稳定性或HPA收益结论。服务器性能脚本保留，需服务器部署、固定数据/查询集、冷热缓存和完整环境记录后验收。

本轮只覆盖四个固定公告批次；不代表接通 CNIPA/NSFC 通用检索、所有年度/附件、当前专利法律状态、完整人物机构消歧、人工冲突裁决或无限再发布许可。OpenAlex/DBLP、任意公告发现、生产集群/HPA、备份恢复演练仍属后续范围。

