from pathlib import Path
import re,json,shutil,csv,hashlib,zipfile
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

ROOT=Path.cwd(); B=ROOT/'.report-build/third-submit'
OUT=ROOT/'Submit/第9组-第三次作业-需求分析'
OLD=ROOT/'需求分析/A组-需求分析整合版-v1.1'
for d in ['图件','模型源文件','支撑材料/前期基线','支撑材料/AI历史记录','汇报材料']: (OUT/d).mkdir(parents=True,exist_ok=True)
def write(name,text): (OUT/name).write_text(text.strip()+'\n',encoding='utf-8')
def copytree(src,dst): shutil.copytree(src,dst,dirs_exist_ok=True)
copytree(OLD/'图件',OUT/'图件')
for f in (OLD/'模型源文件').iterdir():
 if f.suffix in ['.drawio','.json','.zip']:shutil.copy2(f,OUT/'模型源文件'/f.name)
copytree(ROOT/'docs',OUT/'支撑材料/前期基线/docs')
copytree(ROOT/'images',OUT/'支撑材料/前期基线/images')
for f in ['业务对象与关系完整字典.md','新增交互消息表.md','整合版32项设计走查.csv','原始A3-03-采集入库时序图说明.md','原始A3-03-采集六状态对照表.md']:
 shutil.copy2(OLD/'支撑材料'/f,OUT/'支撑材料'/f)
for d,fn in [('A1-昌昂旺','06-AI使用与人工验证记录.md'),('A2-赵琦','02-AI辅助和人工修订.md'),('A组-A3-王彦骁-采集入库-v1.2','03-AI使用与人工修订.md')]:
 f=ROOT/'需求分析'/d/fn
 if f.exists():shutil.copy2(f,OUT/'支撑材料/AI历史记录'/(d+'-'+fn))
model=json.loads((OLD/'模型源文件/A2-核心业务模型.json').read_text(encoding='utf-8'))
parts=(OLD/'本组-需求分析报告.md').read_text(encoding='utf-8').split('<!-- page -->')
P=[]
def page(title,body):P.append('## '+title+'\n\n'+body.strip())
page('学术成果分享平台需求分析报告','''第9组 1011101011 A组

第三次作业    2026年11月4日

本次作业承接前期需求调研和需求建模，说明平台管理哪些业务对象，以及数据采集、门户认领和公开检索如何围绕这些对象完成。报告包含28个业务类、45条关系和三条关键用例的时序模型，并逐项核对它们与SRS、用例图、活动图和状态图的对应关系。

我们将学者、账号、门户管理权和成果贡献分别建模。数据采集保留原文及处理依据，失败时从可靠断点恢复；认领通过后只授予指定门户管理权；检索的列表、总数和详情保持同版读取，并检查当前权限。这些规则贯穿后面的类图与时序图。

正文按业务对象识别、核心业务类图、交互模型、分析模型一致性、AI使用情况五部分组织。完整属性与操作字典、高清图及可编辑模型随报告提交。文中的设计场景用于检查模型，尚不代表平台已经实现或通过运行测试。

材料依据：本组调研报告，SRS与SPEC，A1对象识别资料，A2核心类图，A3采集模型，以及后续补建的认领和检索模型。''')
page('1 业务对象的识别依据','''对象识别从调研中反复出现的业务事实入手：需要长期保存身份、具有独立规则、会发生状态变化，或者需要追溯历史的内容，才作为业务对象。页面、按钮和搜索服务属于边界或控制职责，不直接加入核心业务类。

调研采用公开资料研究和场景推演，未开展真实访谈或问卷。下列依据来自已有调研记录，不将情景案例写成受访者经历。

| 调研发现及定位 | 对象与建模理由 | SRS对应 |
| --- | --- | --- |
| 调研场景一，同名作者会进入错误门户 | Scholar保存稳定身份与证据，Account保存登录资格，两者分离 | UC2.2，DR-01、DR-03 |
| 场景二，身份通过不等于门户和成果都属于本人 | ClaimApplication、PortalAuthorization、Contribution分别表达申请、管理权和贡献 | UC1.3，UC3.1～3.3，BR-01 |
| 场景三，项目编号、专利文献及奖励角色含义不同 | Work抽象共同字段，Paper、Patent、Project、Award保留类型身份 | §4.1.1，UC5.3 |
| 场景四，移除错误关联不能删除公共成果 | Contribution独立记录确认与撤销，Work继续保留 | UC3.3，SPEC §7 |
| 场景五，当前机构不能解释历史署名和机构产出 | Institution、Affiliation、ContributionAffiliation分别记录机构、任职与当时署名 | UC2.1、UC4.2，SPEC §5～6 |
| 场景六，来源失败和部分更新要能够恢复 | DataSource、CollectionTask、SourceRecord、CollectionObservation保留范围、原文、断点与处理结果 | UC5.1、UC5.3～5.4 |
| 调研报告的数据覆盖与更新问题 | UpdateRecord记录后续工作，PublicRelease固定公开内容版本 | UC5.4～5.5，SPEC §2、§6、§8 |

学术领域使用ResearchField和FieldAssignment表达分类体系、版本及标注依据。来源缺少学科时保持未分类，不凭题名推断为已确认标签。''')
for idx,title in [(3,'1.1 账号学者和认领相关对象'),(4,'1.2 四类学术成果'),(5,'1.3 贡献机构和学术领域'),(6,'1.4 采集任务与更新记录')]:
 body=parts[idx].strip().split('\n',1)[1]
 body=re.sub(r'完整类型、参数、可选性及45条关联.*?(?=\n|$)','完整属性类型、操作参数及需求依据见支撑材料《业务对象与关系完整字典》。',body)
 page(title,body)
