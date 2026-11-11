# API v0.3

返回 UTF-8 JSON。公开目录匿名可读；私有操作用 `Authorization: Bearer <token>`。随机会话令牌有效 8 小时，数据库只存 SHA-256 摘要，登出即失效；密码用 PBKDF2。服务端每次核对最新角色和对象授权，客户端显示不是权限依据。远程应使用 TLS。

## 接口

| 方法与路径 | 授权 | 说明 |
| --- | --- | --- |
| POST `/api/auth/register` | 公开 | username、password、displayName；只能注册 USER |
| POST `/api/auth/login` | 公开 | 返回 token、expiresAt、user；密码运算并发上限 2 |
| GET `/api/auth/me` | 本人 | 最新角色、当前 scholarId |
| POST `/api/auth/logout` | 本人 | 撤销当前会话 |
| GET `/api/reference` | 公开 | 机构、已收录领域和最新 revision |
| GET `/api/works` | 公开 | 同版筛选、分页、总数、类型分面 |
| GET `/api/works/{id}` | 公开 | 题录、日期语义、贡献者、单位、领域、类型字段、来源摘要 |
| GET `/api/scholars` | 公开 | q、dataset；姓名不合并，返回独立 ID；最多 100 条 |
| GET `/api/statistics` | 公开 | 与检索相同筛选/版本，按规范成果去重 |
| GET `/api/graph/path` | 公开 | start、end、dataset、revision、from/to、field、institution |
| GET/POST `/api/claims` | 本人 | 查询本人申请 / 新建草稿 |
| GET `/api/claims?review=true` | ADMIN | 最近 200 条审核记录 |
| GET `/api/claims/{id}` | 本人或 ADMIN | 私有证据及有序状态历史 |
| POST `/api/claims/{id}/actions` | 按动作 | 带 version 的状态迁移 |
| GET `/api/me/outcomes` | RESEARCHER | 本人已确认成果，最多 500 项 |
| GET/POST `/api/admin/imports` | ADMIN | 最近 100 批 / 受控结构化导入 |
| GET `/api/admin/audit` | ADMIN | 最近 200 条操作记录 |
| POST `/api/admin/institutions` | ADMIN | 显式登记独立机构 id、name |
| POST `/api/admin/scholars` | ADMIN | 显式登记 id、name、institutionId、bio、simulated |

公共 reference 是词表，不代表每个数据集都存在对应成果；目录与统计明确用 `dataset=real|demo` 分开，默认 real。当前每个机构/学者列表有数量上限，完整后台分页管理后续实现。

## 检索与版本

```text
GET /api/works?dataset=demo&type=PAPER&q=并发&from=2020&to=2026&scholar=S1&institution=I1&page=0&size=20&sort=year
GET /api/works/{id}?revision=1
```

条件包括 q（最多 120 字）、type、scholar、institution、field、from/to、sort=`relevance|year|citations|title`、page、size（1–50）、revision。默认 relevance：精确规范标识命中优先，其后按加权 TF 的 BM25 变体排序；拉丁词、中文二元组与独立单字按 AND 求交。空查询按最近内容版本排序。跨维度 AND；指定 scholar 时 institution 必须属于同一个人的贡献记录。排序最终以成果 ID 打破并列，未知年份/引用置后。排序公式、词规则、权重和局限见 [构件设计](design/component-design.md)。

不传 revision 时读取当前公开版本，后续分页/详情/统计继续携带该版本。成果、贡献、机构、领域和检索倒排按不可变内容修订及 `[revision, valid_to)` 有效区间查询；来源证据同时按接受状态与发布版本过滤。现阶段旧版本不回收，非法/未来版本返回 410。增量更新同一成果不会改变旧版详情、旧版排序和统计。

## 审核

新建：`{kind,targetId,evidence,contributionRole}`，kind 为 IDENTITY / PORTAL / OUTCOME / REVOKE；贡献角色分别为 AUTHOR / INVENTOR / PI / AWARDEE。身份证明/门户申请的 contributionRole 为空字符串。IDENTITY 的 targetId 必须是本人账号 ID。其他申请要求已认证 RESEARCHER，成果申请还需已绑定门户。

动作：`{version,action,reason,evidence}`；version 是上次读取的整数版本，reason 必须存在（提交/撤回可以为空，终审必须非空）。

