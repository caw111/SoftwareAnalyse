from pathlib import Path
import json

OUT = Path(__file__).resolve().parent.parent
VERSION='v1.0'
DATE='2026-10-23'
META='第9组 1011101011 / A组 / A2 / 责任人 赵琦 / AI辅助编制 / v1.0 / 2026-10-23 / 待赵琦及另一成员复审'
C=[]
def cls(name,cn,group,attrs,ops,desc,rule,source,level='核心',nature='基线对象'):
    C.append(dict(id=f'C{len(C)+1:02}',name=name,cn=cn,group=group,attrs=attrs,ops=ops,desc=desc,rule=rule,source=source,level=level,nature=nature))

cls('Account','平台账号','A',
 ['accountId: ID','accountStatus: AccountStatus','researcherVerified: Boolean','roleGrants: RoleGrant[0..*]','version: Integer'],
 ['canApplyForPortal(): Boolean','checkObjectPermission(target): Boolean'],
 "平台账号表示系统的登录主体，并保存账号状态、科研人员身份审核结果和角色授权范围。科研人员身份审核通过后，账号才具备申请本人门户的资格。管理员使用具有相应审核权限的平台账号。",
 "账号标识应当保持稳定。系统应当结合角色权限和对象授权判断访问权限。researcherVerified由UC1.3的审核结果生成，用户只提交申请材料。科研人员身份申请与门户认领申请分别维护各自的业务记录。账号停用后，系统继续保留历史申请、授权和审计记录。",
 'SRS §1.1、§2、UC1.1～1.3、DR-01、BR-01；SPEC §7.1～7.3')
cls('Scholar','来源学者','A',
 ['scholarId: ID','displayName: String','aliases: Alias[0..*]','externalIds: ExternalIdentity[0..*]','identityEvidence: EvidenceRef[0..*]'],
 ['addEvidence(evidence)','proposeIdentityMatch(candidate)'],
 "来源学者表示来源资料中具有独立身份的人物。平台允许仅具有来源身份的学者记录存在，账号注册和门户认领分别按照对应流程处理。平台应当分别保存同名人物的身份资料。",
 "系统使用scholarId标识学者。系统应当分别记录ORCID格式校验结果、可信来源断言和账号控制证明。已经确认的ORCID发生冲突时，系统应当阻止自动合并并提交人工复核。候选匹配用于提供身份判断依据，人物合并和门户授权分别通过对应的审核流程生效。",
 'SRS DR-01、DR-03、UC2.2、DC-01；SPEC §5.1～5.2')
cls('ScholarPortal','学者门户','A',
 ['portalId: ID','publicBio: String[0..1]','personalAnnotations: Annotation[0..*]','visibility: Visibility','version: Integer'],
 ['updatePersonalInfo(patch, expectedVersion)','listPublicWorks(releaseId)'],
 "学者门户组织某一学者的公开资料及各类学术成果。门户从学者、贡献关系和成果对象中读取来源事实，并单独保存个人简介、补充说明、标签和展示顺序。",
 "每个门户对应一个学者。本模型规定，每个学者至多具有一个当前有效的规范门户；人物合并后，系统保留旧入口并设置重定向。个人资料更新应当实时校验有效的管理授权。个人更新的范围限定为简介、说明、标签和展示顺序，公共题录、贡献顺序和机构事实通过数据治理流程更新。",
 'SRS UC2.2、UC3.4、BR-02、BR-04；SPEC §7.3',nature='基线对象；每个学者至多具有一个规范门户属于A2设计约定')
cls('PortalAuthorization','门户管理授权','A',
 ['authorizationId: ID','validFrom: Instant','validTo: Instant[0..1]','revocationReason: String[0..1]','version: Integer'],
 ['isEffective(at): Boolean','revoke(reason, expectedVersion)'],
 "门户管理授权记录一个账号对一个门户获得的管理权限及其有效时间区间。该对象同时支持当前权限判断和历史授权追溯。",
 "账号和门户均可关联多条历史授权。任一时刻，每个账号至多具有一条有效的本人门户授权，每个门户至多具有一条有效的管理授权。审核通过时，系统按照原子提交要求生成授权。后续授权撤销通过治理流程处理，原申请继续保留APPROVED终态。",
 'SRS BR-01、BR-03、UC3.1；SPEC §7.2～7.3')
