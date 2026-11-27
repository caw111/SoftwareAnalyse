# 需求 设计 实现追踪表

初次逐项核对日期为 2026 年 11 月 25 日，当时本地 Group2 提交为 `d083098`。追踪覆盖 SRS 的全部 104 条 FR、42 条 AC、15 条 AN-AT、3 条 AN-UC、21 条统计与成果管理 UC，以及课程工程交付和非功能目标。

## 当前基线同步

2026 年 11 月 25 日读取 GitHub 后发现远端 Group2 已推进到 `9b77cb7`，随后本地完成快进同步。下方第 1–11 节保留 d083098 的初次核对快照，其中实现状态、测试数量和测试行号均属于旧提交。当前实施优先使用本节、[v0.5 验收映射](acceptance.md)、[当前构件设计](design/component-design.md)及[流水线操作与验证](pipeline.md)。

| 原追踪范围 | 远端已有进展 | 当前仍需核验或完善 |
| --- | --- | --- |
| CRAWL、SYNC、AN-UC-01 | 已有 Crossref 与三个注册公告批次、持久化任务、租约、停止、断点及重试 | 任意来源接入、完整数据规模、人工质量抽样 |
| ES、SEARCH、AN-UC-03 | 已有同库倒排 BM25、不可变目录修订和原子发布 | 外部搜索引擎属于架构差异，查询质量评估及其余字段条件仍需完善 |
| STAT、INNOV | 已有热点时间桶、同版统计及路径 | 确认统计、完整网络交互及算法边界专项验收 |
| NF-04、ENG-05 | 后端测试已增至 83 项，历史 H2/PostgreSQL 各通过 | 覆盖率、当前提交运行报告和未完成业务场景 |
| ENG-02～04、NF-06 | 已有 GitHub Actions 五阶段、GHCR 摘要发布、受限 SSH 部署、健康检查和失败应用回滚 | 本轮补本地工具识别及打包 EXE 对同次 JAR 的集成检查，实际备份恢复演练后续执行 |
| NF-07 | v0.5.1 自带运行时 EXE，默认通过内置 CA 校验连接正式 HTTPS API | 本机 SDK 发现、统一构建入口及最新产物连通验证 |

此前按旧快照统计的状态数量不能用于当前版本完成率。后续功能迭代按当前代码逐项重新核定相关 FR，原快照代码和测试已改为对应提交的永久链接。

工程流程按用户确认采用 GitHub。需求、SPEC 和原始设计保留已有编号，本文记录实施对应关系及差异。设计来源使用 GitHub 已归档材料的固定提交链接，旧基线代码和测试使用 d083098 的永久链接。课程课件按用户提供附件标识来源。

本次状态来自源码、模型、测试代码和历史验收记录的静态核对。历史通过记录见 E01、E02，该旧提交的结果沿用历史记录，当前版本执行结果见流水线文档。实现状态与最终验收分别记录，带有测试编号只表示该用例支撑对应行为，其覆盖范围以测试断言为准。

## 1 状态及使用方式

| 状态 | 判定 | 后续处理 |
| --- | --- | --- |
| 已实现 | 当前代码覆盖该条主要行为 | 在最终环境回归并补证据 |
| 部分实现 | 仅覆盖部分子要求或存在设计差异 | 按最后一列补齐并复验 |
| 未实现 | 运行代码尚无对应完整能力 | 依赖排序后实现和验收 |
| 后续 P1 | SRS 明确列为后续账户工具或推荐能力 | 启用时纳入版本范围与验收 |

本文的 C、D、T、S、E 编号是文件和测试定位索引。AN-AT/AC 保持原始编号。负责人、GitHub Issue、PR 和最终运行链接由实际任务指派及执行后填写。

## 2 需求和设计基线