- 本人 SUBMIT：DRAFT → PENDING_REVIEW。门户保留 PENDING_VERIFICATION → VERIFYING → PENDING_REVIEW 的每一步审计；本地结构检查在同一事务完成，外部身份证明仍须人工核验。
- 本人补充 SUBMIT：NEED_MORE_INFO 提供非空 evidence；材料版本递增，门户重新经过验证状态。
- ADMIN TAKE：PENDING_REVIEW → UNDER_REVIEW，领取 10 分钟审核占用。
- 占用者 APPROVE / REJECT / NEED_MORE_INFO：必须有当前版本、有效占用和理由。
- 占用者 RELEASE：主动释放；超时后其他审核员可 TAKE，原占用者不能终审。**首版超时释放采用重新领取时惰性恢复，不是定时自动迁移。**
- 本人 WITHDRAW：任一非终态撤回。终态不可覆盖，再申请创建新 ID；同类在审申请返回本人原记录。

申请行锁 + version 条件更新防止过期写入；审批时再次锁定申请人账号并核对绑定，数据库约束保证门户两端唯一、每人每成果唯一。批准授权、状态、审计同事务；门户授权不改变 RESEARCHER 角色，也不确认任何源贡献。管理材料仅本人和管理员可见，未引入私人笔记权限。

## 导入

使用 [四类型 JSON 样例](../scripts/samples/import-demo.json)。每批 ≤200 条、HTTP body ≤2 MiB，requestKey 为幂等键。同一 requestKey+相同内容返回原任务，不同内容返回 409。出版 DOI 去前缀并规范小写；授权专利按司法辖区+申请号，项目仅有可信批准号时按资助机构+批准号，获奖按体系+年度+项目编号归并；其他记录按来源稳定键保存，不按同名/近似题名自动合并。真实与模拟具有不同规范键。

每批在发布行锁下原子提交成果、贡献、来源原文/校验和、来源观测、内容修订、倒排、任务、审计和发布版本；批次失败全部回滚。相同来源键和原文/规范哈希只记录观测；同主来源的较新元数据更新稳定成果 ID。跨源差异、过期数据、人工锁定及相同原文的规则重处理进入质量冲突记录，保留原文，禁止静默覆盖。JSON 导入是高级兼容入口；主要数据入口为下述服务器采集任务。导入记录 SUCCESS 仅表示一批结构化数据原子发布成功，不等于整个采集窗口完成。

来源 URL 仅保留和显示，API 不抓取用户输入 URL。人物/机构 ID 必须事先显式登记；缺少人物证据可只留贡献姓名，不按姓名创建或合并学者。时间保留实际精度，缺失为 null；单位奖可没有个人贡献者。

## 错误与容量

统一 `{code,message}`：400 非法输入，401 未登录/过期，403 越权，404 不存在，409 版本/唯一关系冲突，410 无此版本，413 超大批次，422 图计算范围超限，429 有界并发超限，503 查询/锁等待超时，500 其他服务错误。正常空集合为 200 + total=0。写请求超时可能已经提交，客户端提示先刷新，禁止盲目重复写入。

默认 Hikari 8 连接、查询超时 4 秒、连接等待 2 秒、入口并发上限 96；搜索缓存 256 个键、统计 64 个键、图 16 个键，均有过期。缓存只存公开数据且含版本键。共著计算仅论文来源关系，最多 2,000 节点 / 10,000 边 / 6 跳，每边展示 20 篇证据并标注截断；超限提示缩小范围，不假装返回完整网络。

管理端口：`8081/actuator/health/liveness`、`/readiness`、`/prometheus`。默认绑定回环；容器内开放但不通过 Ingress 发布。


## 服务器采集任务与质量查看（v0.3）

以下接口全部要求 ADMIN；列表和详情返回的数据库字段以 camelCase 命名。真实接通的来源为 `crossref`，地址固定为 `https://api.crossref.org`；管理员输入范围，不输入任意抓取 URL。