page('2 核心业务类图','''![图2-1 核心业务类图](图件/02-核心业务类图.png)

图2-1 核心业务类图总览

图中保留28个业务类及45条关系。类框依次展示类名、属性与操作。总图用于定位各业务领域，后面的局部图说明具体关系。原图文字较多，可打开随附PNG或SVG放大查看。''')
class_titles=['2.1 账号身份与门户授权','2.2 成果类型的继承与专利文献','2.3 贡献机构和领域关系','2.4 原文版本与来源映射','2.5 更新与公开版本的组合关系']
for idx,title in zip(range(9,14),class_titles):
 body=parts[idx].strip().split('\n',1)[1]
 body=re.sub(r'图3-(\d)',lambda m:'图2-'+str(int(m[1])),body)
 if idx==10:body+='''

选择继承，是因为四类成果都具有规范标识、题名、来源证据、可见性及更新规则，检索和更新可以面向Work处理。Paper增加DOI与出版信息，Patent增加申请身份与授权证据，Project增加资助机构及批准号，Award增加奖励体系和年度。一条成果只能属于其中一种类型。

PatentDocument没有继承Work。它描述同一申请的公布或授权文献，一件申请可以对应多份文献。申请与文献采用关联，文献及其来源证据可以先存在、后核验归属，因此不把它们画成依赖申请删除的强组合。PatentFamily也保留独立身份及成员证据。
'''
 if idx==13:body+='''

组合表示生命周期上的强归属：ReleaseEntry是某个PublicRelease中的条目，脱离该公开版本就失去这条快照记录的意义。Work是可以被多个公开版本引用的公共成果，因此不随某个公开版本条目一起删除。机构、学者与成果之间也使用普通关联，撤销管理授权不会级联删除公共事实。
'''
 page(title,body)
for idx,title in [(14,'2.6 关联多重性和业务约束'),(15,'2.7 类操作的前后置条件')]:page(title,parts[idx].strip().split('\n',1)[1])
mapping={16:'3 交互模型 数据采集入库',17:'3.1 清洗去重子交互',18:'3.2 停止与重试子交互',19:'3.3 采集消息顺序和提交边界',20:'3.4 失败恢复与采集状态',21:'3.5 门户认领审核',22:'3.6 原子授权与撤回竞争',23:'3.7 认领申请的输入和状态',24:'3.8 批准事务及异常处理',25:'3.9 检索请求处理',26:'3.10 权限计数与分页子交互',27:'3.11 检索条件与结果契约',28:'3.12 同版读取与权限变化',29:'3.13 人物机构联合检索示例'}
for idx,title in mapping.items():
 body=parts[idx].strip().split('\n',1)[1]
 body=body.replace('本次补建。','').replace('本次设计','本报告采用的设计')
 body=re.sub(r'第6\.4节','第3.13节',body)
 body=body.replace('图4-','图3-A').replace('图5-','图3-B').replace('图6-','图3-C')
 body=re.sub(r'图3-C(\d)',lambda m:'图3-C'+m[1],body)
 body=body.replace('此策略参考B5 M25～M30，替代v1.0的一次内部重算方案。','此策略参考已有B5个人检索材料中的M25～M30，采用作废结果后显式重试的方式。')
 body=body.replace('假设固定窗口','假设固定采集时间范围')
 if idx==20:body+='\n\n这里的固定窗口指任务创建时确定的采集时间范围。分页断点只表示该范围内可靠登记到了哪里；如原文已登记而清洗未完成，恢复时还要继续处理积压工作。只有全部输入具有明确处理结果并完成校验，才推进成功水位。'
 page(title,body)
