"""Rebuild v1.1 against the existing workspace; v1.0 remains untouched."""
from pathlib import Path
import json,hashlib,shutil,re
import content,diagrams

ROOT=content.ROOT;BUILD=Path(__file__).parent
OUT=ROOT/'需求分析/A组-需求分析整合版-v1.1'
diagrams.OUT=OUT;diagrams.FIG=OUT/'图件';diagrams.SRC=OUT/'模型源文件'

def replace(old,new):
    count=sum(p.count(old) for p in content.PAGES)
    assert count, old
    content.PAGES[:]=[p.replace(old,new) for p in content.PAGES]

replace('本组整合版 v1.0','本组整合版 v1.1')
replace('第9章查看交付与评审记录','第9章查看交付与评审记录，第10章查看Group2与B5的对照和具体修订')
replace('由Codex辅助整合和补建','由Codex辅助整合和补建；v1.1纳入Group2与B5对照')
replace('本次没有读取或对比B组当前模型，没有补造跨组独立性比较结论。','v1.1已核对GitHub Group2提交b93110b及用户补充的B5 v0.9。v1.0文件保留，修订与来源见第10章；文件快照不等于双方成员签署的独立冻结或正式互评。')
replace('权限修订变化时作废并重算','权限修订变化时作废并要求显式重试')
replace('QX05按同一ReleaseEntry快照取公开字段，返回前再确认权限修订。若变化，在同一公开版本下重新计算一次；仍持续变化则返回刷新提示。跨页时发现令牌权限版本过期也要求重算。该有界重算和令牌方案是本次设计决策，具体数据结构及索引产品后续确定。',
'''QX05仅在ID集合非空时读取同一ReleaseEntry快照。QX04a取得真实total后校验页码：page=1且total=0允许返回空集；其余页码超过ceil(total/page_size)返回越界错误。该空集第二页约定是本次设计选择。查询、读取或同版校验已失败时，先返回对应错误；不以“权限变化”掩盖已知故障。

QX06在返回前确认权限修订与页内权限。若变化，作废本次结果并要求显式重试，不返回旧total、facets或部分列表，也不在请求内部重算。跨页令牌权限修订过期同样提示重新查询。此策略参考B5 M25～M30，替代v1.0的一次内部重算方案。新请求仍固定原公开版本；旧版已失效时才要求显式重新绑定。详情也在同版读取后通过Q15a再次校验，失败走Q13。''')
replace('| T20 权限返回前持续变化 | 有界重算后明确刷新失败，不循环等待或泄漏旧计数 | QX06～QX08覆盖；为新增设计方案 |','| T20 权限返回前变化 | 作废本次结果，明确要求重试；不返回旧计数或部分列表 | QX06～QX08及Q15a覆盖；v1.1策略 |')
replace('| T18 权限在分页间撤销 | 新请求不能读取旧权限内容；列表总数分面同范围重算 |','| T18 权限在分页间撤销 | 旧令牌提示重试，新查询按当前范围统一计算；拒绝旧权限内容 |')
replace('| 关键词和标识 | 精确合法DOI、申请／公开号等先按相应类型解析；无效标识提示，不强行变成规范ID |','| 关键词和标识 | 显式标识字段或可识别标识按类型解析；非法标识提示。普通关键词包含斜杠不自动当作坏DOI |')
replace('| 排序 | 默认文本相关度；并列按业务年份降序、未知年份置后、规范ID升序。跨类型默认分组，原始评分不直接混排 |','| 排序 | 有关键词默认文本相关度；同分按业务年降序、未知置后、ID升序。无词浏览按公开投影的规范成果首次收录时间降序、ID升序，不用重复观测时间顶置 |')
replace('| 分页 | page_size默认10、最大100；非法页码和过期查询令牌给出具体原因 |','| 分页 | page_size默认10、最大100，约束整页。all按论文、专利、项目、奖励固定分组串接后统一分页；页码范围在total返回后校验 |')
replace('BM25字段权重title^4', '无关键词但有筛选可浏览；完全空条件按SPEC §6.1的最新收录顺序。为使分页可复现，本版将“收录时间”明确为公开投影中规范成果首次收录时间，固定在release内；不以来源发布日期替代。all的组内使用生效排序，组间不比较原始相关度；跨页可延续同一分组，分组标题随结果保留。以上分组串接和收录时间字段含义是设计选择。\n\nBM25字段权重title^4')