cls('ClaimApplication','门户认领申请','A',
 ['claimId: ID','state: ClaimState','materialVersion: Integer','evidence: PrivateEvidence[0..*]','version: Integer','reviewLease: ReviewLease[0..1]'],
 ['submit(expectedVersion)','requestMore(reason, expectedVersion)','approve(expectedVersion)','reject(reason, expectedVersion)','withdraw(expectedVersion)'],
 "门户认领申请记录指定账号申请指定门户管理权限的一次业务请求。申请应当保存材料版本、提交时间、处理时间和前次申请引用。私有证明材料由具有访问控制的值对象保存。",
 "申请状态限定为既有的六种状态。approve表示申请审核通过的领域操作，由审核协调对象在同一事务中提交申请状态、唯一绑定、管理授权和审计记录。申请人补充材料后，系统复用submit执行提交校验。已经进入终态的申请再次发起认领时，系统创建新的申请编号并关联历史申请。",
 'SRS UC3.1、UC3.5、BR-03、§4.1.2；SPEC §7.1～7.3')
cls('ReviewRecord',"门户审核记录",'A',
 ['reviewId: ID','action: ReviewAction','reason: String','materialVersion: Integer','objectVersion: Integer','reviewedAt: Instant'],
 ['appendDecision(action, reason)'],
 "门户审核记录保存管理员已经提交的补充材料要求、通过决定和驳回决定，并记录审核所依据的材料版本及对象版本。申请人和具有相应权限的审核人员按照访问规则查询这些记录。",
 "每条审核记录对应一份申请和一个审核账号。已经提交的记录采用追加方式保存，后续纠正通过新增记录表达。审核事务提交失败时，系统记录操作失败日志；审核事务提交成功时，系统生成对应的ReviewRecord。",
 'SRS UC5.2、BR-03；SPEC §7.1、§7.3',nature='基线审核历史的分析细化')

cls('Work','规范学术成果','B',
 ['workId: ID','title: FieldValue<String>','dataVersion: Integer','visibility: Visibility','mergedInto: WorkRef[0..1]','fieldEvidence: FieldEvidence[0..*]'],
 ['applyVerifiedUpdate(patch, expectedVersion)','markForReview(reason)','resolveCanonicalId(): ID'],
 "规范学术成果是抽象基类，统一保存稳定标识、公共题名、字段依据、数据版本和可见性。论文、专利申请、科研项目和学术获奖构成完整且互斥的具体类型集合。",
 "成果公开应当满足题名有效、来源明确和类型已确认的条件。摘要、DOI或年份缺失时，系统允许保存具有缺失标记的基础记录。成果合并后，系统应当保留旧标识、来源依据和历史记录。人工锁定的字段优先采用已经确认的主值，新来源中的冲突信息进入复核流程。",
 'SRS DR-01、DR-02、DR-06、BR-05；SPEC §3.2、§4.3、§9')
cls('Paper','论文','B',
 ['doi: ExternalIdentity[0..1]','venue: FieldValue<String>','publicationDates: BusinessDate[0..*]','oaStatus: FieldValue<OAStatus>','citations: CitationObservation[0..*]'],
 ['checkDoiIdentity(): IdentityResult','selectPublicationDate(): BusinessDate'],
 "论文保存专属的出版信息。系统分别保存纸质出版日期print、在线出版日期online和发布日期issued，并按照print、online、issued的优先顺序选择默认出版日期。引用量按照来源和观察时间分别记录。",
 "DOI缺失时，系统保留缺失状态。合法DOI相互冲突时，系统应当阻止模糊合并；相同DOI对应的字段发生冲突时，系统应当提交复核。引用量未知时，系统保存未知状态；引用量为零时，系统保存有效的零值观测。引用量统计采用明确的来源口径。预印本与正式出版版本通过版本关系分别保存。",
 'SRS DR-02、DR-04、UC2.3；SPEC §3.1、§4.1～4.2、§8.1')
cls('Patent','专利申请','B',
 ['jurisdiction: String','applicationNo: ExternalIdentity[0..1]','grantDate: BusinessDate[0..1]','grantEvidence: EvidenceRef[0..*]'],
 ['checkApplicationIdentity(): IdentityResult','hasGrantEvidence(): Boolean'],
 "专利申请作为Work的具体子类，以申请实体作为规范成果的身份单位。基础授权专利统计仅纳入具有可靠授权依据的申请。专利公开文献和专利家族分别通过独立的类进行表达。",
 "专利申请的精确身份由司法辖区和申请号共同确定。申请号缺失或可靠性待核实时，系统保留待核实记录。同一申请关联的多份文献及多个家族按照同一申请身份去重统计。授权日期采用授权证据中的业务日期，网页公告日期另行保存。",
 'SRS DR-02、BR-06；SPEC §4.1、§8.1')