trace=[
 ['门户认领','UC3.1、UC3.5、UC5.2','01_科研人员用例图；门户认领审核流程活动图','ClaimApplication、PortalAuthorization、ReviewRecord','CL02～CL17；CX01～CX10','DRAFT、PENDING_REVIEW、NEED_MORE_INFO、APPROVED、REJECTED、WITHDRAWN','T02、T08～T10、T19'],
 ['采集入库','UC5.1、UC5.3、UC5.4','数据采集任务状态机；SRS UC5.1事件流','DataSource、CollectionTask、SourceRecord、CollectionObservation、SourceMapping、UpdateRecord','M01～M21；N01～N11；X01～X10','PENDING、RUNNING、SUCCEEDED、FAILED、RETRYING、STOPPED','T03～T07、T16'],
 ['成果检索与详情','UC2.1、UC2.2、UC2.3','普通用户用例图；作者检索详细活动图','Work、Scholar、Contribution、ContributionAffiliation、PublicRelease、ReleaseEntry','Q01～Q16含Q15a；QX01～QX08含QX04a','查询不另加成果业务状态；固定公开版本并实时校验权限','T11～T13、T18、T20、V21～V32'],
 ['公共成果维护','UC3.2～3.4、UC5.3','成果管理模块用例图及SRS用例规约','Work、Contribution、GovernanceReview、UpdateRecord','三条关键时序中的写入及后续登记；非本次独立第四条时序','撤销本人关系保留公共成果','T14、T15、T17']]