| 索引 | 来源 | 使用范围 |
| --- | --- | --- |
| B01 | [系统需求规格说明书_SRS.md](../前期成果/需求调研和建模/docs/系统需求规格说明书_SRS.md) | 全部 FR、UC、AC 和非功能目标 |
| B02 | [核心模块开发规范_SPEC.md](../前期成果/需求调研和建模/docs/核心模块开发规范_SPEC.md) | 9 项 SPEC 的处理约束与验收 |
| D01 | [学术成果分享平台_需求分析报告_v1.0.md](../前期成果/需求分析/docs/学术成果分享平台_需求分析报告_v1.0.md) | §3–4 核心类、§6–8 三条时序、§9 状态、§12 追踪；draw.io 源在同目录上级 image 下 |
| D02 | [面向对象设计与构件设计说明书.docx](https://github.com/caw111/SoftwareAnalyse/blob/9b9d25ea317b27e5a57d60738621036e43e3aa6c/docs/%E4%BD%9C%E4%B8%9A5-%E9%9D%A2%E5%90%91%E5%AF%B9%E8%B1%A1%E8%AE%BE%E8%AE%A1%E5%8E%9F%E5%88%99%E5%92%8C%E6%A8%A1%E5%BC%8F/%E9%9D%A2%E5%90%91%E5%AF%B9%E8%B1%A1%E8%AE%BE%E8%AE%A1%E4%B8%8E%E6%9E%84%E4%BB%B6%E8%AE%BE%E8%AE%A1%E8%AF%B4%E6%98%8E%E4%B9%A6.docx) | 类职责、模式、§4 协作、§5–7 UI、§8 算法 |
| D03 | [接口设计说明书.docx](https://github.com/caw111/SoftwareAnalyse/blob/9b9d25ea317b27e5a57d60738621036e43e3aa6c/docs/%E4%BD%9C%E4%B8%9A5-%E9%9D%A2%E5%90%91%E5%AF%B9%E8%B1%A1%E8%AE%BE%E8%AE%A1%E5%8E%9F%E5%88%99%E5%92%8C%E6%A8%A1%E5%BC%8F/%E6%8E%A5%E5%8F%A3%E8%AE%BE%E8%AE%A1%E8%AF%B4%E6%98%8E%E4%B9%A6.docx) | REST、查询、认领动作、异步采集及错误契约 |
| D04 | [数据库设计说明书.docx](https://github.com/caw111/SoftwareAnalyse/blob/9b9d25ea317b27e5a57d60738621036e43e3aa6c/docs/%E4%BD%9C%E4%B8%9A5-%E9%9D%A2%E5%90%91%E5%AF%B9%E8%B1%A1%E8%AE%BE%E8%AE%A1%E5%8E%9F%E5%88%99%E5%92%8C%E6%A8%A1%E5%BC%8F/%E6%95%B0%E6%8D%AE%E5%BA%93%E8%AE%BE%E8%AE%A1%E8%AF%B4%E6%98%8E%E4%B9%A6.docx) | 概念模型、事务、修订、索引与安全 |
| D05 | [系统架构设计说明书.docx](https://github.com/caw111/SoftwareAnalyse/blob/9b9d25ea317b27e5a57d60738621036e43e3aa6c/docs/%E4%BD%9C%E4%B8%9A4-%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1/%E7%B3%BB%E7%BB%9F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E8%AF%B4%E6%98%8E%E4%B9%A6.docx) | 现有实现与目标架构、Worker、CSS、部署及 ADR |
| D06 | [设计类模型.drawio](https://github.com/caw111/SoftwareAnalyse/blob/9b9d25ea317b27e5a57d60738621036e43e3aa6c/images/%E4%BD%9C%E4%B8%9A5-%E9%9D%A2%E5%90%91%E5%AF%B9%E8%B1%A1%E8%AE%BE%E8%AE%A1%E5%8E%9F%E5%88%99%E5%92%8C%E6%A8%A1%E5%BC%8F/%E8%AE%BE%E8%AE%A1%E7%B1%BB%E6%A8%A1%E5%9E%8B.drawio) | 可编辑目标设计类图 |
| D07 | [02_数据采集入库时序图.drawio](../前期成果/需求分析/image/02_数据采集入库时序图.drawio) | AN-UC-01 交互模型 |
| D08 | [03_门户认领审核时序图.drawio](../前期成果/需求分析/image/03_门户认领审核时序图.drawio) | AN-UC-02 交互模型 |
| D09 | [04_检索请求处理时序图.drawio](../前期成果/需求分析/image/04_检索请求处理时序图.drawio) | AN-UC-03 交互模型 |
| E01 | [README.md](../docs/verification/v0.2/README.md) | 2026-11-09 的 27 项 H2/PostgreSQL 测试与桌面历史验证 |
| E02 | [first-version.md](../docs/verification/first-version.md) | 首版历史构建、功能及容器记录 |
| E03 | 课程附件 ssad10.设计后.pdf（用户提供，本地路径 `ppt/ssad10.设计后.pdf`） | 第 22、30、44、47–50、58 页的工程和交付要求 |

## 3 代码和测试定位

### 3.1 d083098 实现入口

| 索引 | 文件 | 当前职责 |
| --- | --- | --- |
| C01 | [AuthService.java](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/java/cn/edu/group2/academic/AuthService.java) | register、login、require、profile、logout；AuthController 转换 HTTP |
| C02 | [ClaimService.java](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/java/cn/edu/group2/academic/ClaimService.java) | create、validateTarget、action、authorize、detail、page、myOutcomes |
| C03 | [CatalogService.java](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/java/cn/edu/group2/academic/CatalogService.java) | query、filter、search、detail、stats、scholars、referenceData；CatalogController 暴露公开接口 |
| C04 | [ImportService.java](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/java/cn/edu/group2/academic/ImportService.java) | normalizeDoi、normalize、ingest、audit |
| C05 | [WorkflowController.java](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/java/cn/edu/group2/academic/WorkflowController.java) | 身份/认领、profile、statistics、institution、scholar、imports、audit 的 HTTP 入口 |
| C06 | [GraphService.java](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/java/cn/edu/group2/academic/GraphService.java) | load、path 和 GraphController；BFS、图容量限制及证据 |
| C07 | [MainWindow.Workspace.cs](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/frontend/AcademicDesktop/MainWindow.Workspace.cs) | 角色导航、资料维护、身份/门户认证、本人申请和管理员统计 |
| C08 | [MainWindow.xaml.cs](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/frontend/AcademicDesktop/MainWindow.xaml.cs) | Query、Search、ShowDetail、LoadScholars、ScholarWorks、LoadStats、FindPath、申请与审核事件 |
| C09 | [ApiClient.cs](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/frontend/AcademicDesktop/ApiClient.cs) | 异步 HTTP、令牌及错误反馈；LoginWindow 负责独立登录/注册/访客入口 |
| C10 | [V1__initial.sql](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/resources/db/migration/V1__initial.sql) | 规范成果、贡献、来源、申请、唯一绑定、审计和目录发布表 |
| C11 | [V2__personal_profiles.sql](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/resources/db/migration/V2__personal_profiles.sql) | 个人资料和乐观版本字段 |
| C12 | [ProfileService.java](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/java/cn/edu/group2/academic/ProfileService.java) | update；资料字段、ORCID、URL、对象权限及版本更新 |
| C13 | [ApiErrors.java](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/main/java/cn/edu/group2/academic/ApiErrors.java) | API 错误协议；RequestLimits 限制请求体 |

C01–C06 的持久化事实由 C10 提供，个人资料由 C11、C12 补充。目标设计中的 SourceAdapter、独立 Worker、SearchStrategy、PublicationService 和 outbox 当前仍需实施。

### 3.2 d083098 测试代码

T01–T19 为 Spring 集成测试，T20–T27 为 HTTP 契约测试。当前仓库尚无独立单元测试层与行覆盖率报告。

| 索引 | 测试方法与位置 |
| --- | --- |
| T01 | [PlatformIntegrationTest.defaultsNeverMixSimulatedWithReal](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L41) |
| T02 | [PlatformIntegrationTest.invalidQueryIsDifferentFromEmptyResult](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L45) |
| T03 | [PlatformIntegrationTest.samePersonInstitutionMustBelongToSameContribution](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L50) |
| T04 | [PlatformIntegrationTest.normalizeDoiAndDoNotInventDatePrecision](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L55) |
| T05 | [PlatformIntegrationTest.replayAndCrossSourceDoiDoNotDuplicateWork](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L61) |
| T06 | [PlatformIntegrationTest.failedBatchRollsBackWorkAndReleaseAndSource](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L68) |
| T07 | [PlatformIntegrationTest.previousReleaseSurvivesNewPublication](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L75) |
| T08 | [PlatformIntegrationTest.applicantEvidenceIsPrivate](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L82) |
| T09 | [PlatformIntegrationTest.ordinaryAccountCannotClaimPortalBeforeIdentityApproval](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L88) |
| T10 | [PlatformIntegrationTest.submittingEditedDraftSavesMaterialAndRejectsStaleVersion](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L94) |
| T11 | [PlatformIntegrationTest.blankDraftMaterialIsRejectedAndOmittedMaterialPreservesLegacyDraft](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L106) |
| T12 | [PlatformIntegrationTest.supplementPreservesHistoryAndIncreasesMaterialVersion](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L120) |
| T13 | [PlatformIntegrationTest.expiredReviewLeaseCannotApproveButCanBeRetaken](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L126) |
| T14 | [PlatformIntegrationTest.concurrentApprovalAndWithdrawalHaveExactlyOneWinner](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L132) |
| T15 | [PlatformIntegrationTest.concurrentCompetingPortalClaimsCannotCreateTwoOwners](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L139) |
| T16 | [PlatformIntegrationTest.coauthorsCanBothClaimAndRevokeOnlyOwnRelationship](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L145) |
| T17 | [PlatformIntegrationTest.graphReturnsEvidenceAndDistinguishesSameNamePeople](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L155) |
| T18 | [PlatformIntegrationTest.statisticsCountCanonicalWorksAndSeparateUnknownCitations](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L160) |
| T19 | [PlatformIntegrationTest.organizationAwardKeepsInstitutionWithoutInventingPeople](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/PlatformIntegrationTest.java#L165) |
| T20 | [HttpContractTest.publicCatalogAndExplicitClientErrors](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/HttpContractTest.java#L32) |
| T21 | [HttpContractTest.anonymousAndReaderCannotAccessAdmin](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/HttpContractTest.java#L39) |
| T22 | [HttpContractTest.logoutRevokesTokenAndRegistrationDoesNotAcceptRoleEscalation](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/HttpContractTest.java#L48) |
| T23 | [HttpContractTest.oversizedAndInvalidPayloadsAreRejected](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/HttpContractTest.java#L56) |
| T24 | [HttpContractTest.personalProfilePersistsWithoutEscalatingPermissionsOrChangingAnotherAccount](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/HttpContractTest.java#L73) |
| T25 | [HttpContractTest.staleProfileEditCannotOverwriteNewerValues](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/HttpContractTest.java#L94) |
| T26 | [HttpContractTest.unsafeLinksInvalidOrcidAndUnboundedProfilesAreRejectedAtomically](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/HttpContractTest.java#L107) |
| T27 | [HttpContractTest.pagedApplicationsIncludeOnlyOwnerAndAdminSummaryRequiresAdmin](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/backend/src/test/java/cn/edu/group2/academic/HttpContractTest.java#L123) |
| S01 | [MainWindow.RunSmoke](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/frontend/AcademicDesktop/MainWindow.xaml.cs#L376)，由 [工作区验证脚本](../scripts/verify-desktop-workspace.ps1)以 `--smoke` 组织公共页验收 |
| S02 | [LoginWindow.RunLoginSmoke](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/frontend/AcademicDesktop/LoginWindow.Smoke.cs#L18) 与 [MainWindow.RunWorkspaceSmoke](https://github.com/caw111/SoftwareAnalyse/blob/d083098089f2387232b99aacbc686c35ec37bf32/frontend/AcademicDesktop/MainWindow.Smoke.cs#L20)，分别以 `--login-smoke`、`--workspace-smoke` 验证入口和角色工作区 |

S01、S02 是桌面自动化入口，具体历史运行结果见 E01。表内“—”表示本次未定位到针对该要求的专项用例。

## 4 功能需求逐项追踪

| 实现状态 | 条数 |
| --- | --- |
| 已实现 | 8 |
| 部分实现 | 49 |
| 未实现 | 33 |
| 后续 P1 | 14 |

计数按完整 FR 判定，部分实现的剩余子要求仍属于待交付范围。

### 4.1 AUTH

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-AUTH-001 用户注册 | SPEC-CLAIM-01；D02 §4.2、6；D03 §2.1 | C01、C02、C07 | 已实现 | T22 | 用户名注册并固定创建 USER；补独立重复用户名、口令边界用例 |
| FR-AUTH-002 用户登录 | SPEC-CLAIM-01；D02 §4.2、6；D03 §2.1 | C01、C02、C07 | 已实现 | T22 | 账号口令登录、会话和登出；补错误口令、过期会话专项用例 |
| FR-AUTH-003 角色权限 | SPEC-CLAIM-01；D02 §4.2、6；D03 §2.1 | C01、C02、C07 | 已实现 | T21 T22 T27 | 服务端校验 USER、RESEARCHER、ADMIN 和对象权限 |
| FR-AUTH-004 科研人员身份申请 | SPEC-CLAIM-01；D02 §4.2、6；D03 §2.1 | C01、C02、C07 | 部分实现 | T09 S02 | 已有 IDENTITY 申请；缺机构选择及机构审核衔接 |
| FR-AUTH-005 身份审核 | SPEC-CLAIM-01；D02 §4.2、6；D03 §2.1 | C01、C02、C07 | 已实现 | T09 S02 | 管理员人工审核后授权；外部身份核验另见 AN-AT-08 |

### 4.2 SEARCH

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-SEARCH-001 关键词检索 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | T20 | search_text 仅拼接标题、DOI、编号、摘要；缺作者、载体和学科文本查询 |
| FR-SEARCH-002 字段检索 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | T03 | 支持 scholar ID 过滤；DOI 为包含匹配，缺独立精确 DOI 和载体字段查询 |
| FR-SEARCH-003 条件过滤 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | T03 | 已有年份、人物、机构、领域、类型；缺出版商、OA、载体及未分类专用过滤 |
| FR-SEARCH-004 排序 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | — | 已有年份降序、引用降序和标题排序；缺 BM25 与日期升序 |
| FR-SEARCH-005 分页 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | T20 S01 | API 每页 1–50、桌面固定 20；需对齐 10/20/50/100、回退与跨页条件恢复 |
| FR-SEARCH-006 搜索结果信息 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | S01 | 列表已有标题、贡献者、年份等；缺摘要匹配片段及逐字段 UI 验收 |
| FR-SEARCH-007 条件逻辑与人物确认 P0 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | T03 S01 | 已按人物 ID 和跨维度 AND 筛选；缺同维度多选 OR、领域层级和完整空查询顺序约定 |
| FR-SEARCH-008 贡献人与机构条件 P0 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 已实现 | T03 | CatalogService.filter 在同一贡献记录内关联人物与署名机构 |
| FR-SEARCH-009 类型专属字段 P0 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | T04 | 编号进入通用文本；缺四类型专属查询参数、适用性校验及条件切换说明 |
| FR-SEARCH-010 结果状态与合并导航 P0 | SPEC-SEARCH-01；D01 检索时序；D02 §4.3、8.3；D04 §4 | C03、C08 | 部分实现 | T07 T18 | 引用缺失置后及来源可读；缺撤稿/冲突状态、排除撤稿和合并旧 ID 导航 |

### 4.3 PAPER

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-PAPER-001 基本元数据展示 | SPEC-SEARCH-01；D02 §4.3、5；D03 §2 | C03、C08 | 部分实现 | S01 | 详情有题录、贡献者、摘要、来源及 details；缺出版商等字段的结构化契约和完整显示验收 |
| FR-PAPER-002 出版社跳转 | SPEC-SEARCH-01；D02 §4.3、5；D03 §2 | 待实现 | 未实现 | — | 桌面现有按钮打开原始来源；需独立 DOI Resolver 出版社入口 |
| FR-PAPER-003 OA 状态 | SPEC-SEARCH-01；D02 §4.3、5；D03 §2 | C03、C08 | 部分实现 | T18 S01 | 已展示 OPEN/NOT_FOUND/UNKNOWN；缺 OA 状态来源字段及展示 |
| FR-PAPER-004 OA 访问入口 | SPEC-SEARCH-01；D02 §4.3、5；D03 §2 | 待实现 | 未实现 | — | 需有来源的 OA landing page/PDF 地址和访问入口 |
| FR-PAPER-005 参考文献 | SPEC-SEARCH-01；D02 §4.3、5；D03 §2 | 待实现 | 未实现 | — | 需参考文献关系、列表和本地 DOI 内链 |
| FR-PAPER-006 引用次数 | SPEC-SEARCH-01；D02 §4.3、5；D03 §2 | C03、C08 | 部分实现 | T18 | 已存引用数及来源；缺真实 Crossref 同步和引用最近同步时间展示 |
| FR-PAPER-007 相关推荐 | SPEC-SEARCH-01；D02 §4.3、5；D03 §2 | 待实现 | 后续 P1 | — | 随 FR-REC 实现推荐、理由及不足候选处理 |

### 4.4 PORTAL

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-PORTAL-001 个人门户 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | S01 S02 | 已有学者简介、按 scholar 筛选和个人已确认列表；缺公开门户中候选/确认成果分区及确认统计 |
| FR-PORTAL-002 搜索待认领成果 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | S02 | 现有检索与成果申报入口；专属字段查询依赖 SEARCH-009 |
| FR-PORTAL-003 成果认领申请 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 已实现 | T16 S02 | 校验科研身份、门户、贡献角色、已有关系和在审重复 |
| FR-PORTAL-004 成果认领审核 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 已实现 | T16 S02 | 审核批准、驳回、补充；授权与状态审计处于同一事务 |
| FR-PORTAL-005 认领撤销 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | T16 | 本人撤销审核保留共享成果和他人关系；缺管理员独立治理纠正关系入口 |
| FR-PORTAL-006 成果信息维护边界 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | — | 已有公共元数据写入边界；缺本人标签、成果说明、展示顺序与纠错申请 |
| FR-PORTAL-007 门户认领申请 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | T09 S02 | 已有既有门户申请；缺无对应门户时的申请新建流程 |
| FR-PORTAL-008 门户认领审核 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 已实现 | T15 S02 | 角色和门户对象分开授权，事务校验唯一绑定，竞争转人工处理 |
| FR-PORTAL-009 候选资料标识 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | S01 | scholars.claimed 及来源关系与 outcome_binding 分存；缺门户成果逐项候选标识验收 |
| FR-PORTAL-010 补录与纠错 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | 待实现 | 未实现 | — | 需补录/纠错申请、类型字段、审核和后续发布流程 |
| FR-PORTAL-011 本人申请查询 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | T08 T27 S02 | 本人申请分页与私有材料隔离已有；补录/纠错两类尚缺 |
| FR-PORTAL-012 补充、撤回与再次申请 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | T10 T11 T12 S02 | 已有补充、撤回、终态保护和新申请；材料仅计版本，缺历次原文快照及再申请历史关联 |
| FR-PORTAL-013 审核并发与状态反馈 | SPEC-CLAIM-01；D01 门户时序；D02 §4.2、6；D04 §3 | C02、C07、C08 | 部分实现 | T13 T14 | 已有锁、版本校验、审核租约和状态反馈；租约超时为重新领取时惰性释放，外部核验失败路径待补 |

### 4.5 INST

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-INST-001 机构查询 | SPEC-DATA-03、SPEC-CLAIM-01；D02 §1.1、6；D04 §1、3 | C03、C05、C07 | 部分实现 | — | GET /api/reference 返回机构词表；缺独立机构搜索和分页接口 |
| FR-INST-002 机构注册申请 | SPEC-DATA-03、SPEC-CLAIM-01；D02 §1.1、6；D04 §1、3 | 待实现 | 未实现 | — | 需普通登录用户可提交机构注册申请及规定字段 |
| FR-INST-003 机构审核 | SPEC-DATA-03、SPEC-CLAIM-01；D02 §1.1、6；D04 §1、3 | 待实现 | 未实现 | — | 现有 IDENTITY 审核用于科研身份；需机构注册审核独立流程 |
| FR-INST-004 机构去重 | SPEC-DATA-03、SPEC-CLAIM-01；D02 §1.1、6；D04 §1、3 | C03、C05、C07 | 部分实现 | — | 机构 ID 主键防重复；缺名称、域名、ROR 候选复核和规范机构归并 |

### 4.6 INDEXREQ

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-INDEXREQ-001 提交索引更新申请 | SPEC-INGEST-01、SPEC-CLAIM-01；D02 §4.1、6；D03 §3 | 待实现 | 未实现 | — | 需索引补采申请及幂等提交 |
| FR-INDEXREQ-002 自动预检查 | SPEC-INGEST-01、SPEC-CLAIM-01；D02 §4.1、6；D03 §3 | 待实现 | 未实现 | — | 需 DOI/题名/来源/重复预检查并返回明确结果 |
| FR-INDEXREQ-003 管理员审核 | SPEC-INGEST-01、SPEC-CLAIM-01；D02 §4.1、6；D03 §3 | 待实现 | 未实现 | — | 需索引补采申请的管理员审核 |
| FR-INDEXREQ-004 定向采集 | SPEC-INGEST-01、SPEC-CLAIM-01；D02 §4.1、6；D03 §3 | 待实现 | 未实现 | — | 需审核通过后发起定向采集并关联任务 |
| FR-INDEXREQ-005 申请状态追踪 | SPEC-INGEST-01、SPEC-CLAIM-01；D02 §4.1、6；D03 §3 | 待实现 | 未实现 | — | 需分别跟踪审核、采集、索引和公开可见状态 |

### 4.7 CRAWL

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-CRAWL-001 初始采集 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | 待实现 | 未实现 | — | 现有 JSON 批次导入可复用；需真实来源初始采集链 |
| FR-CRAWL-002 采集范围 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | 待实现 | 未实现 | — | 需数据源配置、许可用途、固定采集范围及分类依据 |
| FR-CRAWL-003 Cursor 分页 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | 待实现 | 未实现 | — | 需真实来源 Cursor 分页和断点提交 |
| FR-CRAWL-004 数据清洗 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | C04（结构化导入基础） | 部分实现 | T04 T19 | 已有 Unicode/空白、DOI、日期及角色校验；缺真实源解析、HTML 清洗、隔离原因与规则版本 |
| FR-CRAWL-005 去重 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | C04（结构化导入基础） | 部分实现 | T05 | 已有强标识与来源稳定键去重；缺弱匹配候选及冲突复核队列 |
| FR-CRAWL-006 Upsert | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | C04（结构化导入基础） | 部分实现 | T05 T06 | 重复导入保留来源观测；已有规范字段不更新，缺有依据的字段修订和锁定冲突处理 |
| FR-CRAWL-007 原始数据留存 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | C04（结构化导入基础） | 部分实现 | T05 | source_record 保存导入 DTO JSON、哈希和来源地址；需额外保留原始 HTTP 响应和解析版本 |
| FR-CRAWL-008 失败重试 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | 待实现 | 未实现 | — | 需失败分类、退避、重试预算和执行历史 |
| FR-CRAWL-009 来源响应与接入验证 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | 待实现 | 未实现 | — | 需区分 412/429、JS 外壳、结构变化与有效空响应 |
| FR-CRAWL-010 文献体裁与候选数据质量 | SPEC-INGEST-01、SPEC-DATA-01/02；D01 采集时序；D02 §4.1、8.1–8.2 | 待实现 | 未实现 | — | 需文献体裁规则、研究论文候选判定及排除依据 |

### 4.8 SYNC

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-SYNC-001 定时任务 | SPEC-INGEST-01；D01 采集时序；D02 §4.1、8.1；D03 §3 | 待实现 | 未实现 | — | 需持久化调度与增量执行 |
| FR-SYNC-002 Checkpoint | SPEC-INGEST-01；D01 采集时序；D02 §4.1、8.1；D03 §3 | 待实现 | 未实现 | — | 需页检查点、成功水位和崩溃恢复 |
| FR-SYNC-003 有界时间窗口 | SPEC-INGEST-01；D01 采集时序；D02 §4.1、8.1；D03 §3 | 待实现 | 未实现 | — | 需固定时间窗口并约束恢复时沿用原窗口 |
| FR-SYNC-004 任务状态机 | SPEC-INGEST-01；D01 采集时序；D02 §4.1、8.1；D03 §3 | 待实现 | 未实现 | — | import_task 只有批次运行/成功语义；需六状态、租约、停止确认和旧执行器隔离 |
| FR-SYNC-005 手动补采 | SPEC-INGEST-01；D01 采集时序；D02 §4.1、8.1；D03 §3 | 待实现 | 未实现 | — | 需管理员定向/补偿任务和原任务关联 |

### 4.9 ES

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-ES-001 索引构建 | SPEC-SEARCH-01；D02 §4.3、8.3；D04 §4；D05 ADR-01/03 | 待实现 | 未实现 | — | 已有设计 es-mapping.json；运行代码尚无全文索引客户端与同步任务 |
| FR-ES-002 关键检索字段 | SPEC-SEARCH-01；D02 §4.3、8.3；D04 §4；D05 ADR-01/03 | 待实现 | 未实现 | — | 需落实设计映射中的检索字段、分类来源和版本 |
| FR-ES-003 搜索排序 | SPEC-SEARCH-01；D02 §4.3、8.3；D04 §4；D05 ADR-01/03 | 待实现 | 未实现 | — | 需 BM25 策略、字段权重和固定查询集调参记录 |
| FR-ES-004 数据一致性 | SPEC-SEARCH-01；D02 §4.3、8.3；D04 §4；D05 ADR-01/03 | 待实现 | 未实现 | — | 需索引待重建状态、可靠任务、重试和数据库重建索引 |

### 4.10 REC

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-REC-001 推荐候选集 | SPEC-STAT-01；D02 §8.3–8.4；SRS §4.10 | 待实现 | 后续 P1 | — | 需候选检索及过滤策略 |
| FR-REC-002 排除当前论文 | SPEC-STAT-01；D02 §8.3–8.4；SRS §4.10 | 待实现 | 后续 P1 | — | 需排除当前规范论文 |
| FR-REC-003 去重 | SPEC-STAT-01；D02 §8.3–8.4；SRS §4.10 | 待实现 | 后续 P1 | — | 需按规范 ID/DOI 去重 |
| FR-REC-004 推荐数量 | SPEC-STAT-01；D02 §8.3–8.4；SRS §4.10 | 待实现 | 后续 P1 | — | 需默认 8、最多 20 和候选不足处理 |
| FR-REC-005 可解释性 | SPEC-STAT-01；D02 §8.3–8.4；SRS §4.10 | 待实现 | 后续 P1 | — | 需基于真实字段的推荐理由 |
| FR-REC-006 降级策略 | SPEC-STAT-01；D02 §8.3–8.4；SRS §4.10 | 待实现 | 后续 P1 | — | 需无标签/无摘要等降级策略 |

### 4.11 STAT

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-STAT-001 平台概览 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | C03、C06、C08 | 部分实现 | T18 S01 | 已有类型总数、引用覆盖、开放及未知计数；缺完整来源作者/学者/载体口径 |
| FR-STAT-002 时间统计 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | C03、C06、C08 | 部分实现 | T04 S01 | 已有业务年度分布；缺未结束年度截至时间和采集不完整标识 |
| FR-STAT-003 机构统计与分类排名 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | C03、C06、C08 | 部分实现 | T18 | 已有历史成果机构去重和并列排名；缺排名下钻及完整界面专项验收 |
| FR-STAT-004 学科统计 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | C03、C06、C08 | 部分实现 | T18 | 已有领域去重及未分类；缺分类体系/版本和来源主题展示 |
| FR-STAT-005 科研人员统计 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | 待实现 | 未实现 | — | 当前按 scholar 筛选来源贡献；需按有效确认关系计算公开个人统计 |
| FR-STAT-006 领域热点分析 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | 待实现 | 未实现 | — | 需时间桶关键词频次、有效分母、覆盖率和趋势 |
| FR-STAT-007 专家合作网络 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | C03、C06、C08 | 部分实现 | T17 S01 | 已有 BFS 路径、共著边权和证据；缺完整网络交互图 |
| FR-STAT-008 本人管理统计 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | C03、C06、C08 | 部分实现 | T27 S02 | 已有本人申请和成果列表；缺本人专用确认成果与申请状态统计 |
| FR-STAT-009 数据质量统计 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | 待实现 | 未实现 | — | 管理员总量统计已有；需质量完整率、疑似重复、未匹配和同步异常专项指标 |
| FR-STAT-010 统计更新 | SPEC-STAT-01；D02 §8.4；D04 §3–4 | C03、C06、C08 | 部分实现 | T07 | 现有按目录 revision 查询和缓存；缺统计任务、失败状态、修订失效与重试发布 |

### 4.12 ADMIN

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-ADMIN-001 Dashboard | SPEC-QUALITY-01；D02 §7；D03 §1；D04 §3 | C02、C04、C05、C08 | 部分实现 | T27 S02 | 已有用户/成果/申请/导入汇总；缺失败采集、机构和索引补采待办 |
| FR-ADMIN-002 机构管理 | SPEC-QUALITY-01；D02 §7；D03 §1；D04 §3 | C02、C04、C05、C08 | 部分实现 | — | 已有机构新增接口；缺编辑、禁用、别名维护和合并 |
| FR-ADMIN-003 审核中心 | SPEC-QUALITY-01；D02 §7；D03 §1；D04 §3 | C02、C04、C05、C08 | 部分实现 | S02 | 已有身份/门户/成果/撤销审核；缺机构、补录、纠错、索引补采审核 |
| FR-ADMIN-004 采集任务管理 | SPEC-QUALITY-01；D02 §7；D03 §1；D04 §3 | 待实现 | 未实现 | — | 现有仅 JSON 导入记录；需真实采集创建、启动、停止、重试和日志页 |
| FR-ADMIN-005 审计日志 | SPEC-QUALITY-01；D02 §7；D03 §1；D04 §3 | C02、C04、C05、C08 | 部分实现 | T12 T14 | 已有导入及认领状态审计；需机构/学者创建等管理动作审计及按对象/人/时间筛选分页 |

### 4.13 OUTCOME

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-OUTCOME-001 类型与有效记录 | SPEC-DATA-01/02、SPEC-QUALITY-01；D01 核心类图；D02 §1.1、4.1；D04 §1–3 | C04、C03、C08 | 部分实现 | T19 S01 | 已有四类型目录和样例；公共维护/有效性治理尚缺 |
| FR-OUTCOME-002 非论文录入与导入 | SPEC-DATA-01/02、SPEC-QUALITY-01；D01 核心类图；D02 §1.1、4.1；D04 §1–3 | C04、C03、C08 | 部分实现 | T05 T06 | 管理员结构化导入和模拟隔离已有；需科研人员非论文草稿及审核 |
| FR-OUTCOME-003 多类型检索与详情 | SPEC-DATA-01/02、SPEC-QUALITY-01；D01 核心类图；D02 §1.1、4.1；D04 §1–3 | C04、C03、C08 | 部分实现 | T03 S01 | 已有跨类型检索、详情和贡献角色；类型专属查询仍缺 |
| FR-OUTCOME-004 类型专属校验 | SPEC-DATA-01/02、SPEC-QUALITY-01；D01 核心类图；D02 §1.1、4.1；D04 §1–3 | C04、C03、C08 | 部分实现 | T04 T19 | 已校验贡献角色和专利授权依据；需按完整类型字段契约补齐约束 |
| FR-OUTCOME-005 元数据治理 | SPEC-DATA-01/02、SPEC-QUALITY-01；D01 核心类图；D02 §1.1、4.1；D04 §1–3 | 待实现 | 未实现 | — | 需修订、归并、类型领域维护、软删除及前后值审计 |
| FR-OUTCOME-006 治理后的传播 | SPEC-DATA-01/02、SPEC-QUALITY-01；D01 核心类图；D02 §1.1、4.1；D04 §1–3 | 待实现 | 未实现 | — | 需治理事件可靠登记、索引/统计更新及重复处理保护 |
| FR-OUTCOME-007 贡献角色与成果时间 | SPEC-DATA-01/02、SPEC-QUALITY-01；D01 核心类图；D02 §1.1、4.1；D04 §1–3 | C04、C03、C08 | 部分实现 | T04 T19 | 已保存角色、业务时间及年/月/日精度；需原始网页发布时刻、来源成果时刻等独立字段完整性 |
| FR-OUTCOME-008 来源完整性与展示样本校验 | SPEC-DATA-01/02、SPEC-QUALITY-01；D01 核心类图；D02 §1.1、4.1；D04 §1–3 | C04、C03、C08 | 部分实现 | T19 | 已有来源、标题和单位奖表达；缺完整样本/待补样本分级及分源完整率验收 |

### 4.14 SCHOLAR

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-SCHOLAR-001 人员查询 | SPEC-DATA-03、SPEC-SEARCH-01；D01 核心类图；D02 §1.1、5–6 | C03、C05、C08 | 部分实现 | S01 | 支持姓名/ID 查询和候选状态；缺机构、领域过滤和分页 |
| FR-SCHOLAR-002 人员与成果导航 | SPEC-DATA-03、SPEC-SEARCH-01；D01 核心类图；D02 §1.1、5–6 | C03、C05、C08 | 部分实现 | S01 | 学者到成果筛选已有；详情中的人员仍为文本，需有依据的反向点击导航 |

### 4.15 ACCESS

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-ACCESS-001 公开访问与任务恢复 P0 | SPEC-SEARCH-01；D02 §5–6；D03 §1–2 | C07、C08、C09 | 部分实现 | S01 S02 | 访客可访问公共页，失败保留条件；任务恢复尚缺完整条件/位置持久化及取消登录专项验证 |

### 4.16 FEEDBACK

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-FEEDBACK-001 公开数据反馈 P0 | SPEC-QUALITY-01；D02 §7；SRS FR-FEEDBACK-001 | 待实现 | 未实现 | — | 需公众反馈、处理状态、重复反馈及管理员受理流程 |

### 4.17 INNOV

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-INNOV-001 最短共著路径与证据 P0 创新 | SPEC-STAT-01；D02 §8.4；SRS FR-INNOV-001 | C06、C08 | 部分实现 | T17 S01 | BFS 按过滤范围返回路径与证据；六跳限制、等长路径和图上限需专项验收 |

### 4.18 TOOLS

| 需求编号及内容 | SPEC 与设计 | 当前实现入口 | 状态 | 已有测试 | 剩余工作或验收条件 |
| --- | --- | --- | --- | --- | --- |
| FR-TOOLS-001 收藏、专题库、私人笔记 | SPEC-TOOLS-01；SRS §4.16；SPEC §10 | 待实现 | 后续 P1 | — | 需收藏、专题库、笔记和对象级私有授权 |
| FR-TOOLS-002 引用及元数据导出 | SPEC-TOOLS-01；SRS §4.16；SPEC §10 | 待实现 | 后续 P1 | — | 需 CSV/BibTeX、范围一致性和来源/缺失标记 |
| FR-TOOLS-003 文献比较 | SPEC-TOOLS-01；SRS §4.16；SPEC §10 | 待实现 | 后续 P1 | — | 需 2–10 篇比较和缺失值表达 |
| FR-TOOLS-004 研究资源关联 | SPEC-TOOLS-01；SRS §4.16；SPEC §10 | 待实现 | 后续 P1 | — | 需有来源的代码/数据集资源及失效处理 |
| FR-TOOLS-005 引用方向与后续研究 | SPEC-TOOLS-01；SRS §4.16；SPEC §10 | 待实现 | 后续 P1 | — | 需区分参考/被引关系及来源边界 |
| FR-TOOLS-006 姓名别名和高级查询 | SPEC-TOOLS-01；SRS §4.16；SPEC §10 | 待实现 | 后续 P1 | — | 需已确认别名和高级 all/any 查询 |
| FR-TOOLS-007 检索保存与关注 | SPEC-TOOLS-01；SRS §4.16；SPEC §10 | 待实现 | 后续 P1 | — | 需私有保存查询/人物/领域及取消关注；自动通知属于 P2 |

## 5 三条关键用例和 SPEC 对应关系

| 用例或规范 | 设计对象及交互 | 当前实现 | 实现差异和验收入口 |
| --- | --- | --- | --- |
| AN-UC-01 / SPEC-INGEST-01 | D07；CrawlTask、SourceAdapter、IngestionService、原文、检查点、Worker | C04 的结构化批次导入，C10 来源与事务表 | 联网、分页、任务恢复与索引阶段待实现；AN-AT-01～06、AC-R16/23/26～28 |
| AN-UC-02 / SPEC-CLAIM-01 | D08；账号、门户、Claim、审核租约与授权 | C01、C02、C07；T08～T16、S02 | 外部核验、完整材料历史、机构及补录纠错申请待补；AN-AT-07～10/15 |
| AN-UC-03 / SPEC-SEARCH-01 | D09；SearchService、ExactIdStrategy/Bm25Strategy、ReleaseSnapshot | C03、C08；T02/03/07/20、S01 | 数据库包含检索、50 条上限、追加版本；全文索引、修订和过期机制待补；AN-AT-11～14 |
| SPEC-DATA-01 | D02 §1.1、8.2；类型值、日期精度和清洗 | C04.normalize；T04/19 | 来源解析、规则版本、隔离及人工抽样待补 |
| SPEC-DATA-02 | D02 §8.2；强键、候选、来源映射与归并 | C04.ingest；T05/06 | 弱匹配候选、治理归并、撤销归并与不可变修订待补 |
| SPEC-DATA-03 | D01 身份对象、D02 §1.1；人物/机构标识与历史关系 | C03、C04、C05；T03/09/15/17 | 同名分离已有；ORCID/ROR 核验、机构别名和人工候选处理待补 |
| SPEC-STAT-01 | D02 §8.4；统计、快照、共著图与 P1 推荐 | C03.stats、C06.path、C08；T17/18 | 确认关系统计、热点、统计任务、网络图和后续推荐待补 |
| SPEC-QUALITY-01 | D02 §7、D04 §3；修订、复核、字段锁定、审计 | C04.audit、C05.audit 与 C02 状态审计 | 治理工作流、质量分母、回退及恢复演练待补 |
| SPEC-TOOLS-01 | SRS §4.16、SPEC §10；私人资料对象 | 尚未实现 | 按后续 P1 保留，AC-U12 在启用时执行 |

## 6 分析验收场景追踪

原始场景见 [需求分析验收场景.csv](../前期成果/需求分析/docs/需求分析验收场景.csv)。

| 场景 | 对应 FR 与设计 | 当前实现和测试 | 完整场景状态及剩余条件 |
| --- | --- | --- | --- |
| AN-AT-01 | CRAWL-005/007；D07 | C04；T05 | 部分实现；批次重复与跨源 DOI 已覆盖，真实重复分页待补 |
| AN-AT-02 | CRAWL-005、SCHOLAR-001；D01/D02 | C04 来源键、C03 独立 ID | 部分实现；缺候选复核队列和无强键同名专项测试 |
| AN-AT-03 | OUTCOME-004/007/008；D02 §1.1 | C04；T04/19 | 部分实现；日期精度和单位奖已有，真实四类样本字段校验待补 |
| AN-AT-04 | SYNC-002/003、CRAWL-003/006；D07 | 待实现 | 未实现；需第二页失败、断点恢复、成功水位和重放验证 |
| AN-AT-05 | SYNC-004、CRAWL-008；D07 | 待实现 | 未实现；停止确认、旧执行器隔离和重试耗尽 |
| AN-AT-06 | ES-004、INDEXREQ-005；D05 ADR-03 | 待实现 | 未实现；入库保留、索引恢复和旧公开版本可用 |
| AN-AT-07 | PORTAL-012；D08 | C02；T10/11/12 | 部分实现；补充和重新验证已有，历次材料原文保存待补 |
| AN-AT-08 | PORTAL-008/013；D08 | 人工审核、本地结构检查 | 未实现外部调用路径；需超时转待核验/人工且不自动驳回的测试 |
| AN-AT-09 | PORTAL-013；D08 | C02；T14 | 部分覆盖；现有两请求批准/撤回竞争，需两审核员加申请人三方场景 |
| AN-AT-10 | PORTAL-007/008；D08 | C02/C10；T08/15 | 部分覆盖；门户竞争及私有隔离已有，需同账号第二门户组合用例 |
| AN-AT-11 | SEARCH-007/008；D09 | C03.filter；T03 | 已实现主要关系语义；最终环境回归 |
| AN-AT-12 | SEARCH-010、ACCESS-001；D09 | C03/C09/C13；T02/20、S01 | 部分实现；非法/空集已有，需注入实际超时并核对条件保留 |
| AN-AT-13 | SEARCH-005、ES-004；D09 | C03/C04；T07 | 部分实现；旧追加版本可读，尚无修订与版本到期回收 |
| AN-AT-14 | STAT-003/004；D02 §8.4 | C03.stats；T18 | 已实现主要去重和未知值口径；最终环境回归 |
| AN-AT-15 | PORTAL-011、TOOLS-001；D08 | C02.detail；T08/27 | 私有证明已覆盖；私人笔记随 P1 启用后另验 |

## 7 统计与成果管理用例追踪

| 用例 | FR 对应 | 代码和测试 | 剩余范围 |
| --- | --- | --- | --- |
| UC-ST-01 | STAT-001 | C03/C08；T18、S01 | 完整平台概览口径 |
| UC-ST-02 | STAT-002 | C03/C08；T04、S01 | 截至时间和未知/不完整年度区分 |
| UC-ST-03 | STAT-003 | C03/C08；T18 | 排名下钻与 UI 专项验收 |
| UC-ST-04 | STAT-004/006 | C03 仅领域计数 | 时间桶热点、覆盖率和趋势 |
| UC-ST-05 | STAT-007 | C06/C08；T17、S01 | 完整交互共著图 |
| UC-ST-06 | STAT-005、PORTAL-001 | C02.myOutcomes 提供本人列表 | 公开门户按有效确认关系聚合 |
| UC-ST-07 | STAT-008 | C02.page、myOutcomes；T27 | 本人专用统计 |
| UC-ST-08 | STAT-009 | 待实现 | 来源/字段质量分母与质量指标 |
| UC-ST-09 | STAT-010 | C03/C04 追加目录版本；T07 | 统计任务、失败重试和旧快照保留 |
| UC-AM-01 | PORTAL-001、OUTCOME-003 | C02.myOutcomes、C07；S02 | 类型/年份/关联状态完整过滤及分页 |
| UC-AM-02 | PORTAL-002/003 | C02/C07/C08；T16、S02 | 类型专属检索字段 |
| UC-AM-03 | PORTAL-006 | 待实现个人附加信息 | 标签、说明、排序及对象授权测试 |
| UC-AM-04 | PORTAL-005 | C02 REVOKE；T16 | 最终版本回归与统计更新 |
| UC-AM-05 | PORTAL-010、INDEXREQ-001、OUTCOME-002 | C04 仅管理员导入 | 用户补录/纠错及论文补采申请 |
| UC-AM-06 | PORTAL-011/012/013 | C02/C07；T10/11/12/27、S02 | 新增申请类型、材料历史和历史关联 |
| UC-AM-07 | PORTAL-004/005 | C02；T14/16、S02 | 最终环境回归 |
| UC-AM-08 | PORTAL-010、INDEXREQ-003、OUTCOME-005 | 待实现 | 补录/纠错审核与发布 |
| UC-AM-09 | OUTCOME-005 | 待实现 | 元数据修订、归并、软删除 |
| UC-AM-10 | ADMIN-005 | C05.audit、C02.detail | 审计完整性、过滤和分页 |
| UC-AM-11 | PORTAL-003 | C02.validateTarget；T09/15/16 | 新版本继续回归并补重复请求专项 |
| UC-AM-12 | INDEXREQ-002、OUTCOME-004 | C04 仅导入校验；T04/19 | 补录/纠错上下文预检查 |

## 8 SRS 验收场景追踪

FR 缩写在本节省略前缀 FR-。状态按该场景完整预期判定，测试编号指已有局部证据。

| 验收编号 | 验收内容 | FR 或规则对应 | 现状、证据和待完成验收 |
| --- | --- | --- | --- |
| AC-R01 | 真实／模拟数据采集、清洗、入库、检索、统计完整演示 | CRAWL、OUTCOME、SEARCH、STAT | 部分实现；已有模拟四类链路，真实采集和至少 10,000 条规模验收待执行 |
| AC-R02 | 注册用户认领既有候选门户，管理员核验 | PORTAL-007/008 | 已实现既有门户认领；T09/15、S02；最终版本需回归 |
| AC-R03 | 两位真实合著者分别认领同一论文，并重复提交一次 | PORTAL-003/004 | 部分覆盖；T16 覆盖两合著者与重复关联保护，需重复申请的独立 HTTP 场景 |
| AC-R04 | 修改个人说明，并尝试直接修改 DOI／他人说明 | PORTAL-006 | 未实现个人说明；需合法修改与 DOI/他人说明越权组合验收 |
| AC-R05 | 撤销一人的错误关联 | PORTAL-005、STAT-010 | 部分实现；T16 覆盖关系撤销和共享成果保留，需新快照个人统计验证 |
| AC-R06 | 非论文补录、驳回、重复处理与纠错 | OUTCOME-002/005、PORTAL-010 | 未实现科研人员补录与纠错闭环 |
| AC-R07 | 使用 P1/P2 构造样例查看排名、OA 和引用 | STAT-001/003/005 | 部分实现；T18 支撑去重和未知引用；公开确认统计及全部 OA 分母待核 |
| AC-R08 | 合作网络中加入共著和仅引用样例 | STAT-007 | 部分覆盖；T17 验证共著路径与证据，需只有引用关系的负例 |
| AC-R09 | 使用固定小样本查看关键词年度趋势 | STAT-006 | 未实现热点趋势与手算样本 |
| AC-R10 | 更新统计任务失败并重试 | STAT-010 | 未实现统计任务失败恢复；T07 仅支撑追加目录旧版本 |
| AC-R11 | 管理员与普通用户访问申请／质量／审计信息 | ADMIN-003/005、STAT-008/009 | 部分实现；T08/21/27 支撑权限；需补质量统计及新接口权限 |
| AC-R12 | 工程证据必交付；相关推荐在启用 P1 时验收 | SRS §8.8、REC | 部分准备；本地脚本及历史记录已有，GitHub 流水线/评审/AI 证据待形成；推荐随 P1 验收 |
| AC-R13 | 用标题、DOI、作者及类型专属标识检索并切换筛选、排序、分页 | SEARCH-001～010、SCHOLAR | 部分实现；T03/20、S01；缺类型专属字段、完整排序与 100 条分页 |
| AC-R14 | 查看论文详情、开放状态、引用及参考文献 | PAPER-001～006 | 部分实现；S01；需 DOI/OA 入口、参考文献和同步时间 |
| AC-R15 | 未认证用户所需机构不存在 | INST-002/003 | 未实现机构申请与审核衔接 |
| AC-R16 | 定时／手动增量执行、失败重试及索引恢复 | CRAWL、SYNC、ES-004 | 未实现联网增量及索引恢复；C04 仅提供幂等批次基础 |
| AC-R17 | 普通账号尝试调用管理员审核接口 | AUTH-003、ADMIN-003/005 | 已有拒绝越权用例 T21；需审核写接口和完整管理审计专项 |
| AC-R18 | 导入 Crossref 第二轮 10 条原始记录，学科字段全部缺失 | CRAWL-002、SRS §6.11 | 待接入真实 Crossref 固定原始样本，验证缺学科仍为未分类 |
| AC-R19 | 导入第一轮 4 条 Editorial Board 记录 | CRAWL-010 | 未实现体裁排除；需固定 Editorial Board 原文样本 |
| AC-R20 | 分别导入知识产权局 10 条与高校补充 10 条专利 | OUTCOME-007/008 | 部分数据结构；需两来源各 10 条真实样本及独立完整率报告 |
| AC-R21 | 导入 2019 项目、2023 奖项及其 2020／2024 发布日期 | OUTCOME-007、SRS §6.4/6.10 | 部分实现；T04 支撑日期精度；需项目/奖励年度与网页发布日期组合负例 |
| AC-R22 | 核对“科学部编号”、项目负责人、获奖提名者与专利权人 | OUTCOME-004/007 | 部分实现；T04/19；需科学部编号、权利人、提名者等完整样本断言 |
| AC-R23 | 输入 HTTP 412、HTTP 200 的 JavaScript 外壳、合法空数据三种响应 | CRAWL-009 | 未实现真实响应分类与固定响应夹具 |
| AC-R24 | 门户申请补充、撤回、驳回后再次申请 | PORTAL-012 | 部分实现；T10/11/12、S02；需历次材料原文及再申请历史关联 |
| AC-R25 | 两管理员审核同一版本，同时申请人撤回 | PORTAL-013 | 部分覆盖；T14 为两请求竞争；需两管理员和申请人三方竞争 |
| AC-R26 | 自动重试耗尽、管理员取消及运行中停止 | CRAWL-008、SYNC-004 | 未实现任务重试耗尽、取消和停止确认 |
| AC-R27 | 一窗口中前页已入库，后页解析失败，随后重跑 | CRAWL-003/006、SYNC-002/003 | 未实现页级提交及整窗水位 |
| AC-R28 | 数据入库成功但搜索索引更新失败 | ES-004、INDEXREQ-005 | 未实现入库与索引阶段分离及可靠重试 |
| AC-R29 | 同名无 ORCID、同域名不同机构、用户仅填写他人 ORCID | SCHOLAR、PORTAL-008、SRS §6.2/6.3 | 部分实现；独立人物 ID 和人工授权已有，需同域名机构及伪填 ORCID 专项 |
| AC-R30 | 固定检索／推荐样本，改变字段权重并模拟标签缺失 | ES-003、REC | 全文权重评估未实现；推荐缺失降级随 P1 验收 |
| AC-U01 | 同名 A01 / A02，选定 A01 后加主题和年份 | SEARCH-007 | 部分覆盖；T03 支撑人物 ID，需同名候选确认后添加主题/年份的完整 UI 场景 |
| AC-U02 | 同一作者机构条件与任一作者机构条件分别检索 | SEARCH-008 | 主要关系已实现；T03；补 API 与界面两语义结果集对照 |
| AC-U03 | 无 DOI 同名题名，另一组有不同合法 DOI | CRAWL-005、SPEC-DATA-02 | 部分实现来源独立保存；缺候选记录、不同合法 DOI 和冲突依据专项 |
| AC-U04 | 一个专利申请的申请公开和授权公告，两次跨源导入 | OUTCOME-004/007、SPEC-DATA-02 | 部分实现申请号强键；需申请公开/授权公告文献阶段和跨源完整验收 |
| AC-U05 | 同号码不同资助机构、科学部编号、计划结束年 | OUTCOME-004/007 | 部分实现资助机构加批准号和编号类型；缺完整项目字段及计划结束年负例 |
| AC-U06 | 单位奖和该单位任职学者 | OUTCOME-007/008 | 已有单位奖不造个人规则；T19；最终真实来源样本回归 |
| AC-U07 | 起止学者存在两条等长共著路径、引用边与过滤条件 | INNOV-001、STAT-007 | 部分实现；T17；补等长路径、引用负例、过滤和六跳限制专项 |
| AC-U08 | 重试耗尽及管理员后来放弃 | SYNC-004、CRAWL-008 | 未实现 FAILED 耗尽与人工 STOPPED 分离 |
| AC-U09 | 采集成功而公开版本构建失败 | ES-004、STAT-010 | 未实现公开版本构建失败和旧完整版本保留 |
| AC-U10 | 两账号同时认领、一个账号申请第二个门户 | PORTAL-007/008/013 | 部分覆盖；T15 测门户竞争；补同账号第二门户及审计原子性组合 |
| AC-U11 | 条件改变、取消登录、超时与空结果 | ACCESS-001、SEARCH-005/010 | 部分实现；S01/S02；补取消登录、超时和返回位置恢复组合 |
| AC-U12 | 同成果收藏合并、跨页导出、另一个用户访问笔记 | TOOLS-001/002 | 后续 P1；收藏归并、跨页导出和私人笔记权限待启用后验收 |
## 9 非功能与课程交付追踪

以下 NF、ENG 为本文定位编号，原始要求仍按 B01 §8、B02 §13、D01 §11 和 E03 页码追溯。

| 编号 | 基线目标 | 已有实现或证据 | 待完成内容与验收 |
| --- | --- | --- | --- |
| NF-01 | ≥10,000 条有效规范成果，真实/模拟分列 | Bootstrap 支持模拟初始化，C03 默认 real | 记录最终数据集计数、四类样例、来源及模拟比例 |
| NF-02 | 20 并发，预热后 300 秒；搜索 P95≤2 秒、详情≤1 秒、统计≤3 秒 | [服务器 k6 脚本](../scripts/performance/server-load.js)及[执行说明](../scripts/performance/README.md) | 在服务器执行，保存原始结果、错误率、冷热条件、硬件和版本 |
| NF-03 | 500 条分类型/来源抽样，清洗正确率≥99%，合法存在标识精确命中目标 100%，固定查询≥50 组 | T04/05/19 是局部合成样本测试 | 人工标注集、错误分类、分母及查询集结果 |
| NF-04 | 清洗去重消歧、检索排序、统计三个核心模块行覆盖率均≥80% | 已有 27 个集成/HTTP 用例，build.gradle 尚无覆盖率插件 | 接入覆盖率工具，明确模块纳入类，报告实际行覆盖率并补关键分支测试 |
| NF-05 | 对象权限、会话摘要、密码保护、私有材料隔离 | C01/C02/C09/C13；T08/21/22/23/26/27 | 新增接口继续验证权限、输入边界和私有数据；扫描结果纳入发布证据 |
| NF-06 | 服务可恢复、备份可用、部署可回滚 | [部署说明](../docs/deployment.md)、Compose/k3s 模板、readiness 和 Prometheus 配置 | 完成实际部署、故障恢复、回滚及独立数据库恢复演练 |
| NF-07 | 原生 Windows 客户端及可复现构建 | WPF、build/start/publish 脚本；E01 | 工具发现与版本固定、干净环境构建、最终自带运行时 EXE 验证 |
| NF-08 | SRS §8.2 的10万级扩展、成果类型可扩展及来源独立启停 | 四类成果已有；C03 深分页边界、C06 图边界已限制 | 10万级扩展独立测量，来源适配启停与容量预算验证 |
| NF-09 | SRS §8.5 的来源许可、用途限制、归因与私人资料保护 | 来源地址和模拟标记已有 | 真实来源接入登记、条款及许可记录、字段展示和访问边界检查 |
| NF-10 | SRS §8.6–8.7 的可观测性、一致性、可解释性与易用性 | readiness/Prometheus、审计、目录revision和错误提示已有 | 实际监控与告警、taskId/revision关联日志、故障注入和条件恢复验收 |
| ENG-01 | 设计与代码对应、模型随实现更新；E03 第13/58页 | D01～D09 与本表 | 根据后续功能修改模型，补实现提交及评审记录 |
| ENG-02 | 分支、PR、至少1人检视；E03 第47页 | 当前使用 GitHub 和 Group2 分支 | 真实 Issue、PR、检视意见及关闭记录；仓库规则配置与执行证据 |
| ENG-03 | 个人/集成/发布三层流水线；E03 第44/48页 | 本地脚本已有，当前本地无 .github/workflows | GitHub Actions 自动检查、测试、构建、部署；成功和门禁失败记录 |
| ENG-04 | 可追溯制品、成功部署、发布与回滚；E03 第34/44/50页 | JAR/EXE 打包及镜像模板已有 | Releases/GHCR、版本号与 SHA、部署运行链接和日志、实际回滚记录 |
| ENG-05 | 测试计划、用例、缺陷、回归、测试评估小结；E03 第26/28/30/49页 | E01/E02 历史验证，已有测试代码 | 当前版本分层报告、缺陷台账、遗留风险和发布结论 |
| ENG-06 | AI 日志、≥3 个人工修正案例、≥2项 Agentic Coding 实践；B01 §8.8/B02 §13 | E01 记载初始化、隐藏标签、草稿材料三项修复 | 核对对应提交和人工复核者，补提示词约束、前后差异、测试及演示记录 |
| ENG-07 | 现场运行演示、架构/流水线说明和答问；E03 第58页 | 已有桌面与设计材料 | 固定发布版本、演示数据、顺序脚本、操作人和备用恢复步骤；课件检查日期暂定12月30日 |

本表未将智能体产品的 RAG、模型服务、提示词发布和模型成本门禁加入运行系统范围。现有产品的 AI 使用要求落实在开发、复核和工程证据中；若产品后续接入模型能力，再补对应功能及评测需求。

## 10 设计与实现差异及后续工作

| 差异 | 目标设计 | 当前实现 | 关联项及下一步 |
| --- | --- | --- | --- |
| 代码职责划分 | D02 的 entry/application/domain/ports/infrastructure | 同一 Java 包中的 Controller/Service，JDBC SQL 主要在服务中 | AN-UC-01～03；新增能力逐步落实端口和领域约束，调整需更新设计 |
| 采集与处理 | SourceAdapter、独立 Worker、CrawlTask、租约、检查点 | ImportService 同步 JSON 批次事务 | CRAWL、SYNC、INDEXREQ；实现真实采集与恢复 |
| 清洗与来源 | 原始响应、解析规则、候选和质量状态 | 导入 DTO JSON、SHA 和来源观测 | CRAWL-004/005/007、OUTCOME-008；补原文保存、规则版本和质量分级 |
| 检索 | 精确标识策略、BM25、多字段过滤 | LIKE，year/citations/title，页大小≤50 | SEARCH-001～009、ES；补引擎、100条分页与查询评估 |
| 公开版本 | 不可变修订、索引/统计就绪后切换 | 追加目录 revision、关系库直接查询 | ES-004、OUTCOME-005/006、STAT-010；补修订、可靠发布和过期策略 |
| 材料历史 | 历次材料版本及原文可追溯 | evidence 覆写，material_version 递增，审计记状态 | PORTAL-012、AN-AT-07；增加不可变材料快照和再申请历史关联 |
| 审核租约 | 超时可释放，旧占用者失效 | TAKE 时惰性恢复，requireLease 拒绝过期终审 | PORTAL-013；明确实现选择并补超时/重领验收，按评审决定是否需主动调度 |
| 身份与机构 | 机构申请、核验和门户对象授权分层 | 身份/门户授权已分层，机构申请及外部核验待实现 | AUTH-004、INST、PORTAL-007/008；补申请及核验失败路径 |
| 图算法边界 | 指定版本的共著最少边路径及完整证据 | BFS 最多六跳，最多2000节点/10000边，每边证据最多20条 | INNOV-001、AC-U07；评审边界、补测试并同步设计与 UI |
| 工程平台 | 设计中 CodeArts、SWR、CCE | GitHub、本地脚本、Compose/k3s 模板 | ENG-02～04；按用户确认补 GitHub Actions、Releases/GHCR，部署拓扑随实际环境更新 |

后续任务顺序沿用本轮实施计划，实际指派后补负责人和 Issue/PR 链接。

| 后续任务 | 关联需求和差异 | 交付完成条件 | 依赖 |
| --- | --- | --- | --- |
| 任务二 构建复现 | NF-07 | 新检出环境构建测试通过，最终产物含版本/提交信息 | 工具版本核验 |
| 任务三 GitHub 协作与流水线 | ENG-02～04 | 分支、PR、评审、门禁与成功运行可追溯 | 任务二 |
| 任务四 真实采集与恢复 | CRAWL、SYNC、INDEXREQ | 至少一来源从采集到恢复入库，AN-AT-01～06相关用例通过 | 来源接入验证、数据迁移 |
| 任务五 数据治理与身份缺口 | INST、PORTAL、OUTCOME、FEEDBACK、ADMIN | 机构、补录、纠错、归并及材料历史闭环通过 | 需求字段与迁移设计 |
| 任务六 全文检索和发布 | SEARCH、PAPER、ES、STAT-010 | 精确/BM25、多字段、同版发布及故障恢复通过 | 采集数据与修订契约 |
| 任务七 统计与数据质量 | STAT、SCHOLAR、INNOV、NF-01/03 | 确认统计、热点、网络、数据集及人工抽样报告 | 四至六的稳定契约 |
| 任务八 测试和缺陷闭环 | NF-04/05、ENG-05 | 核心覆盖率、分层报告、关键用例和缺陷回归证据 | 随每项实现持续执行 |
| 任务九 部署与运维 | NF-06、ENG-04 | 服务器部署、回滚、备份恢复和故障处理记录 | 任务三及候选制品 |
| 任务十 性能与最终交付 | NF-01～03、ENG-05～07 | 服务器性能结果、测试评估、Release及现场演示材料 | 稳定候选版本及验收环境 |

## 11 更新记录和关闭条件

每次 PR 更新受影响 FR、设计位置、代码方法、测试及剩余条件。提交合并后记录提交号，执行验收后追加报告或工作流链接。调整需求或技术方案时保留原编号，并在 ADR 或需求变更记录中写明原因。

FR 关闭需要对应子要求实现、相关测试通过、设计同步及评审记录。AC/AN-AT 关闭需要按原场景完整执行并保存实际结果。NF/ENG 关闭需要实际数据集、覆盖率、服务器测量或平台记录。后续 P1 启用时独立纳入迭代。

| 日期 | 基线 | 更新内容 | 验证方式 |
| --- | --- | --- | --- |
| 2026-11-25 | Group2 / d083098 及本地后续设计材料 | 建立104条FR、42条AC、15条AN-AT、3条AN-UC、21条UC及工程目标追踪 | 源编号完整性、文件/测试定位及表格结构检查；执行结果沿用已注明日期的历史记录 |