| 方法与路径 | 说明 |
| --- | --- |
| GET `/api/admin/crawl/sources` | 来源状态、配置版本、定时间隔、联系邮箱是否已配置 |
| POST `/api/admin/crawl/sources/{id}/settings` | 带配置 version 的更新；停用来源请求其活动任务停止 |
| GET `/api/admin/crawl/checkpoints` | 各来源/范围最近完整扫描的截止日 |
| GET `/api/admin/crawl/tasks?page=0&size=20` | 分页任务 `{items,total,page,size}`，size 1–100 |
| POST `/api/admin/crawl/tasks` | 创建 PENDING、不立即执行的任务 |
| GET `/api/admin/crawl/tasks/{id}` | 任务字段、状态日志 logs、已提交页面 pages |
| GET `/api/admin/crawl/tasks/{id}/pages/{page}` | 指定页原始响应、校验和、排除原因、发布版本 |
| POST `/api/admin/crawl/tasks/{id}/actions` | `{version,action:"START|STOP|RETRY"}` |
| GET `/api/admin/quality?page=0&size=20` | 只读质量队列、未分类/未匹配机构/失败采集等计数 |

示例仅创建一条 DOI 任务；再以返回的 id、version 调用 START 才会联网：

```json
{"sourceId":"crossref","doi":"10.1038/nphys1170","mode":"BOUNDED","maxRecords":1,"pageSize":1,"maxPages":1}
```

范围任务示例：

```json
{"sourceId":"crossref","issn":"1476-4687","query":"quantum","fromDate":"2026-11-01","untilDate":"2026-11-02","fromPublicationYear":2020,"toPublicationYear":2026,"mode":"BOUNDED","maxRecords":40,"pageSize":20,"maxPages":2}
```

- DOI 与 ISSN/关键词互斥。非 DOI 请求须至少给出 ISSN 或关键词，固定索引时间窗口为 1–31 天，不能晚于当前 UTC 日期。出版年可选，索引日期与出版日期含义不同。
- pageSize、maxPages 均 1–100；maxRecords 为来源返回的原始记录总预算（1–10,000），包含重复、更新和排除记录，**不承诺等量新增**。返回分别统计 received、inserted、updated、unchanged、excluded、conflicts。
- BOUNDED 达预算可以 SUCCESS/LIMIT_REACHED，但从不推进完整同步水位。INCREMENTAL 仅在窗口扫尽时 SUCCESS 并推进水位；预算先耗尽则 FAILED/LIMIT_REACHED，已提交页仍可查，可创建 parentTaskId 关联的新任务扩大预算。DOI 定向任务不推进水位。
- 单页原始响应、增量入库、公开版本、已提交游标在同一事务提交。游标过期允许从窗口起点重扫并依赖幂等去重；预算不会重置。失败不跳过未扫描页。
- 六状态为 PENDING/RUNNING/SUCCESS/FAILED/RETRYING/STOPPED。STOP 在运行中先置 stopRequested，在提交边界确认，终态不可重新 START；重试受次数限制，终态重跑创建关联新任务。
- 所有变更使用 version；过期提交返回 409。多实例通过来源数据库租约、任务 attempt/token 和源级 nextRequestAt 协调；网络等待不持有数据库事务。
- 定时设置字段：version、enabled、minIntervalMs（1,000–60,000）、scheduleEnabled、scheduleEveryMinutes（60–10,080）、scheduleIssn、schedulePageSize、scheduleMaxPages、scheduleLookbackDays（1–31）。启用定时需要有效 ISSN。默认关闭；启用后自动创建 INCREMENTAL 窗口至 UTC 昨日，按已完成水位滚动并保留重叠。配置参考部署说明。
- 尊重 robots、Retry-After、HTTP 缓存约束、来源速率/并发头。401/403、挑战页和非法响应可见失败；访问拒绝、robots 拒绝或验证挑战会在有效租约且配置版本仍匹配时暂停定时计划、递增配置版本，等待人工复核。429 只退避；不自动绕过认证或验证码。
- 质量队列当前只读，不能在此界面批准冲突、合并学者或机构。Crossref ORCID 仅作为学术人物标识，不赋予用户身份或门户权限。

统计 `/api/statistics` 在原类型/年份/机构计数外增加热点 `hotspots`、分母 `hotspotDenominator`、逐年 `hotspotTrend`/`hotspotBuckets`、规则 `hotspotRule` 和覆盖率 `coverage`。热点频次按每篇成果去重，只使用题名/摘要；未知年份单独成桶，不推测未来趋势。完整算法和 ER 见 [构件设计](design/component-design.md)、[数据库设计](design/database-er.md)。