cls('PatentDocument','专利公开文献','B',
 ['documentId: ID','authority: String','publicationNo: ExternalIdentity','kindCode: FieldValue<String>','publicationDate: BusinessDate','evidence: EvidenceRef[1..*]'],
 ['checkDocumentIdentity(): IdentityResult'],
 "专利公开文献表示一份申请公开文献或授权公告文献。该对象具有独立的文献身份。所属申请尚待解析时，平台先保存文献及其来源证据。",
 "authority、publicationNo和kindCode共同构成文献的精确标识。kindCode缺失时，文献进入候选匹配流程。申请公开文献与授权公告文献分别保存各自的身份和日期。文献参与授权申请统计的前提是所属申请关联已经确认，并且申请具有可靠的授权依据。",
 'SRS DR-02；SPEC §4.1',level='支撑',nature='专利分层身份的分析细化')
cls('PatentFamily','专利家族','B',
 ['familyId: ID','scheme: String','sourceFamilyKey: String','membershipEvidence: EvidenceRef[1..*]'],
 ['verifyMembership(patent, evidence)'],
 "专利家族表达来源定义的专利分组。scheme保存家族划分口径。申请按照各个来源的划分口径关联相应的家族。",
 "家族成员关系应当具有来源证据。本模型采用多对多关联保存各类家族口径，同一口径下的成员唯一性按照对应来源契约执行。系统分别使用家族标识、申请号和文献号标识相应层次的对象。",
 'SRS DR-02、BR-06；SPEC §4.1',level='支撑',nature='专利分层身份的分析细化')
cls('Project','科研项目','B',
 ['funder: InstitutionRef','approvalNo: ExternalIdentity[0..1]','programScope: String[0..1]','fundingYear: BusinessDate[0..1]','projectDates: BusinessDate[0..*]'],
 ['checkFundingIdentity(): IdentityResult'],
 "科研项目保存资助机构、批准编号及身份识别所需的计划范围。系统分别保存资助时间、批准立项时间、计划起止时间和实际结题时间。",
 "项目身份由资助机构和批准编号共同确定。批准编号相同而资助机构相异的项目分别保存。批准编号缺失的项目进入人工复核流程，科学部编号作为独立字段保存。机构身份尚待确认时，系统保存具有来源证据的机构记录，并保留其待确认状态。",
 'SRS DR-02、DR-04；SPEC §3.2、§4.1')
cls('Award','学术获奖','B',
 ['awardSystem: String','awardYear: BusinessDate','sourceProjectNo: String[0..1]','categoryAndGrade: FieldValue<String>','awardingBody: InstitutionRef'],
 ['checkAwardIdentity(): IdentityResult'],
 "学术获奖表示某一奖励体系在指定年度授予的获奖成果，并保存授奖机构、类别、等级和项目资料。获奖主体通过Contribution表达。",
 "奖励年度、奖励体系、授奖机构或等级发生明确冲突时，系统应当阻止自动合并。正式单位奖允许仅关联机构贡献主体。系统分别记录提名者和完成人的角色，并按照来源原义保存奖项等级。科研价值评价采用独立的评价规则。",
 'SRS DR-02；SPEC §3.2、§4.1～4.2')
cls('Contribution','成果贡献关系','B',
 ['contributionId: ID','roles: RoleAssignment[1..*]','confirmation: RelationStatus','evidence: EvidenceRef[1..*]','validPeriod: TimeInterval','personalNote: String[0..1]'],
 ['confirm(evidence, expectedVersion)','revokeRelation(reason, expectedVersion)'],
 "成果贡献关系连接一个规范成果和一个贡献主体。贡献主体在学者与机构之间选择其一。roles集合保存该主体在同一成果中的各项职责，RoleAssignment分别记录角色、顺序和证据。",
 "Scholar端与Institution端应当满足恰有一个有效主体的互斥约束。同一主体与同一规范成果至多具有一条有效贡献关系，各个角色保存在该关系的角色集合中。撤销操作结束目标关系的有效期，系统继续保留公共成果及其他贡献关系。公共角色和顺序的修改应当经过审核。",
 'SRS BR-01、BR-02、UC3.2～3.3；SPEC §3.2、§7.3')