page('4 分析模型与前期需求的衔接','''本次分析沿用前期SRS的五个用例包。用例图确定参与者和业务目标，活动图说明步骤与分支，状态图限定对象可以发生的变化。类图说明这些行为由什么数据和对象承载，时序图进一步说明对象之间按什么顺序协作。

前期图中的UC01、UC13等是局部编号，不能直接当成本版SRS的UC1.1或UC3.1。这里按业务名称建立对应，再使用SRS编号追踪。所用前期图和原生Draw.io都保存在“支撑材料/前期基线/images”。

| 业务目标 | SRS定位 | 本次类与时序 |
| --- | --- | --- |
| 申请与管理本人门户 | UC3.1、UC3.5、UC5.2 | C01～C06，CL与CX交互 |
| 获取并清洗来源数据 | UC5.1、UC5.3 | C20～C26，M、N、X交互 |
| 增量更新与发布 | UC5.4、UC5.5 | UpdateRecord、PublicRelease、ReleaseEntry，M15～M21 |
| 检索与查看详情 | UC2.1～UC2.3 | Work、Contribution及公开版本，Q与QX交互 |

三条时序覆盖本次要求的关键用例，不把收藏、导出、合作网络等其他用例写成已经完整展开的交互。它们继续由前期SRS约束。''')
page('4.1 用例活动与消息顺序的核对','''门户认领活动图中的“提交材料、核验、补充、审核、授权”分别对应CL提交校验、CL14补充、CL15驳回和批准ref。拟批准后由CX完成授权事务，既保留活动图的业务顺序，又说明了批准时重新核验的必要性。材料超时保持可恢复状态，不走驳回分支。

采集任务由SRS UC5.1基本路径进入M01～M12，清洗去重由M13引用N子交互，停止或故障由X子交互承接。M15确认整个范围完成后才能成功，后续公开构建结果由M20～M21单独记录。这样与前期“采集、清洗、入库、更新”的步骤一致，也区分了“已入库”和“已公开”。

作者检索活动图中的人物消歧、条件组合、查找结果、查看详情分别对应Q中的候选选择、QX03条件约束、QX04共同允许集合和Q11～Q16同版详情。人物与机构联合查询沿同一Contribution处理，不能把另一作者的机构拼到目标作者上。

时序图中的页面和控制对象不要求出现在核心业务类图中。页面承担输入输出，控制对象协调跨实体操作，类图保留业务数据与规则。消息名称不同于实体方法时，在附带的消息表中核对实际责任，不能为了统一名称把所有操作都塞入Work。

典型映射：批准请求由ClaimControl协调ClaimApplication.approve、PortalAuthorization创建和ReviewRecord.appendDecision；取页由执行器协调来源访问与CollectionTask.commitCheckpoint；检索由检索控制协调版本、权限、索引和ReleaseEntry.readPublicView。''')
page('4.2 状态与跨模型约束的核对','''认领状态沿用SRS §4.1.2。DRAFT或NEED_MORE_INFO在材料有效提交后进入PENDING_REVIEW，审核只能从合法待审核状态作出决定。APPROVED、REJECTED和WITHDRAWN保留终态历史，再申请建立新记录。验证过程及审核占用使用内部字段，不额外加入VERIFYING或UNDER_REVIEW业务状态。

采集状态沿用SRS §4.1.3。RUNNING发生错误先记FAILED，可重试且预算允许时经RETRYING恢复RUNNING，预算耗尽转STOPPED。运行中停止先记录stopRequested，到安全边界退出。SUCCEEDED及STOPPED结束本次任务，再执行创建关联任务。

| 核对项 | 类图承载 | 时序保证 | 反例及预期 |
| --- | --- | --- | --- |
| 管理授权唯一且完整 | Account、ScholarPortal、PortalAuthorization | CX提交时复验双向唯一，申请、授权、决定及审计共同提交 | 两人同时批准，只能一方成功 |
| 已提交页面不丢失 | SourceRecord、CollectionObservation、CollectionTask | M11～M12可靠登记后推进断点 | 第一页成功第二页失败，保留第一页且可恢复 |
| 历史机构不被覆盖 | Affiliation与ContributionAffiliation分离 | QX03沿同一贡献匹配人物机构 | R06中作者机构交叉，不命中 |
| 同版内容与当前权限同时成立 | PublicRelease、ReleaseEntry及权限职责 | QX04同集合计数，QX06和Q15a返回前复验 | 权限变化作废结果，新版发布不偷偷替换旧版详情 |
| 个人关系撤销影响有限 | Work与Contribution普通关联 | 按指定贡献处理，不级联删除公共数据 | 移除错误作者不影响其他真实作者 |

32项设计场景附在CSV中，记录输入、预期和模型定位。这里的“覆盖”指能在模型里找到相应对象和路径，运行正确性及性能仍需实现后验证。''')
ai='''我们使用Codex辅助整理需求分析材料。AI读取本组已有调研报告、SRS、SPEC、业务类图和时序图，帮助核对对象名称、补写解释、生成认领与检索交互、整理追踪关系，并完成Word和PPT排版。本次提交整理日期为2026年11月4日。历史AI记录作为附件保留，不补写无法确认的模型版本或提示词。

声明方面，报告说明AI参与的内容及参考材料。A2核心类图和A3采集模型继承已有交付；认领及检索模型来自此前AI辅助补建。本轮主要重组正文、补足跨模型追踪、整理提交附件和修订展示材料。没有开展新的访谈、问卷、数据抓取或平台运行测试。

理解方面，成员需要能够解释四类成果为什么继承Work，专利申请为什么与文献分开，门户授权为什么不能代替成果贡献，以及断点与成功水位、同版读取与实时权限各自的含义。附带的案例和逐页讲稿用于准备讲解，不作为已经完成理解验证的证明。

责任方面，AI可以帮助发现遗漏和排版问题，是否采用业务规则及最终提交责任由成员承担。现有记录仍标注成员交叉复审未完成，本次没有收到新增的复审签字、答辩或教师评审记录，因此不填写“全组已审核通过”。实际可确认的人工反馈，是用户对汇报重点、图件使用和术语解释提出了修改要求，相关调整已落实到材料。

课程原任务书中的至少3个代码人工修正案例、至少2项Agentic Coding实践属于后续开发答辩要求。本次是需求分析提交，下列记录说明分析材料的修订过程，不将其冒充已完成的代码实践。'''
page('5 AI使用声明与人工验证情况',ai)
cases='''| 使用环节 | AI参与内容 | 现有验证或反馈 | 本次处理 |
| --- | --- | --- | --- |
| 对象识别 | 整理对象候选和SRS依据，生成字典 | 已有A2记录保留待成员复审状态 | 保留来源、稳定ID和对象边界，附完整字典 |
| 类图 | 生成可编辑图元、属性和关系说明 | 有程序结构核对；没有新增成员签字 | 沿用28类45关系及原图，解释泛化和组合选择 |
| 时序图 | 补建认领及检索交互，展开异常路径 | 与SRS、SPEC及已有模型进行自动静态对照 | 保留消息编号及Draw.io，附32项设计场景 |
| 一致性 | 整理用例、活动、状态与消息映射 | 本轮检查文件引用、状态集合和模型定位 | 单列第四章，保留前期图件和SRS快照 |
| 展示与语言 | 编排图解PPT和讲稿，解释图中术语 | 用户明确要求减少抽象表格、使用已有图件 | 沿用图解形式，改写固定窗口表述，按本次五项要求组织结尾 |

可确认的人工反馈及修订有以下几项。

1. 用户指出两组起始基准相同。后续材料按共同需求比较建模方式，本次报告不把版本标记差异写成两项不同任务。
2. 用户指出表格内容抽象，希望使用原图。汇报改用现有类图和时序图局部，保留完整图册备查。
3. 用户追问“固定窗口”的含义。讲解明确为预先确定的采集时间范围，并区分分页断点、积压处理与整窗成功水位。
4. 用户要求汇报突出需求分析。此次正文按对象、类图、交互、一致性、AI使用组织，去除以两组差异为主线的安排。

以上是实际用户反馈，不等同于对所有类、消息和并发约束完成了成员交叉复核。历史记录中的AI修订也不改记为人工修订。人工确认范围以真实记录为准。
'''
page('5.1 使用记录与实际修订',cases)
write('01-需求分析报告.md','# 学术成果分享平台需求分析报告\n\n'+'\n\n<!-- page -->\n\n'.join(P))
write('03-AI使用声明与验证记录.md','# AI使用声明与验证记录\n\n'+ai+'\n\n'+cases)
with (OUT/'支撑材料/业务对象与SRS对应表.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['编号','类名','中文名称','关键属性','操作','识别性质','SRS与SPEC依据'])
 for c in model['classes']:w.writerow([c['id'],c['name'],c['cn'],'；'.join(c['attrs']),'；'.join(c['ops']),c.get('nature',''),c['source']])
with (OUT/'支撑材料/跨模型一致性追踪表.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['业务','SRS用例','前期模型','核心对象','时序消息','状态与关键约束','场景']);w.writerows(trace)

# Word body uses the same logical pages and unmodified source figures.
doc=Document(); sec=doc.sections[0]
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.8);sec.left_margin=Cm(2.1);sec.right_margin=Cm(2.1)
sec.header_distance=Cm(.7);sec.footer_distance=Cm(.7)
for name,size in [('Normal',10.5),('Title',22),('Heading 1',15),('Heading 2',12),('Caption',9)]:
 s=doc.styles[name];s.font.name='Calibri';s.font.size=Pt(size);s.font.color.rgb=RGBColor(0,0,0)
 s._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体' if name=='Normal' else '微软雅黑')
 s.paragraph_format.space_after=Pt(7);s.paragraph_format.line_spacing=1.15
 if name not in ['Normal','Caption']:s.font.bold=True
# Remove the starter template's decorative paragraph rules.
for pr in doc.element.xpath('//w:pBdr'):
 pr.getparent().remove(pr)
for pr in doc.styles.element.xpath('//w:pBdr'):
 pr.getparent().remove(pr)
header=sec.header.paragraphs[0];header.text='第9组  学术成果分享平台  第三次作业';header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
for r in header.runs:r.font.size=Pt(8)
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
def clean(t):return re.sub(r'`([^`]+)`',r'\1',t).replace('**','').replace('<br>','\n')
def table(lines):
 rows=[[clean(c.strip()) for c in l.strip('|').split('|')] for l in lines if not re.match(r'^\|[\s:|\-]+\|$',l)]
 n=len(rows[0]);t=doc.add_table(rows=0,cols=n);t.autofit=False
 widths={2:[4,12.8],3:[4,7.1,5.7],4:[3.5,4.5,4.8,4]}.get(n,[16.8/n]*n)
 for c,w in zip(t.columns,widths):c.width=Cm(w)
 for i,row in enumerate(rows):
  cells=t.add_row().cells
  for j,c in enumerate(cells):
   c.width=Cm(widths[j]);c.text=row[j] if j<len(row) else '';pr=c._tc.get_or_add_tcPr()
   sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E7EDF0' if i==0 else 'FFFFFF');pr.append(sh)
   bor=OxmlElement('w:tcBorders')
   for side in ['top','left','bottom','right']:
    b=OxmlElement('w:'+side);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'D9D9D9');bor.append(b)
   pr.append(bor)
   for p in c.paragraphs:
    p.paragraph_format.space_after=Pt(4);p.paragraph_format.space_before=Pt(4);p.paragraph_format.line_spacing=1.05
    for r in p.runs:r.font.size=Pt(9);r.bold=i==0
  tr=t.rows[-1]._tr.get_or_add_trPr();tr.append(OxmlElement('w:tblHeader' if i==0 else 'w:cantSplit'))
 doc.add_paragraph().paragraph_format.space_after=Pt(1)