# Main detail revalidation and an explicit optional projection read.
main=next(x for x in diagrams.SPECS if x['file']=='06-检索请求处理时序图')
idx=next(i for i,r in enumerate(main['rows']) if r.get('id')=='Q16')
main['rows'][idx:idx]=[
    diagrams.msg('Q15a',2,4,'同版读取后重验当前权限及读取完整性'),
    diagrams.frame('break','权限变化／读取失败／同版不可满足',[diagrams.band('执行Q13对应错误响应并结束；不返回详情，不回退最新版本')])]
child=next(x for x in diagrams.SPECS if x['file']=='06a-检索权限计数与分页子交互')
idx=next(i for i,r in enumerate(child['rows']) if r.get('id')=='QX05')
child['rows'][idx:idx+1]=[
    diagrams.msg('QX04a',0,0,'依据实际total校验页码；total=0仅page=1有效'),
    diagrams.frame('break','页码超出有效范围',[diagrams.band('返回页码错误并保留条件；不读取详情，不伪装有效空集')]),
    diagrams.frame('opt','规范ID页非空',[diagrams.msg('QX05',0,3,'按同一release批量读公开条目和来源；核对完整性')])]
for r in child['rows']:
    if r.get('kind')=='frame' and r.get('op')=='alt':
        for row in r['rows']:
            if row.get('text')=='本次结果作废；同一release下重算一次，仍变化则提示刷新':row['text']='本次结果作废；要求显式重试，不返回旧total／facets或部分列表'
child['rows'].insert(2,diagrams.frame('break','续页令牌的权限修订已过期',[diagrams.band('返回查询上下文冲突；保留条件，要求重新查询')]))
idx=next(i for i,r in enumerate(child['rows']) if r.get('id')=='QX04a')
child['rows'].insert(idx,diagrams.frame('break','查询超时／索引失败／查询返回版本不一致',[diagrams.band('立即返回查询或版本错误；不作页码判断，不把故障当0条')]))
idx=next(i for i,r in enumerate(child['rows']) if r.get('id')=='QX06')
child['rows'].insert(idx,diagrams.frame('break','公开读取失败／同版条目缺失',[diagrams.band('立即返回读取或一致性错误；不返回部分列表，不由权限变化覆盖故障')]))
for r in child['rows']:
    if r.get('kind')=='frame' and r.get('op')=='alt':
        r['rows']=r['rows'][:-2]
        r['rows']+= [diagrams.otherwise('权限校验服务失败'),diagrams.band('明确失败并保留条件；不返回旧计数或部分成功')]
child['rows'].append(diagrams.ref('已知查询／读取错误先返回；无错误时再判断权限变化；成功才进入主图Q07'))
main['rows']=[dict(r,text=r['text'].replace('QX01—QX08','QX01—QX08（含QX04a）')) if r.get('kind')=='ref' else r for r in main['rows']]

