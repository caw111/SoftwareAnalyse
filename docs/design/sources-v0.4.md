# v0.4 固定公告来源接入

> 本文保留2026-11-17的接通设计与核验事实。自v0.5起LYNU已弃用，仅保留历史；当前可用范围与弃用行为见 [v0.5来源说明](sources-v0.5.md)。

版本：Group2 / v0.4。来源核验日期：2026-11-17。本文说明本轮注册范围、字段语义与恢复契约；构建、数据库回归、桌面及端到端采集的最终结果由 [v0.4 验证记录](../verification/sources-v0.4.md) 单列，本文不将页面可达核验写成全部验收通过。

需求依据：[SRS §4.7、FR-CRAWL-007/008、四类型语义](../../前期成果/需求调研和建模/docs/系统需求规格说明书_SRS.md)、[SPEC-INGEST-01 / SPEC-DATA-01/02](../../前期成果/需求调研和建模/docs/核心模块开发规范_SPEC.md)、[调研报告 §8.5](../../前期成果/需求调研和建模/docs/需求调研报告.md)。来源样本不能自动赋予人员账号、学者门户或成果认领权限。

## 1. 注册范围与实际入口

Crossref 继续承担论文 DOI/ISSN/关键词和索引日期窗口。四个非论文来源使用 REGISTERED_BATCH，管理员只能从注册目录选择公告批次；不接收抓取 URL，不搜索站点，不爬取历史栏目。Source ID、sourceName、类型、能力和批次由 GET /api/admin/crawl/sources 返回。

