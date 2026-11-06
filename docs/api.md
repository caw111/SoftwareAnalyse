# API v0.1

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

条件包括 q（最多 120 字；按空格拆分 AND；字面包含匹配）、type、scholar、institution、field、from/to、sort=`year|citations|title`、page、size（1–50）、revision。跨维度 AND；指定 scholar 时 institution 必须属于同一个人的贡献记录。排序稳定，以成果 ID 打破并列，未知年份/引用置后。首版是数据库包含查询与精确标识文本定位，不声称已经实现 BM25 或中文全文相关度。

不传 revision 时读取当前公开版本，后续分页/详情/统计继续携带该版本。追加式目录和来源均按 revision 过滤；现阶段旧版本不回收，非法/未来版本返回 410。不会在旧版详情拼接后来导入的来源。后续修订/删除必须引入不可变成果修订和版本过期策略；当前不提供公共题录覆盖编辑。

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

每批在发布行锁下原子提交成果、贡献、来源原文/校验和、来源观测、任务、审计和发布版本；批次失败全部回滚，失败不产生 SUCCESS。新的来源内容保留新版本，已有规范字段不静默覆盖；冲突字段的专门复核队列尚未实现。失败批次目前通过 HTTP 错误告知，**不是**具备六状态、断点和重试的联网采集任务。导入记录中的 SUCCESS 仅表示该结构化批次原子发布成功。

来源 URL 仅保留和显示，API 不抓取用户输入 URL。人物/机构 ID 必须事先显式登记；缺少人物证据可只留贡献姓名，不按姓名创建或合并学者。时间保留实际精度，缺失为 null；单位奖可没有个人贡献者。

## 错误与容量

统一 `{code,message}`：400 非法输入，401 未登录/过期，403 越权，404 不存在，409 版本/唯一关系冲突，410 无此版本，413 超大批次，422 图计算范围超限，429 有界并发超限，503 查询/锁等待超时，500 其他服务错误。正常空集合为 200 + total=0。写请求超时可能已经提交，客户端提示先刷新，禁止盲目重复写入。

默认 Hikari 8 连接、查询超时 4 秒、连接等待 2 秒、入口并发上限 96；搜索缓存 256 个键、统计 64 个键、图 16 个键，均有过期。缓存只存公开数据且含版本键。共著计算仅论文来源关系，最多 2,000 节点 / 10,000 边 / 6 跳，每边展示 20 篇证据并标注截断；超限提示缩小范围，不假装返回完整网络。

管理端口：`8081/actuator/health/liveness`、`/readiness`、`/prometheus`。默认绑定回环；容器内开放但不通过 Ingress 发布。