content.page('10 Group2与B5的来源和基线差异','''
本章将外部模型作为对照输入。当前整合继续采用工作区SRS/SPEC v2.0；Group2有自己的v1.1基线，其模型不能直接替换本组状态和术语。文件交付时间相近不代表规则相同。

| 来源 | 实际取得内容 | 采用边界 |
| --- | --- | --- |
| GitHub caw111/SoftwareAnalyse 的Group2 | 提交b93110b8964e9061469bcfab8d0ced701f3d4526，2026-10-26 16:50:09 +08:00；报告、15场景CSV、四张原生Draw.io及PNG/SVG | 按此固定提交比较；没有切换或覆盖当前工作区 |
| 用户补充的B5压缩包 | B组B5吴星宇v0.9，SRS/SPEC v2.0；两张PlantUML图、六份说明及检查记录 | 个人交付，不等同于Group2整组报告；保留本人未确认状态 |
| 本组v1.0 | 28类45关系，原有A2/A3与本次补图 | 保留文件与SHA-256，v1.1另建目录；不补写成员签署冻结 |

| 冲突项 | Group2报告 | 当前v2.0及本组采用规则 |
| --- | --- | --- |
| 认领状态 | 九状态，含PENDING_VERIFICATION、VERIFYING、UNDER_REVIEW | 六状态；验证步骤与审核占用是过程或内部字段，不能新增业务状态 |
| 采集成功 | SUCCESS | SUCCEEDED；并非同时保留两个成功状态 |
| 预算耗尽 | 保持FAILED，管理员放弃才STOPPED | 重试耗尽按当前基线进入STOPPED；不可重试配置等故障保留FAILED供人工处理 |
| 门户建模 | 门户与管理绑定折叠在Scholar及关联中 | ScholarPortal、PortalAuthorization分离，显式记录有效期、版本和撤销历史 |
| 关系与投影 | 15个较粗类，部分版本和权限由职责契约表达 | 28类显式展开贡献机构、观测、公开版本和条目；不能按类数量直接评优 |

基线裁决以现有需求条目为依据；若全组以后决定改用Group2基线，必须同步修订SRS、SPEC、状态图、时序、场景及迁移规则，不能只改一个枚举名。外部材料中的PPT或分工要求保留为来源内容，本次按用户要求完成详细文档和图片。
''')
content.page('10 1 对象与交互逐项对照','''
| 对照点 | Group2或B5的表达 | 本组处理及理由 |
| --- | --- | --- |
| 四类成果 | AcademicOutcome继承Paper、Patent、ResearchProject、Award | 映射Work四子类；专利另有PatentDocument与PatentFamily，避免文献数当成果数 |
| 贡献与机构 | OutcomeContributor加成果机构关联，单位贡献可由成果机构承载 | Contribution主体Scholar XOR Institution；ContributionAffiliation显式保存同次贡献机构与证据 |
| 来源版本与重复出现 | SourceRecord保存内容版本，CrawlTask多对多观察 | SourceRecord不可变，CollectionObservation独立保存每次观测及处理结果；SourceMapping记录归并依据 |
| 更新记录 | UpdateRecord目标联合，承接变更和追踪 | 保留C25；查询索引不作为权威实体，更新登记必须可靠提交 |
| 认领与成果确认 | Group2另列ResearcherOutcomeClaim | 本报告关键用例只处理门户；成果确认需求仍由贡献及需求追踪承接，不把门户批准当成果确认 |
| 采集主交互 | Group2 17条消息，强调全窗完成和发布分开 | 沿用A3 M21/N11/X10；保留页事务、规范入库事务、执行尝试与整窗水位细节 |
| 认领主交互 | Group2 18条消息，九状态验证流程 | 采纳版本、私有材料及原子绑定的核对点；六状态流程沿用CL/CX，不导入多出的状态 |
| 检索主交互 | Group2 14条消息；同版规范ID读取，实时权限 | 保留本组Q/QX并细化返回前再校验；B5将公开读取职责独立展开供对照 |
| 权限变化 | B5 M25～M30作废结果并重试 | v1.1采用此保守策略；替代v1.0的内部一次重算，减少返回时点的不确定性 |
| 页码与空集 | B5 M20～M24：先得total，再判越界，非空才读取 | v1.1新增QX04a及break、opt片段，主图Q15a补详情读取后的权限检查 |

对应不等于完全等价：Account↔User、ResearchField↔AcademicField等是术语映射；PublicRelease在B5中只是职责契约，不应声称其已在Group2十五类图内显式落模。双方采用相同的“来源追踪、同贡献条件、同版读取”等原则，也不足以证明模型已由真人互评通过。

引用定位：Group2报告§3～4、§6～9及其消息索引；B5《检索模型说明》与两份puml，主图M20～M30、详情图D01～D20。源文件副本位于支撑材料/外部对照，逐文件校验见对照来源索引.json。
''')
content.page('10 2 检索边界和具体实现契约','''
新增QX04a和Q15a不会重新编号已有消息。主图与子图的成功返回都以同版读取完整、权限校验成功为前提；已知错误直接结束本次请求。

| 设计决策 | 具体约定 | 性质与依据 |
| --- | --- | --- |
| DEC-01 全类型分页 | 类型顺序Paper→Patent→Project→Award；组内按生效排序，串接后统一offset/page_size；每页合计≤page_size，保留分组标题 | 对SPEC默认分组的细化；不跨索引直接比较BM25原始分 |
| DEC-02 无词浏览 | 有筛选允许浏览；全空按最新收录。公开投影保存规范成果首次收录时间，release内固定；并列ID升序 | 空条件来源于SPEC §6.1；时间字段的精确定义是本次选择 |
| DEC-03 范围歧义 | 人物+机构要求same_contribution；若请求any_contribution则返回范围待确认错误，不能默改或扩大。无指定人物时可筛任一已确认贡献的机构 | 暂定接口保护规则，待基线澄清；B5 TODO-B5-01仍不冒称全局关闭 |
| DEC-04 取得总数后判页 | page正整数、1≤page_size≤100先验；实际total返回后校验上界。total=0时仅page=1合法 | 参数约束是基线；空集第二页处理为本次选择 |
| DEC-05 可见范围变化 | 返回前发现变化，作废结果，候选409并保留查询条件；客户端显式重试。续页旧权限令牌亦失效 | 参考B5 DEC-03；不返回旧计数或部分成功 |
| DEC-06 空集与故障 | total=0跳过公开条目读取，但仍重验权限；total>0而应读条目缺失视为同版错误 | B5 M20～M30；空集不触发无意义读取或掩盖故障 |
| DEC-07 标识与缺失 | 显式或可识别标识才校验标识格式；斜杠可作为普通文本。引用0与unknown、OA失败与非OA分开 | 保持原字段语义；不造事实 |

同贡献谓词：match(p,w,O)=存在贡献c，使c.work=w、c.scholar=p，且c的机构集合与O相交。person_mode=all要求每个指定人物各有匹配贡献；any要求至少一人匹配。O为空时只核对人物贡献；机构条件不从其他贡献“借用”。

对一个固定release、可见范围和筛选集合，total=去重后的规范成果数；facets也从该集合派生。分页只截取上述固定总序列，不能影响计数分母。真正实现时须选定索引读视图或等效一致性机制，不能仅靠两个独立HTTP调用“碰巧一样”。
''')
content.page('10 3 补充场景和预期输出','''
下面使用B5明确标为模拟的R1集合，与第6.4节A组R01样例分开。W01为2024论文，贡献(S1,O1)、(S2,O2)；W02为2023论文，贡献(S1,O2)；W03、W04为不同资助机构O9/O8下编号均0007的项目；W05为年份未知论文。S1与S3同名。

| 新场景 | 输入或并发事件 | 静态预期与对应图 |
| --- | --- | --- |
| V21 人物机构 | S1 + O2，same_contribution | 只有W02；W01的O2属于S2。QX03/C14/C17 |
| V22 多人all | 人物[S1,S2]，无机构条件 | W01；不能把两个人分别存在于不同作品当共同作品 |
| V23 多人any | 人物[S1,S2]，无机构条件 | W01、W02；规范ID去重 |
| V24 同号项目 | 项目编号0007，未选资助机构 | 提示机构/计划消歧；选择O9后W03，不能混W04 |
| V25 页码上界 | 当前可见总数3，page_size=2 | 第1页2条、第2页1条、第3页错误。QX04a |
| V26 空集第一页 | 过滤结果0条，page=1 | items=[]、total=0；跳过QX05但执行QX06 |
| V27 空集第二页 | 过滤结果0条，page=2 | 页码错误；不宣称有效空集。设计约定DEC-04 |
| V28 版本切换 | 列表绑定R1后R2发布，点击详情 | 仍读R1；R1失效则说明刷新，不换成R2。Q11～Q16 |
| V29 权限变化 | 查询和读取成功，返回前可见范围改变 | 作废全部结果及计数，提示重试。QX06～QX08 |
| V30 同版缺项 | 索引ID在指定release中无公开条目 | 明确一致性错误；不能从最新业务库补齐 |
| V31 普通斜杠 | 文本query为graph/search，未指定DOI | 普通文本查询；不能仅凭斜杠返回DOI格式错误 |
| V32 分组跨页 | 模拟四类结果按DEC-01组序，page_size=2 | 总序列连续分页，整页最多2条；组边界不丢项或重计 |

上述32项由原T01～T20和本次V21～V32组成，属于设计走查；不是32次运行通过。B5原35项和Group2原15项单独保留，不能直接相加称为满足SPEC“至少50组查询”的运行证据。检索50组固定查询、10,000条与20并发性能目标仍须在真实实现后验证。
''')
content.page('10 4 对照问题处理和提交边界','''
| 问题与来源 | 本次处理 | 当前状态 |
| --- | --- | --- |
| Group2九状态与本组六状态冲突 | 保留各自原件；整合图文统一当前v2.0，不混入验证和审核中状态 | 本版裁决已写明；非对方原稿已修正 |
| Group2 SUCCESS、耗尽FAILED与v2.0冲突 | 整合采用SUCCEEDED、耗尽STOPPED；旧执行尝试及索引边界继续保持 | 本版模型按当前基线统一 |
| B5 QA-01～04 其余岗位材料缺失 | GitHub已取得整组报告、类图和两条其他时序；并非B1～B4各岗位签署包，且基线有差异 | 更新“材料可获得”证据，不能关闭B组正式验收 |
| B5 QA-06 any_contribution歧义 | DEC-03给出暂定拒绝规则，防止静默扩大 | 本版处理路径明确；基线语义待团队确认 |
| B5 QA-07 分组分页与空集页码 | DEC-01/04明确，并增加QX04a与V25～V27/V32 | 本版设计已补，未运行验证 |
| B5 QA-08 权限变化策略 | 采用显式重试，替换v1.0内部重算，并补Q15a | 本版设计已统一，成员复审待实填 |
| B5 QA-09 任务书和附录缺失 | 当前工作区有任务书、用户截图和验收附录，列入输入依据 | 当前整合可核对；不改写B5编写时缺件事实 |
| B5 QA-05/10/11 工具、人审、独立冻结 | 保留真实状态；新增Draw.io不冒充CodeArts原生工程，文件哈希不冒充真人签署 | 正式工程要求和人审待实际记录 |

交付中“完成”指本版详细报告、缺失图件、可编辑源、对照记录和设计场景已生成并检查。模型业务行为、数据库并发约束、50组查询和性能数值尚无运行证据，不在本包虚填通过。

外部对照目录保存Group2四套图源、原报告Markdown/CSV和必要基线文本，以及B5两套图源和原说明；保留原署名与消息编号。原压缩包校验、固定提交、文件哈希和采用位置写入来源索引。引用副本不等于对原作者贡献重新署名。

15分钟汇报建议：1分钟交代任务，3分钟解释账号/门户/贡献/专利层次，3分半讲断点和整窗水位，3分钟讲原子授权及撤回竞争，3分钟讲同版和同贡献检索，最后1分半说明本章两项状态冲突与新增页码、权限场景。详细字段和完整关系留作答辩查阅。
''')

