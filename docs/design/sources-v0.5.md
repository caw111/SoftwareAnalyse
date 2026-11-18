# v0.5 来源范围与弃用策略

版本：Group2 / v0.5，更新日期：2026-11-18。当前部署与回归见 [v0.5验证记录](../verification/server-v0.5.md)；首次固定批次接通、原文结构与字段映射保留在 [v0.4来源说明](sources-v0.4.md)。2026-11-17 的 HTTP/robots 核验是历史观察，本轮没有为更新文档重新采集源站。

## 当前可用来源

| 来源 | 类型/方式 | 允许范围 | 定时/完整水位 |
| --- | --- | --- | --- |
| crossref | PAPER / Crossref API | 单DOI；ISSN/关键词、最多31天索引窗口、可选出版年 | 支持；默认定时关闭，仅完整INCREMENTAL窗口推进水位 |
| cnipa-patents | PATENT / 固定PDF | `cnipa-25-gold-2025`：第二十五届专利金奖附件，原样本30项 | 不支持；只接受BOUNDED |
| nsfc-projects | PROJECT / 固定HTML | `nsfc-life-key-2019`：2019生命科学部重点项目，原样本115项 | 不支持；只接受BOUNDED |
| most-awards | AWARD / 固定HTML | `most-natural-science-2023`：2023国家自然科学奖，原样本49项 | 不支持；只接受BOUNDED |

固定公告不是全站搜索，也不承诺覆盖所有年度。管理员选择登记批次和原始记录预算，不输入抓取URL；预算包括重复、排除和冲突，不代表等量新增。小预算仍下载整份公告，HTTP大小另有硬上限；后续事务从任务冻结原文继续，不重取不同版本。字段与正文冻结契约沿用 [v0.4设计](sources-v0.4.md)。

专利金奖年份不替代授权日期，当前法律状态保持未知；项目“科学部编号”不冒充批准号；获奖完成人、提名者、完成单位分别保留。三个公告解析器不从抓取或页面发布时间推定可信修订时刻，`sourceUpdatedAt=null`；无可信更晚源时间的差异保留复核，不静默覆盖主值。NSFC限定主机PKIX配置与公有根维护要求见 [TLS说明](../../backend/src/main/resources/tls/README.md)。

## LYNU 弃用与历史保留

`lynu-patents` / `lynu-grants-2025` 自v0.5起不再接受联网采集。既有规范成果、来源记录、冻结HTML、任务页、状态日志及来源链接保留；弃用不删除历史成果，不重新解释已发布修订，也不撤销既有人工确认关系。

来源目录保留旧定义用于读取历史，返回 `available=false`、`deprecated=true` 和 `deprecationReason`。这与管理员可调整的 `enabled` 不同：数据库临时启用不能恢复已弃用适配器。新建任务、修改来源设置、START/RETRY均被后端拒绝；客户端从新建与设置列表移除LYNU，历史任务仍可查看并显示弃用提示。

[V7迁移](../../backend/src/main/resources/db/migration/V7__retire_lynu_source.sql) 在来源锁序下关闭来源与定时、递增配置版本、释放来源租约；将PENDING/RUNNING/RETRYING任务置STOPPED，记录SOURCE_DEPRECATED日志、原因和完成时间，并失效任务租约。SUCCESS/FAILED/STOPPED等既有终态不重写。运行时在领取、请求、提交和回调边界复核可用性，传输白名单也不再接受LYNU URL，防止旧执行尝试在弃用后继续发布。

V7没有新增表或字段，来源的弃用策略定义在应用目录，不伪装成新增数据库 `deprecated` 列。物理ER仍为32表、297字段、44外键，见 [数据库设计](database-er.md)。

## 生产初始策略与扩展

生产空库使用 `APP_DEMO=false`，仅创建管理员，无演示资料。Crossref、CNIPA、NSFC、MOST来源启用，LYNU停用，所有定时计划关闭；启用来源本身不会自动创建采集任务。新任务必须由管理员按范围/预算明确创建并启动。

扩展来源或批次前核实官方访问条件、robots、许可/展示范围、类型字段和资源上限。验证码、登录和访问拒绝保持可见失败，不绕过；429尊重退避。OpenAlex、DBLP、通用CNIPA/NSFC搜索、任意公告URL、法律状态动态查询和自动弱身份归并仍未接通。