for pi,page_text in enumerate(P):
 lines=page_text.splitlines();h=doc.add_paragraph(lines[0][3:],'Title' if pi==0 else 'Heading 1')
 if pi:h.paragraph_format.page_break_before=True
 else:h.alignment=WD_ALIGN_PARAGRAPH.CENTER
 i=1
 while i<len(lines):
  line=lines[i].strip()
  if not line:i+=1;continue
  if line.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i].strip());i+=1
   table(rows);continue
  m=re.match(r'!\[(.*?)\]\((.*?)\)',line)
  if m:
   f=OUT/m[2]
   with Image.open(f) as im:w,h=im.size
   # Full images are supplied separately for zooming. Reserve room for prose and caption.
   maxh=19 if pi in range(7,13) else 20
   ww=min(16.8,maxh*w/h)
   p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
   p.add_run().add_picture(str(f),width=Cm(ww));p.paragraph_format.keep_with_next=True
  else:
   p=doc.add_paragraph(clean(line),'Caption' if re.match(r'^图\d',line) else 'Normal')
   if re.match(r'^图\d',line):p.alignment=WD_ALIGN_PARAGRAPH.CENTER
  i+=1
doc.core_properties.title='学术成果分享平台需求分析报告'
doc.core_properties.author='第9组 1011101011 A组'
doc.core_properties.subject='第三次作业 业务对象 类图 时序模型 一致性 AI使用'
doc.save(OUT/'01-需求分析报告.docx')
write('提交说明.md','''# 第9组第三次作业

课程：软件系统分析与设计。项目：学术成果分享平台。团队：第9组1011101011 A组。整理日期：2026年11月4日。

优先阅读01-需求分析报告，Word与Markdown同源，PDF用于固定版式阅读。正文按本次五项要求组织。

图件目录保存13张分析模型的PNG与SVG；模型源文件保存Draw.io、模型数据和原始CodeArts采集工程。图件较大时请打开原文件放大，不以报告中的缩略图代替高清图。

支撑材料中包含业务对象字典、对象与SRS对应表、跨模型一致性表、32项设计场景、消息表、前期SRS及用例活动状态图。前期基线按原目录保存，以便相对图片链接正常使用。

汇报材料提供按本次要求调整的图解PPT和逐页演讲稿。AI使用声明单独存放，历史记录保留在支撑材料中。

本次提交范围为需求分析文档与模型。运行测试和性能验证属于后续实现工作。现有记录没有新增成员交叉复审签字，本包如实说明人工反馈和自动检查的范围。
''')
print(json.dumps({'output':str(OUT),'logical_pages':len(P),'classes':len(model['classes']),'figures':len(list((OUT/'图件').glob('*.png')))},ensure_ascii=False))