cls('Institution','机构','B',
 ['institutionId: ID','name: String','ror: ExternalIdentity[0..1]','aliases: TimedAlias[0..*]','history: InstitutionHistory[0..*]'],
 ['proposeIdentityMatch(candidate)','recordHistory(change, evidence)'],
 "机构表示学校、院系、科研院所、企业、资助机构和授奖机构等具有独立身份的组织。已经核实且通过冲突校验的ROR用于精确关联，名称和域名用于生成身份匹配候选。",
 "同名或共享域名的机构应当结合来源证据进行身份复核。当前上下级关系通过自关联表达。更名、合并和拆分记录通过包含有效期及证据的历史值对象保存，历史成果继续引用成果发生时的机构关系。",
 'SRS DR-01、DR-03、DC-01；SPEC §5.3')
cls('Affiliation','学者任职关系','B',
 ['affiliationId: ID','roleTitle: String[0..1]','validPeriod: TimeInterval','evidence: EvidenceRef[1..*]','confirmation: RelationStatus'],
 ['confirmPeriod(evidence)','closePeriod(endDate, reason)'],
 "学者任职关系表示一个学者与某一机构之间的任职或隶属关系，并保存对应的时间范围和来源依据。一个学者可以同时具有多段任职，也可以先后具有多段任职。",
 "任职起止时间缺失时，系统应当保留缺失状态。当前任职由有效期查询确定，历史成果署名按照成果发生时的来源证据保存。人物身份判断应当结合身份标识和来源资料进行，任职变化作为其中的一项证据。",
 'SRS DR-04、DC-01；SPEC §5.1、§5.3',level='支撑',nature='时间化关联对象')
cls('ContributionAffiliation',"成果发生时的机构关系",'B',
 ['relationId: ID','validPeriod: TimeInterval','basis: String','evidence: EvidenceRef[1..*]','confirmation: RelationStatus'],
 ['confirmEvidence(evidence)','revoke(reason)'],
 "成果发生时的机构关系将某一贡献关联到成果署名或承担任务时的机构。一个学者在同一成果中可以具有多个署名机构。人物条件和机构条件通过同一Contribution进行关联查询。",
 "该关系应当依据成果发生时的来源证据建立。机构直接作为贡献主体时，该主体已经构成成果与机构之间的有效关系。本类主要保存个人贡献对应的署名机构或承担机构。统计时，系统合并这些有效机构关系，并按照机构标识与规范成果标识去重。",
 'SRS BR-07、DC-01；SPEC §5.3、§6.1、§8.1',level='支撑',nature='带证据的关联对象')
cls('ResearchField','学术领域','B',
 ['fieldId: ID','label: String','taxonomyVersion: String'],
 ['descendants(): FieldSet'],
 "学术领域表示平台学科目录某一版本中的领域节点。目录采用支持多个根节点的树形结构。来源中的主题文字保存在对应的来源记录中。",
 "同一目录版本中的每个节点至多具有一个父节点，并满足无环约束。跨版本的领域对应关系作为独立的映射处理。有效FieldAssignment数量为零的对象归入待分类集合，并在查询和统计结果中单独展示。",
 'SRS DR-05；SPEC §3.1～3.2、§6.3',nature='基线对象；目录树结构为A2选择')
cls('FieldAssignment','领域标注','B',
 ['assignmentId: ID','basis: EvidenceRef[1..*]','confirmation: RelationStatus','taxonomyVersion: String','validPeriod: TimeInterval'],
 ['confirmMapping(evidence)','retireMapping(reason)'],
 "领域标注连接一个领域与一个成果或学者，并记录映射依据、目录版本和确认状态。同一对象允许具有多个领域标签。",
 "Work端与Scholar端应当满足恰有一个标注对象的互斥约束。同一对象、领域和目录版本的有效标注按照集合去重。确认分类应当具有分类依据及审核结果。统计总体数量时，系统按照规范成果集合去重，领域分项分别按照各自的成员集合计算。",
 'SRS DR-05、BR-07；SPEC §3.2、§6.3、§8.1',level='支撑',nature='分类来源与版本的分析细化')