| sourceId / sourceName | batchId | 类型与原始内容 | 固定入口与本次行数 |
| --- | --- | --- | --- |
| lynu-patents / LYNU Patent Grants | lynu-grants-2025 | PATENT / HTML | [2025 年获得授权的专利清单](https://sites.lynu.edu.cn/kycx/info/1221/5141.htm)，28 行 |
| nsfc-projects / NSFC Life Sciences Projects | nsfc-life-key-2019 | PROJECT / HTML | [2019 年生命科学部重点项目资助清单](https://www.nsfc.gov.cn/p1/2853/3102/72645.html)，115 行 |
| most-awards / MOST National Natural Science Awards | most-natural-science-2023 | AWARD / HTML | [2023 年度国家自然科学奖目录](https://www.most.gov.cn/cxfw/kjjlcx/kjjl2023/202406/t20240624_191176.html)，49 行 |
| cnipa-patents / CNIPA Patent Gold Award List | cnipa-25-gold-2025 | PATENT / PDF | [第二十五届中国专利奖正式授奖公告](https://www.cnipa.gov.cn/art/2025/6/5/art_552_199973.html)的附件 1，专利金奖 30 行 |

CNIPA 只接入公告附件 1；外观设计金奖、银奖、优秀奖及组织奖不是本批次。原文链接为 [第二十五届中国专利金奖项目名单 PDF](https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=%E7%AC%AC%E4%BA%8C%E5%8D%81%E4%BA%94%E5%B1%8A%E4%B8%AD%E5%9B%BD%E4%B8%93%E5%88%A9%E9%87%91%E5%A5%96%E9%A1%B9%E7%9B%AE%E5%90%8D%E5%8D%95.pdf&filename=b712cad8dee344bc8322b4b45291fdf0.pdf)。入口公告用于说明来源，实际任务下载已注册的完整附件 URL。

表中数量是当日固定文件的原始记录数，后续来源可能修订；不表示自动入库数量、字段完整率或新增成果数。CNIPA 作为专利证据接入，而 MOST 提供独立 AWARD 成果；同一专利获得奖励不能因此重复算作两个专利实体。

## 2. 访问核验与约束

本次用本机 PowerShell 普通 HTTPS 请求逐一核验四个页面及一个 PDF：均 HTTP 200，三个表格页面声明 UTF-8，附件返回 application/pdf。CNIPA 附件 296,839 字节，SHA-256：

~~~text
465df4b59b7cd19a9938de94679dd0ef8364a67c650d470ee985d4ca7db3ff74
~~~

四个来源主机的根 /robots.txt 当次均返回 HTTP 404：[LYNU](https://sites.lynu.edu.cn/robots.txt)、[NSFC](https://www.nsfc.gov.cn/robots.txt)、[MOST](https://www.most.gov.cn/robots.txt)、[CNIPA](https://www.cnipa.gov.cn/robots.txt)。这是“未提供可用 robots 文件”的观察，不是站点许可或长期可用性证明。运行时继续检查；明确禁止、登录页、验证码/挑战页及 401/403 都作为访问失败，不能当作空结果，更不能绕过。

LYNU 页面注明版权归科研处，未见单独开放再发布许可。本项目保留必要来源事实与后台审计快照，展示来源链接；不据页面可访问推导任意全文再发布权。未来扩大来源、批次或用途时应重新核验条款、数据服务条件与访问额度。CNIPA 主检索系统、NSFC 通用项目检索门户与这里的公开公告不同，本轮未接通前两者，也不规避其访问控制。

请求只允许固定登记的 HTTPS 地址与对应根 robots 路径，不允许用户指定主机、端口、凭证、片段或任意重定向。新来源初始最小请求间隔 2,000 ms，来源租约及 next_request_at 跨 API 副本生效；不得用 HPA 增加来源并发。执行器环境变量与 Crossref 共用，详见 [部署配置](../deployment.md)。

### NSFC 的 Java TLS 信任配置

本机PowerShell可达不代表Java默认信任集合一致。测试JDK21缺少NSFC证书链使用的CFCA EV ROOT；当前适配器对已登记且主机精确为www.nsfc.gov.cn的批次/robots请求使用独立内存PKIX配置（默认信任锚加经核验的公有根）。其他来源保持默认客户端，不修改系统/JDK信任库，不关闭HTTPS主机名、证书路径、算法或有效期校验，不自动下载AIA证书。

根证书来自Windows LocalMachine\Root，按Mozilla官方CCADB记录核对DER SHA-256；公有证书、指纹、官方依据、2029年到期与维护规则见 [TLS材料说明](../../backend/src/main/resources/tls/README.md)。TLS_VALIDATION_FAILED保持可见失败且不可自动/手动重试；应复核信任配置后新建任务，不能通过关验证让任务成功。修正的本轮实测状态见 [验证记录](../verification/sources-v0.4.md)。

## 3. 类型映射与不能推断的字段

### 3.1 LYNU 授权专利

页面发表于 2026-06-10，清单覆盖 2025 年授权，表头为序号、申请号、专利类别、发明名称、申请日、授权公告日、发明人。申请号按字符串保留，申请日和授权公告日为 YYYYMMDD，解析为明确 DAY 精度；专利默认业务年度取授权公告日，不能取网页发布年。

例如首行申请号 CN202420753596.1：申请日 2024-04-12，授权公告日 2025-01-03。发明人按原表顺序拆分为 INVENTOR；页面没有给出每位发明人的机构，也没有专利权人字段，因此不因学校域名补造机构或权利人。该清单是高校发布的授权证据，不表示知识产权局主检索返回或当前法律状态已核验。

HTML 内容区域包含外围布局 table，适配器应按七列表头识别数据表；正文标题位于 pageTitle 元信息/正文，而不是依赖必有 title 标签。页面结构变化、关键列缺失或无有效数据表属于解析错误。登记HTML必须具有完整匹配表数（LYNU/NSFC各1表，MOST为2表），且每表至少一条非空数据行，不能忽略缺表后宣称成功。

### 3.2 NSFC 科研项目

六列表头为序号、科学部编号、项目名称、负责人、依托单位、直接费用（万元）。资助年度 2019 来自标题和固定批次；发布日期 2020-04-02 单独保存。只有年份时保持 YEAR 精度，不补 2019-01-01；来源没有提供项目起止日期、结题日期或状态。

科学部编号 3193000529 等保留原标签和字符串值，不能假称项目批准号，也不据此启用“资助机构 + 批准号”的强标识合并。负责人映射 PI，依托单位与负责人任职身份不混用；没有真实人物 ID 时只留来源姓名，不按姓名自动建门户。经费原值如 297 的单位是万元，不能当人民币元或整数项目数量；若展示换算必须明确原单位与换算规则。

### 3.3 MOST 国家自然科学奖

页面发布于 2024-06-24，业务奖励年度为 2023。共有两个表：一等奖 1 项、二等奖 48 项。表头为序号、编号、项目名称、主要完成人、提名者。等级标题在 HTML 中由多个 span 和空白分隔，应先提取文本再规范空白；每张表序号重新开始，来源稳定键必须使用项目编号，例如 Z-102-1-01，而不能只用序号。

主要完成人每人在独立段落，中文括号内是该成果对应的单位；姓名保留原值，如“方 忠”。贡献角色 AWARDEE，完成单位与提名者分别保存。提名者可以是机构或个人（例如第二表首项的提名者是个人），不能解析成完成人、获奖单位或人员当前任职。年度、奖项体系、级别和项目编号用于身份判断，不跨年度/等级自动合并。

### 3.4 CNIPA 专利金奖附件

PDF 有 4 页，页面约 841.9 × 595.3 pt，五列：序号、专利号、专利名称、专利权人、发明人。页 1 为第 1–7 项，页 2 为第 8–17 项，页 3 为第 18–28 项，页 4 为第 29–30 项；每页重复列头，多行题名、权利人和发明人可能上下错位，解析须保留页码和行定位，不能仅把 PDF 文本行当成一条记录。

专利号如 ZL202111257655.3 保留原值及标识类型，专利权人与发明人分开。附件没有申请日、授权公告日、当前权利状态或其核验日期。公告发表于 2025-06-05、成文日期 2025-05-28，只能作为来源/奖励证据；PATENT 的授权日期与年份保持未知，不能拿“第二十五届”或 2025 奖励年填充授权年度。记录应在详情中显示缺失，并从“日期完整样本”分母/分子口径中正确区分。

当前适配器仅接受注册的金奖标题与30项结构，并设8MiB输入、32页、单页4MiB解码流/100,000操作符/30,000字符的解析上限；不是通用任意PDF导入器。结构错误失败，个别坏行按明确原因隔离。多权利人保留在patentHoldersRaw，原专利号保留在patentNumberRaw，规范申请标识使用CN前缀；page/cells保存页码和列定位。

本机 Poppler 对该 PDF 的部分数字字体给出嵌入字体警告，文本映射仍可提取。解析器用文本位置/表格结构与固定样本校验，不以截图 OCR 或视觉猜测补标识。

## 4. 管理 API 与预算

~~~json
{
  "sourceId": "lynu-patents",
  "batchId": "lynu-grants-2025",
  "mode": "BOUNDED",
  "maxRecords": 10,
  "pageSize": 5,
  "maxPages": 2
}
~~~

POST /api/admin/crawl/tasks 只创建 PENDING；再按返回 id/version 显式 START。公告任务只能 BOUNDED，不能混入 DOI、ISSN、关键词、索引起止日期、出版年条件；来源/批次不匹配返回参数错误。pageSize、maxPages 为 1–100，maxRecords 为 1–10,000，默认预算为 pageSize × maxPages。

“每页”是数据库提交切片，不是源站分页。即使 maxRecords=1，服务仍需下载并解析整个固定 HTML/PDF；原始响应字节另有8MiB硬上限。文档总行数 recordCount、预算内处理数 received、新增 inserted、更新 updated、未变 unchanged、排除 excluded、冲突 conflicts 分别记录。限量达到预算可 SUCCESS / LIMIT_REACHED，处理完整份文件可以来源耗尽结束；两者都不建立 Crossref 日期水位。

公告重新采集按稳定来源键与原文/规范哈希幂等；非论文定时计划和 INCREMENTAL 均未开放。扩展到滚动公告栏目需要单独设计批次发现、发布时间排序和漏批恢复，不能沿用 Crossref 日期水位假装完成全站同步。

## 5. 冻结原文、分批发布与恢复

~~~mermaid
sequenceDiagram
    participant A as 管理员
    participant W as 任务执行器
    participant O as 已登记来源
    participant D as PostgreSQL
    A->>W: START(taskId, version)
    W->>D: 领取来源/任务租约，读取任务文档
    alt 尚无已提交文档
        W->>O: robots 核验后 GET 固定 HTML/PDF
        O-->>W: 正文、状态、HTTP 标头
        W->>W: 校验类型/结构，映射全部行，截取预算内首批
        W->>D: 同一事务：冻结文档 + 首批规范结果/倒排/断点
    else 已有任务文档
        D-->>W: 不可变正文、校验和、行数
        W->>W: 从该正文恢复下一切片
        W->>D: 同一事务：下一批规范结果/倒排/断点
    end
    W->>D: 记录终态/原因；公告不推进日期水位
~~~

Flyway V6 增加 crawl_task.batch_id 与 crawl_document。后者以 task_id 为 PK/FK，每任务最多一份正文：HTML 保存 UTF-8 等价文本，PDF 保存原始字节的 Base64，并记录类型、编码、字节哈希、正文哈希、HTTP 状态、ETag、Last-Modified、总行数、parser_version及抓取时刻。每个来源记录另保留行级原文、规范映射、解析/规则版本和行号/页码。正文是后台审计材料，原始页 API 仅 ADMIN 可见。

首批保存与规范发布在同一事务；失败则整批回滚，不推进断点。首批提交前崩溃可重新下载，因为尚未发布该任务正文；一旦提交，重试/恢复必须读已冻结正文，并核对登记URL、parser_version和总行数；发生变化明确拒绝，不能拼接更新后的文件或解析规则。后续来源变化须通过新任务保留新快照，不覆盖旧正文；一次公告缺席不意味着删除已有成果。

crawl_page.raw_json 对公告保存文档引用及 offset/count 等切片信息；GET 原始页接口为兼容保留 rawJson 名称，但此时解引用返回整份 HTML 或 Base64 PDF，另返 sliceMetadata、contentType、bodyEncoding、byteChecksum、recordCount、fetchedAt。JSON 字段名不意味着响应值一定是 JSON 文本。校验和口径见 [ER](database-er.md)：公告的crawl_page.response_checksum与crawl_document.response_checksum均对冻结正文文本计算，sliceMetadata.documentChecksum记录同值；byte_checksum对下载原始字节计算。切片定位字符串本身不冒充全文。

来源发布日期独立保留，但不等同于记录修订时间；本轮四个解析器的 sourceUpdatedAt 保持 null，不从固定批次发布日期推定更新先后。fetchedAt 是观察时间。网页内容变更却没有更晚可信源修订时间时保留原始证据并进入冲突复核；未来仅有明确可信源更新时间才可启用时序比较，不得仅因后抓到就覆盖主值。原文不变但规则升级改变规范结果时，沿用 source_processing 与 REPROCESS_REVIEW_REQUIRED 路径。

## 6. 本轮验证范围与后续工作

2026-11-17 已完成的来源核验限于四个固定页面、四个 robots 地址和一个附件；没有批量扫描或压力测试。开发审计产物存 artifacts/source-audit/2026-11-17/，包含等价 HTML、原始 PDF、SHA-256、样本结构与字段检查，产物不入 Git。最终80项H2测试、四源各两次顺序单条任务、桌面业务及原生窗口结果见 [验证记录](../verification/sources-v0.4.md)。本轮PostgreSQL/Docker因引擎不可用未验证；不沿用历史版本的成功结果。

应验证：正确识别四份文档；拒绝登录/挑战/网页壳；类型、表头、重复编号、日期、括号/换行异常；首批及后续批事务失败；重试不重新下载冻结正文；预算不被称为新增；再次采集幂等；非论文拒绝日期窗/定时；只读原始证据权限；来源时间未变的内容变化进入复核。

尚未覆盖：任意年度/批次、通用 CNIPA/NSFC 检索、法律状态动态核验、完整专利公开文献/申请/家族关系、弱身份消歧、人工冲突裁决、批量许可扩展、服务器 P95/HPA 验收。四个来源适配器不能替代这些能力。