content.TALK=content.TALK.replace('权限修订变化时作废旧结果，在同版下重算；持续变化则要求刷新。','权限修订变化时作废旧结果，保留条件并要求显式重试；不能返回旧计数或部分结果。')
content.TALK=content.TALK.replace('如果查询的只是作品任一作者的机构，则口径不同，可以得到四条。','如果只按机构筛选、不限定A01，口径就不同；保留A01时不能借用其他作者的I01。')
content.TALK=content.TALK.replace('## 13分30秒至15分00秒 追踪验收与下一步','## 13分30秒至15分00秒 对照修订与验收')
content.TALK=content.TALK.replace('展示第8章追踪和走查。','展示第10章对照。Group2报告有四张完整模型，但采用较早v1.1的九状态和SUCCESS；本组保留当前v2.0的六状态和SUCCEEDED。B5按v2.0提出的取得total后判断页码、空集跳过读取、权限变化拒绝旧结果，已补入本组模型。用3条结果、每页2条说明第三页必须报错。再展示第8章追踪和走查。')

# Use the existing document formatter; revision driver supplies updated content/models.
source=(BUILD/'build.py').read_text(encoding='utf-8')
source=source.replace("学术成果分享平台需求分析    v1.0","学术成果分享平台需求分析    v1.1")
source=source.replace("QX01～QX08","QX01～QX08（含QX04a）")
exec(compile(source,str(BUILD/'build.py'),'exec'),{'__file__':str(BUILD/'build.py'),'__name__':'__main__'})