cls('DataSource','数据源','C',
 ['sourceId: ID','name: String','accessPolicyRef: String','configVersion: String','enabled: Boolean','verifiedAt: Instant[0..1]'],
 ['validateAccessPolicy(): ValidationResult','disable(reason)'],
 "数据源登记公开来源的访问条件、许可范围、访问频率和配置版本。候选来源的接入状态在完成核验后更新为已接入。",
 "敏感访问凭证保存在受控配置中，数据源对象仅保存配置引用。公开数据按照允许公开的字段清单输出。来源停用后，系统继续保留已经采集的内容和任务历史，并分别保存来源更新时间和平台观察时间。",
 'SRS UC5.1、DR-06；SPEC §2.1、§2.4')
cls('SourceRecord','原始来源记录版本','C',
 ['sourceRecordId: ID','sourceKey: String','rawChecksum: String','rawRef: String','sourceUpdatedAt: Instant[0..1]','isSimulated: Boolean'],
 ['compareChecksum(other): Boolean','retainRawVersion()'],
 "原始来源记录版本表示某一来源稳定键对应的一次原文内容版本。稳定键保持相同而内容校验值发生变化时，系统创建新版本；稳定键和校验值均相同时，系统复用原版本并追加采集观测。",
 "系统应当独立保存原始内容和规范字段。数据源、稳定键及rawChecksum共同标识原文版本。一个公告包含多项成果时，系统按照来源映射契约拆分子记录并保留原页引用。某次采集结果中缺少既有记录时，系统继续保留该记录，并按照来源删除确认规则处理后续变化。",
 'SRS DR-01、DR-06、BR-05；SPEC §2.2、§3.1、§4.3')
cls('CollectionTask','采集任务','C',
 ['taskId: ID','state: CollectionState','fixedWindow: TimeWindow','scope: Scope','configAndRuleVersion: VersionRef','cursor: String[0..1]','successWatermark: Instant[0..1]','retryCount: Integer','retryPolicy: RetryPolicyRef','stopRequested: Boolean','executionAttempt: AttemptRef'],
 ['dispatch(attempt)','commitCheckpoint(batch)','fail(error)','scheduleRetry(policy)','stopAtBoundary(attempt)','succeed(summary)'],
 "采集任务按照固定的数据源、范围、时间窗口、配置版本和规则版本执行采集。任务记录开始时间、结束时间、停止请求、执行尝试和处理数量。",
 "任务状态严格采用既有的六种状态。批次事务提交成功后，任务推进cursor。整个固定窗口的规范处理、校验和后续更新登记完成后，任务推进successWatermark。停止请求使用stopRequested控制字段表达。系统只接受当前有效执行尝试的写入请求。",
 'SRS UC5.1、§4.1.3、REL-01；SPEC §2.1～2.4')
cls('CollectionObservation','采集观测','C',
 ['observationId: ID','observedAt: Instant','batchKey: String','parserVersion: String','ruleVersion: String','processingOutcome: ProcessingOutcome'],
 ['recordOutcome(result, counts)'],
 "采集观测表示某一任务对某一原文版本的一次业务观察。该对象连接采集任务与来源记录，并保存规范处理阶段的结果。",
 "多个任务可以分别观察相同内容。同一任务的有效批次重放应当按照观测幂等键去重。ProcessingOutcome独立描述待处理、处理中、已提交、待复核、隔离和错误等处理结果；CollectionState描述任务整体的六种状态。",
 'SPEC §2.1～2.3；SRS DR-06、REL-01',level='支撑',nature='SPEC已明确采集观测，采用关联对象表达')
cls('SourceMapping','来源映射','C',
 ['mappingId: ID','validPeriod: TimeInterval','ruleVersion: String','decisionEvidence: EvidenceRef[1..*]'],
 ['linkVerifiedTarget(target)','supersedeMapping(newTarget, reason)'],
 "来源映射将原始来源记录版本关联到规范成果或专利公开文献。映射独立于原始内容保存，并支持纠正、重定向和恢复。",
 "Work端与PatentDocument端应当满足恰有一个映射目标的互斥约束。一个原文版本至多具有一个当前有效的规范目标，并允许保留多条历史映射。隔离记录或待复核记录的有效映射数量可以为零。专利文献通过所属申请参与Patent的授权申请统计，统计按照申请身份去重。",
 'SRS BR-05、DR-02；SPEC §4.1、§4.3',level='支撑',nature='来源映射的分析细化')

cls('UpdateRecord','更新记录','D',
 ['updateId: ID','targetRefs: BusinessRef[1..*]','beforeAfter: RevisionRef','ruleVersion: String','reason: String','downstreamOutcome: UpdateOutcome'],
 ['registerFollowUp(workSet)','recordPublishOutcome(result)','requestRecovery(evidence)'],
 "更新记录保存规范数据或业务关系的变更、前后版本、变更依据以及后续索引和统计的更新结果。记录由采集处理或人工治理产生，用于支持修订追溯和恢复。",
 "业务变更及其后续工作登记应当可靠提交，提交结果作为成功判断依据。系统保留失败后的重建入口，恢复操作应当核对后续修订。downstreamOutcome单独表达后续更新结果，CollectionState表达采集任务状态。具体提交机制由架构设计确定。",
 '任务书需求分析对象清单；SRS UC5.4、BR-05、DC-02；SPEC §4.3、§6.3、§9')
cls('GovernanceReview','数据治理复核','D',
 ['reviewTaskId: ID','targetRefs: BusinessRef[1..*]','evidence: EvidenceRef[1..*]','decision: GovernanceDecision[0..1]','reason: String[0..1]','version: Integer'],
 ['recordDecision(decision, expectedVersion)'],
 "数据治理复核汇集重复记录、强标识冲突、人物身份候选、机构身份候选、字段冲突及成果归属纠正等处理资料。具有相应权限的管理员据此选择合并、分别保留、建立版本关系、等待证据或修改字段。",
 "复核决定、实际变更和审计记录应当可靠提交。系统应当拒绝过期版本的修改请求，并优先处理强标识冲突。GovernanceReview描述数据治理待办，ReviewRecord描述门户审核历史，两类对象分别采用对应的状态和记录规则。",
 'SRS UC5.3、BR-05；SPEC §4.2～4.3、§5、§9',level='支撑',nature='基线复核职责的分析细化')
cls('PublicRelease','公开数据版本','D',
 ['releaseId: ID','snapshotRef: String','taxonomyVersion: String','ruleVersion: String','dataScope: Scope','readiness: ReleaseReadiness','publishedAt: Instant[0..1]'],
 ['validateConsistency(): ValidationResult','markReady()','publish()','resolveEntry(workId)'],
 "公开数据版本表示经过校验的统一发布版本，涵盖公开成果、来源、贡献关系、目录、检索和统计。该对象确定用户查询所使用的数据版本范围。",
 "本模型采用SPEC中的候选发布设计表达已经确认的同一版本查询要求。切换版本前，系统应当校验数量、标识和样例；切换失败时，系统继续提供上一版本。令牌过期时，系统返回明确的版本失效结果。访问历史版本时，系统仍应当执行当前生效的权限规则。",
 'SRS BR-04、REL-02、DC-02、UC2.1、UC5.4；SPEC §6.3、§8.4',nature='推荐分析抽象，具体发布机制待架构评审')
cls('ReleaseEntry','公开版本条目','D',
 ['entryKey: ReleaseWorkKey','workVersion: Integer','publicSnapshotRef: String','relationSnapshotRef: String','sourceVersionRefs: SourceRef[1..*]'],
 ['readPublicView(permissionContext)'],
 "公开版本条目保存某一发布版本中指定规范成果的固定公开数据，包括当时的贡献、署名机构、分类和来源版本引用。查询应当按照条目记录的版本读取对应字段及关系。",
 "releaseId与workId共同确定条目的唯一身份。每个条目属于一个发布版本，其生命周期遵循该版本的保留策略。条目清理后，系统继续保留规范成果、原始内容和审计记录。公开快照仅包含允许公开的字段及来源引用。",
 'SRS BR-04、DC-02；SPEC §6.3、§8.4',level='支撑',nature='同一版本明细的分析细化')

R=[]
def rel(a,b,am,bm,label,group,why,kind='association'):
 R.append(dict(id=f'R{len(R)+1:02}',a=a,b=b,am=am,bm=bm,label=label,group=group,why=why,kind=kind))