SUP=OUT/'支撑材料';EXT=SUP/'外部对照';EXT.mkdir(exist_ok=True)
refs=BUILD/'references';group=refs/'Group2-b93110b/前期成果'
for rel in ['需求分析/docs/学术成果分享平台_需求分析报告_v1.0.md','需求分析/docs/需求分析验收场景.csv','需求分析/image',
            '需求调研和建模/docs/系统需求规格说明书_SRS.md','需求调研和建模/docs/核心模块开发规范_SPEC.md']:
    p=group/rel;target=EXT/'Group2-b93110b'/rel;target.parent.mkdir(parents=True,exist_ok=True)
    if p.is_dir():shutil.copytree(p,target,dirs_exist_ok=True)
    else:shutil.copy2(p,target)
b5=refs/'B5/B组-B5-吴星宇-检索与一致性验收'
for p in list(b5.glob('*.md'))+list(b5.glob('*.png'))+list((b5/'07-建模源文件').glob('*.puml')):
    target=EXT/'B5-v0.9'/p.relative_to(b5);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
shutil.copy2(BUILD/'v1.0-before-revision.json',SUP/'v1.0修订前文件清单.json')
shutil.copy2(refs/'输入来源.json',SUP/'外部压缩包校验.json')
info={'github':{'repository':'https://github.com/caw111/SoftwareAnalyse','branch':'Group2','commit':'b93110b8964e9061469bcfab8d0ced701f3d4526','commit_time':'2026-10-26T16:50:09+08:00','url':'https://github.com/caw111/SoftwareAnalyse/tree/b93110b8964e9061469bcfab8d0ced701f3d4526/前期成果/需求分析'},
      'scope':'外部材料作对照，沿用本组v2.0；未代签双方冻结或人审',
      'files':[{'path':p.relative_to(SUP).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in EXT.rglob('*') if p.is_file()]}
(SUP/'对照来源索引.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
comparison='# Group2与B5逐项对照及修订\n\n'+'\n\n'.join(content.PAGES[-5:])
(SUP/'Group2与B5对照及修订.md').write_text(comparison,encoding='utf-8')
notes=(SUP/'来源与修订记录.md').read_text(encoding='utf-8')
notes=notes.replace('版本v1.0，2026-10-26','版本v1.1，2026-10-26').replace('查询令牌绑定权限修订','查询令牌绑定权限修订')
notes=notes.replace('将权限修订令牌和有界重算显式标为本次设计方案','将权限修订令牌和变化后显式重试标为本次设计方案')
notes+='\n\n## v1.1追加修订\n\n'+'''按用户补充请求取得Group2固定提交b93110b及B5原始ZIP，未执行其中脚本或消息任务。新增第10章五节逐项对照与12个补充设计场景，保留外部来源和署名；未将两套不同基线直接合并。完整裁决与局限见Group2与B5对照及修订.md。

新增QX04a（total后判断页码）和Q15a（详情读取后的当前权限复验），QX05改为非空ID才调用；权限变化改为显式重试，替代v1.0内部重算。细化普通斜杠文本、无词浏览、最新收录排序、all分组后统一分页及范围歧义处理。

v1.0文件保持不变；修订前文件清单用于验证文件差异，不证明成员签署冻结。GitHub Group2整体交付与B5个人交付分别保留，不标记B5或B组全员正式验收完成。所有走查均为分析设计核对，未运行平台。
'''
(SUP/'来源与修订记录.md').write_text(notes,encoding='utf-8')
readme=(OUT/'README.md').read_text(encoding='utf-8').replace('整合版 v1.0','整合版 v1.1')
readme+='\n## 本轮继续完成\n\n已加入Group2固定提交与B5个人包的逐项对照；报告第10章列出基线冲突、对象与消息映射、7项检索决策和12项补充设计场景。图6-1/6-2同步补齐页码后置校验、空集opt读取和最终权限复验。整合仍用本目录SRS/SPEC v2.0，外部原图不替换当前状态规则。\n\n建议先看详细报告，汇报使用支撑材料/15分钟汇报讲解稿.md。外部对照原文及源图保存在支撑材料/外部对照；对照来源索引.json可核对固定提交和逐文件哈希。\n'
(OUT/'README.md').write_text(readme,encoding='utf-8')
shutil.copy2(BUILD/'revision.py',OUT/'模型源文件/revision.py')
print(json.dumps({'revision':str(OUT),'pages':len(content.PAGES),'reference_files':len(info['files'])},ensure_ascii=False))