rel('Account','ClaimApplication','1','0..*','提交','A',"每份申请对应一个申请账号，一个账号可以具有多份历史申请。在审申请的重复提交按照INV-04进行控制。")
rel('ClaimApplication','ScholarPortal','0..*','1','目标门户','A',"每份申请对应一个目标门户，一个门户可以具有来自多个账号的历史申请。管理权限按照有效的PortalAuthorization确定。")
rel('Scholar','ScholarPortal','1','0..1','公开展示','A',"每个门户对应一个学者。每个学者的门户数量为零或一个，其中至多一个当前规范门户属于本次设计约定。")
rel('Account','PortalAuthorization','1','0..*','获得授权','A',"每条授权对应一个账号。一个账号可以具有多条历史授权，其中当前有效的本人门户授权至多一条。")
rel('PortalAuthorization','ScholarPortal','0..*','1','管理目标','A',"每条授权对应一个门户。一个门户可以具有多条历史授权，其中当前有效的管理授权至多一条。")
rel('ClaimApplication','PortalAuthorization','1','0..1','通过后产生','A',"每条授权由一份已经审核通过的门户申请产生，每份申请至多产生一条授权。后续撤销授权时，系统继续保留申请及授权的历史记录。")
rel('ClaimApplication','ReviewRecord','1','0..*','审核历史','A',"每条审核记录对应一份申请。一份申请可以经过多次材料补充和审核，审核记录数量从零开始。普通关联支持审核历史的独立保留。")
rel('Account','ReviewRecord','1','0..*','审核人','A',"每条人工审核记录对应一个具有审核权限的账号。系统依据该权限校验记录写入请求。")
rel('ClaimApplication','ClaimApplication','0..1','0..*','前次 / 再申请','A',"每份再次提交的申请至多关联一份前次申请，一份历史申请可以关联多份后续申请。系统继续保留前次申请的终态。")
for child in ['Paper','Patent','Project','Award']: rel(child,'Work','','','泛化','B',"四种具体成果构成Work的完整且互斥的子类型集合。系统仅实例化具体成果类型。",'generalization')
rel('Work','Contribution','1','0..*','贡献关系','B',"每条贡献关系对应一个成果。贡献资料缺失时，成果的贡献数量可以为零，公开详情应当展示待补充状态。")
rel('Scholar','Contribution','0..1','0..*','个人主体 XOR','B',"每条贡献关系至多对应一个学者。选择学者主体后，机构主体端保持为空。同一学者与同一成果至多具有一条有效贡献关系。")
rel('Institution','Contribution','0..1','0..*','机构主体 XOR','B',"正式单位奖或机构承担任务的记录可以使用机构主体。机构端与学者端共同满足恰有一个贡献主体的约束。")
rel('Scholar','Affiliation','1','0..*','任职历史','B',"每段任职关系对应一个学者。一个学者可以先后或同时具有多段任职关系。")
rel('Institution','Affiliation','1','0..*','任职机构','B',"每段任职关系对应一个机构。任职结束后，系统继续保留机构对象和历史任职记录。")
rel('Contribution','ContributionAffiliation','1','0..*','当时署名','B',"每条成果发生时的机构关系对应一条贡献关系。一条贡献关系可以关联多个当时的署名机构，并独立于当前任职关系保存。")
rel('Institution','ContributionAffiliation','1','0..*','署名机构','B',"每条署名机构关系对应一个机构。机构统计按照规范成果标识与机构标识进行去重。")
rel('Institution','Institution','0..1','0..*','上级 / 下级','B',"本模型规定，同一机构目录快照中的每个机构至多具有一个直接上级，并满足无环约束。机构合并和拆分历史通过history保存。")
rel('Institution','Project','1','0..*','资助','B',"本版模型为每个项目记录一个用于身份识别的资助机构。共同资助的扩展设计列入后续评审。机构身份待确认时，系统保留来源证据及确认状态。")
rel('Institution','Award','1','0..*','授奖','B',"每项获奖对应其奖励体系中的一个授奖机构。联合授奖的详细表达列入后续模型扩展。")
rel('Patent','PatentDocument','0..1','0..*','申请对应文献','B',"每份文献至多对应一个已经确认的申请。申请尚待解析时，该关联数量为零。一个申请可以对应多份公开文献。")
rel('Patent','PatentFamily','0..*','0..*','按口径归入','B',"申请按照各个来源的家族口径建立多对多关联。成员关系依据scheme和来源证据解释，申请身份继续由司法辖区与申请号确定。")
rel('ResearchField','ResearchField','0..1','0..*','父领域 / 子领域','B',"同一分类版本采用支持多个根节点的无环树结构。分类待确认的对象通过有效标注数量为零表达。")
rel('ResearchField','FieldAssignment','1','0..*','标注领域','B',"每条领域标注对应一个指定目录版本中的领域。同一对象可以通过多条标注关联多个领域。")
rel('Work','FieldAssignment','0..1','0..*','成果对象 XOR','B',"每条标注在成果与学者之间选择一个目标。选择成果后，学者端保持为空。")
rel('Scholar','FieldAssignment','0..1','0..*','学者对象 XOR','B',"每条标注在学者与成果之间选择一个目标。选择学者后，成果端保持为空。学者领域标注应当保存依据和目录版本。")
rel('DataSource','SourceRecord','1','0..*','原文版本','C',"每个原始记录版本来自一个数据源。一个数据源可以保存多个稳定键及其对应的内容版本。")
rel('DataSource','CollectionTask','1','0..*','固定来源','C',"每个采集任务固定一个数据源和时间窗口。跨来源采集通过分别建立多个任务进行调度。")
rel('CollectionTask','CollectionObservation','1','0..*','批次观测','C',"每条采集观测对应一个任务。任务进入实际采集之前，其观测数量为零。")
rel('SourceRecord','CollectionObservation','1','0..*','观察内容','C',"每条采集观测对应一个原文版本。同一版本可以在多个任务或规则处理过程中分别产生观测。")
rel('SourceRecord','SourceMapping','1','0..*','映射历史','C',"每个原文版本可以具有多条历史映射。目标确认之前，有效映射数量为零；目标确认之后，当前有效映射至多一条。")
rel('Work','SourceMapping','0..1','0..*','成果目标 XOR','C',"每条映射在成果与专利文献之间选择一个目标。多个来源版本可以关联同一规范成果。")
rel('PatentDocument','SourceMapping','0..1','0..*','文献目标 XOR','C',"具有明确文献标识的专利来源映射到PatentDocument，并通过所属申请关联参与授权成果展示。")
rel('CollectionTask','CollectionTask','0..1','0..*','前次 / 新任务','C',"SUCCEEDED或STOPPED任务再次执行时，系统创建新任务并关联前次任务，前次任务继续保留原终态。")
rel('CollectionTask','UpdateRecord','0..1','0..*','产生变更','D',"一个采集任务可以产生多条更新记录。由人工治理产生的更新记录允许保持采集任务引用为空。")
rel('Work','UpdateRecord','0..*','0..*','受影响成果','D',"一次成果合并可以影响多个成果。关系更新或机构更新通过targetRefs指明目标；更新范围仅涉及这些对象时，成果端允许为空。")
rel('GovernanceReview','UpdateRecord','0..1','0..*','决定后的修订','D',"一次复核可以产生多条修订。复核决定为等待证据或分别保留时，修订数量可以为零。按照已确认规则执行的采集更新允许保持复核引用为空。")
rel('SourceRecord','GovernanceReview','0..*','0..*','复核证据','D',"一次复核可以采用多个来源版本作为证据，一个来源版本可以支持多次复核。私有证据按照其独立访问规则保存。")
rel('Account','GovernanceReview','0..1','0..*','当前处理人','D',"复核任务分配之前，当前处理人引用为空。人工决定提交时，系统应当记录具有审核权限的处理账号。")
rel('PublicRelease','ReleaseEntry','1','0..*','拥有快照条目','D',"每个条目仅属于一个发布版本，条目的业务身份及生命周期均依赖该版本。模型允许版本的条目数量为零。",'composition')
rel('Work','ReleaseEntry','1','0..*','规范成果身份','D',"一个规范成果可以出现在多个发布版本中，每个版本至多具有一个对应条目。条目按照固定快照读取公开字段和关系。")
rel('UpdateRecord','PublicRelease','0..*','0..*','覆盖修订','D',"一个发布版本可以覆盖多次修订，同一次修订可以由后续多个全量快照保留。发布成功后，系统登记对应修订的公开结果。")

CLAIM_STATES=['DRAFT','PENDING_REVIEW','NEED_MORE_INFO','APPROVED','REJECTED','WITHDRAWN']
COLLECTION_STATES=['PENDING','RUNNING','SUCCEEDED','FAILED','RETRYING','STOPPED']
GROUPS={'A':'账号、学者与门户授权','B':'四类成果、贡献与领域','C':'来源、采集与规范映射','D':'治理、更新与公开版本'}

if __name__=='__main__':
 data=dict(classes=C,relations=R,groups=GROUPS,version=VERSION,date=DATE,claim_states=CLAIM_STATES,collection_states=COLLECTION_STATES)
 (OUT/'_work'/'model.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'classes={len(C)}, relations={len(R)}')
