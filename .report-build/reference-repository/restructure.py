from pathlib import Path
import re,os,json,shutil,subprocess,hashlib,zipfile,csv,sys
from copy import deepcopy
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK,WD_LINE_SPACING
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT=Path(__file__).resolve().parents[2]
BUILD=Path(__file__).resolve().parent
OUT=ROOT/'Submit'
TAG='9组-1011101011'
VERSION='v2.0'
ARCH=OUT/'归档_历史材料_不放入提交压缩包'/'参考仓库格式重构前_v1.2'
RESUME='--resume-after-package-sources' in sys.argv
if ARCH.exists() and not RESUME:raise SystemExit('Reference restructuring already started; resume only the documented remaining step')
ARCH.mkdir(parents=True,exist_ok=RESUME)
for folder in ([] if RESUME else [ROOT/'docs',OUT/'作业1_需求调研成果',OUT/'作业2_需求建模成果']):
    for p in folder.rglob('*'):
        if p.is_file() and not p.name.startswith('~$'):
            dest=ARCH/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
for f in ([] if RESUME else [OUT/'README.md',OUT/'图文核对与缺图清单.md',ROOT/'README.md']):
    dest=ARCH/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)

old_research=(ROOT/'docs/需求调研报告.md').read_text(encoding='utf-8')
old_srs=(ROOT/'docs/系统需求规格说明书_SRS.md').read_text(encoding='utf-8')
old_spec=(ROOT/'docs/核心模块开发规范_SPEC.md').read_text(encoding='utf-8')
assert not old_srs.startswith('# 文档入口'), 'Cannot rerun after final source redirects'
uc_data=json.loads((BUILD/'usecases.json').read_text(encoding='utf-8'))
cases=uc_data['cases']
current={p.name:p for p in (ROOT/'images').iterdir() if p.suffix in ['.png','.drawio']}
image_inventory={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in current.items()}

def chapter(text,n):
    m=re.search(r'^## '+str(n)+r'(?:\.| ).*?(?=^## \d+(?:\.| )|\Z)',text,re.S|re.M)
    if not m:raise ValueError(('chapter missing',n))
    return m.group(0)
def sub(text,number):
    m=re.search(r'^### '+re.escape(number)+r'\b.*?(?=^### \d|^## |\Z)',text,re.S|re.M)
    if not m:raise ValueError(('subchapter missing',number))
    return m.group(0)
def rename_levels(text,chapter_number):
    return re.sub(r'^(#{2,5}) (\d+)([. ]?)',lambda m:m.group(1)+' '+str(chapter_number)+m.group(3),text,flags=re.M)

def assign(fr):
    prefix=fr.rsplit('-',1)[0];n=int(fr.rsplit('-',1)[1])
    if prefix=='FR-AUTH':return {1:'UC1.1',2:'UC1.2',3:'UC1.2',4:'UC1.3',5:'UC5.2'}[n]
    if prefix=='FR-INST':return 'UC5.2' if n==3 else 'UC1.3'
    if prefix in ['FR-SEARCH','FR-ACCESS']:return 'UC2.1'
    if prefix in ['FR-PAPER','FR-REC']:return 'UC2.3'
    if prefix=='FR-SCHOLAR':return 'UC2.2'
    if prefix=='FR-PORTAL':return {1:'UC2.2',2:'UC3.2',3:'UC3.2',4:'UC5.2',5:'UC3.3',6:'UC3.4',7:'UC3.1',8:'UC5.2',9:'UC2.2',10:'UC3.3',11:'UC3.5',12:'UC3.5',13:'UC3.5'}[n]
    if prefix=='FR-INDEXREQ':return 'UC5.2' if n==3 else 'UC5.4'
    if prefix=='FR-CRAWL':return 'UC5.3' if n in [4,5,6,10] else 'UC5.1'
    if prefix=='FR-SYNC':return 'UC5.1' if n==4 else 'UC5.4'
    if prefix=='FR-ES':return 'UC2.1' if n in [2,3] else 'UC5.4'
    if prefix=='FR-STAT':return {1:'UC4.1',2:'UC4.1',3:'UC4.2',4:'UC4.3',5:'UC4.1',6:'UC4.3',7:'UC4.4',8:'UC3.5',9:'UC5.5',10:'UC5.5'}[n]
    if prefix=='FR-ADMIN':return {1:'UC5.5',2:'UC1.3',3:'UC5.2',4:'UC5.1',5:'UC5.3'}[n]
    if prefix=='FR-OUTCOME':return 'UC2.1' if n==3 else 'UC5.3' if n in [4,5,6,7,8] else 'UC3.2'
    if prefix=='FR-FEEDBACK':return 'UC3.3'
    if prefix=='FR-INNOV':return 'UC4.4'
    if prefix=='FR-TOOLS':return 'UC2.4' if n in [1,6] else 'UC2.5'
    raise ValueError(('unmapped FR',fr))
frs=sorted(set(re.findall(r'\bFR-[A-Z]+-\d{3}\b',old_srs)))
mapping={fr:assign(fr) for fr in frs}
assert len(mapping)==104
for c in cases:c['requirements']=[x for x in frs if mapping[x]==c['id']]

DOC_R=ROOT/'docs/01.需求调研'
DOC_S=ROOT/'docs/02.需求建模'
DOC_R.mkdir(exist_ok=True);DOC_S.mkdir(exist_ok=True)
def local_image(path,name):
    if name not in current:return '缺图：'+name+'（当前 images 未找到）'
    rel=Path(os.path.relpath(current[name],path.parent)).as_posix()
    return f'![{Path(name).stem}]({rel})' if name.endswith('.png') else f'[{name}]({rel})'
def adapt_images(text,dest):
    def change(m):
        t=m.group(2)
        if not re.search(r'\.(png|drawio)$',t,re.I):return m.group(0)
        base=Path(t).name
        if base not in current:raise ValueError((dest,'unknown image',t))
        return m.group(1)+'('+Path(os.path.relpath(current[base],dest.parent)).as_posix()+')'
    return re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',change,text)

research_path=DOC_R/'需求调研报告.md'
research=(BUILD/'research_v2.md').read_text(encoding='utf-8')
research=research.replace('调研方案与执行记录 |','[调研方案与执行记录](调研方案与执行记录.md) |').replace('数据源与竞品调研记录 |','[数据源与竞品调研记录](数据源与竞品调研记录.md) |')
research_path.write_text(research,encoding='utf-8')

record='# 调研方案与执行记录\n\n本附件保存本组已有调研方法、资料范围和任务走查记录。条目来自重构前 v1.2 稿件，保留已执行与待执行的区别；未开展的问卷、访谈和原型测试不填写为已完成。\n\n'
record+=rename_levels(chapter(old_research,1),1)+'\n\n'+rename_levels(chapter(old_research,4),2)
record=re.sub(r'^## 1\..*$', '## 1. 调研目标与方法',record,flags=re.M)
record=re.sub(r'^## 2\..*$', '## 2. 场景走查记录',record,flags=re.M)
record=adapt_images(record,DOC_R/'调研方案与执行记录.md')
# Links to the old SRS/SPEC are redirected to the formal rewritten documents.
record=record.replace('(系统需求规格说明书_SRS.md)','(../02.需求建模/系统需求规格说明书_SRS.md)').replace('(核心模块开发规范_SPEC.md)','(../02.需求建模/核心模块开发规范_SPEC.md)').replace('(整合说明.md)','(../重构说明.md)')
(DOC_R/'调研方案与执行记录.md').write_text(record,encoding='utf-8')
evidence='# 数据源与竞品调研记录\n\n本附件保存已有公开资料比较、来源记录、领域分类、实验限制与调研发现追踪。网页及实验日期沿用原始记录，重构没有重新执行来源实验，也没有将参考仓库的问卷结果并入本组证据。\n\n'
for new,n in enumerate([5,8,9,12],1):evidence+=rename_levels(chapter(old_research,n),new)+'\n\n'
evidence=adapt_images(evidence,DOC_R/'数据源与竞品调研记录.md')
evidence=evidence.replace('(整合说明.md)','(../重构说明.md)').replace('(需求调研报告.md)','(需求调研报告.md)')
evidence=evidence.replace('§8.4','§2.4').replace('§8.5','§2.5').replace('§8.7','§2.7').replace('§1.3','《调研方案与执行记录》§1.3')
evidence=evidence.replace('(../scripts/','(../../scripts/')
(DOC_R/'数据源与竞品调研记录.md').write_text(evidence,encoding='utf-8')

srs_path=DOC_S/'系统需求规格说明书_SRS.md'
srs='''# 系统需求规格说明书

## 1. 引言

### 1.1 项目背景

学术成果检索与分享平台以公开学术资料为基础，组织论文、授权专利、科研项目和学术获奖，提供成果与学者检索、公开门户、身份与认领审核、公共数据治理和基础统计。平台账号、来源学者、门户管理授权和具体成果贡献是不同对象。认领表示平台确认的管理权或贡献关联，不直接判定法律权属。

### 1.2 文档目的

本说明书作为需求建模阶段的沟通与验收依据，通过参与者和用例规约说明系统应完成的用户任务、失败处理及权限边界，补充公共数据规则、非功能目标和设计约束。功能是否实现、参数是否合适、性能是否达到目标，以后续真实实现、测试和团队评审结果为准。

### 1.3 文档结构

第 2 章定义系统参与者，第 3 章按五个用例包组织用户与认证、学术信息、门户管理、科研态势分析以及平台运营，第 4 章规定全局数据规则、状态、质量目标和设计约束。原 FR 编号保留在附录《需求条目与验收场景》中，逐项关联本版 UC1.x 至 UC5.x；SPEC 继续规定实现处理规则。主报告、条目附录和 SPEC 共同组成可追踪的需求基线。

## 2. 系统参与者

- 公众用户：包括匿名访客和普通账户用户，以公开成果、学者查询及统计浏览为主要目标。公开任务不以登录为统一前置条件；私人保存和资料管理需要本人账户。
- 科研人员：通过必要身份审核的注册用户，可以申请门户管理权。已认领门户科研人员还具有指定门户的有效授权，可管理本人附加信息和申请；这个业务身份不另建一个全能账户角色。
- 平台管理员：负责来源、任务、审核、公共资料治理和统计维护。审核权限可以受限；后台角色不自动取得他人的私人笔记或所有私有材料。
- 外部数据源：包括论文接口、开放书目与专利、项目、奖励公告等外部系统。来源访问方式、许可、字段和更新规则须在启用前核验，不把枚举候选来源当作已接入。

## 3. 系统用例模型

### 3.1 总体用例图

当前系统总用例 Draw.io 文件为 academic_platform_usecase.drawio；根目录 images 尚无同名 PNG 预览，本说明书提供源文件链接并使用现有普通用户、科研人员用例图补充角色范围。系统内部执行器、数据库和算法是实现职责，不作为业务使用者；外部数据源是交互对象。

'''
srs+=local_image(srs_path,'academic_platform_usecase.drawio')+'\n\n'
srs+=local_image(srs_path,'普通用户用例图.drawio.png')+'\n\n图 3-1 普通用户用例图\n\n'
srs+=local_image(srs_path,'01_科研人员用例图.drawio.png')+'\n\n图 3-2 科研人员用例图\n\n'
srs+='现有图中的 UC01 至 UC13、UC-AM 和 UC-ST 是各图的局部编号，不直接等同本版五包编号。对应关系见附录；P1、P2 能力出现在角色图中不代表全部成为一期必做。模型按当前 Draw.io 保存，不要求转换为 CodeArts Modeling。\n\n### 3.2 用例规约\n\n'
caption=3
for gid,gname in uc_data['groups']:
    srs+=f'#### 3.2.{gid} 用例包{gid} {gname}\n\n'
    for i,c in enumerate([x for x in cases if x['id'].startswith('UC'+gid+'.')],1):
        srs+=f'##### 3.2.{gid}.{i} {c["id"]} {c["name"]}\n\n'
        srs+='优先级：'+c['priority']+'。关联原需求：'+('、'.join(c['requirements']) if c['requirements'] else '与本包相关条目共同覆盖')+'。\n\n'
        audience='；'.join([c['actors']+'：希望任务结果准确、可解释且可恢复','平台管理与开发团队：需要一致的规则、权限和可追踪处理结果'])
        rows=[['用例名称','',c['id']+' '+c['name']],['简要描述','',c['desc']],['参与者','',c['actors']],['涉众','',audience],['前置条件','',c['pre']],['后置条件','成功',c['success']],['后置条件','失败',c['failure']],['事件流','基本路径','<br>'.join(f'{j}. {v}' for j,v in enumerate(c['steps'],1))],['事件流','备选路径','<br>'.join(c['alt'])]]
        for filename,label in c.get('figures',[]):
            assert filename in current,filename
            content=local_image(srs_path,filename)+f'<br>图 3-{caption} {label} '+Path(filename).stem
            caption+=1
            rows.append([label,'',content])
        srs+='| 项目 | 分类 | 规约内容 |\n| --- | --- | --- |\n'+'\n'.join('| '+' | '.join(v.replace('|','\\|') for v in r)+' |' for r in rows)+'\n\n'

srs+='''## 4. 补充规约

本章规定跨用例的全局要求。四类成果基础流程、公开检索门户、认领治理、基础统计及任务恢复为 P0；私人资料与推荐为 P1；讨论订阅、复杂网络预测和机构 SSO 为 P2。交易、支付及未经授权全文托管不在一期范围。

### 4.1 数据需求与业务规则

#### 4.1.1 公共数据契约

| 编号 | 需求或规则 | 约束与检查依据 |
| --- | --- | --- |
| DR-01 | 稳定业务标识 | 平台账号、学者、机构、成果、来源记录分别保存内部标识；姓名不是唯一键；规范记录保留来源和版本 |
| DR-02 | 四类成果差异 | 论文 DOI 与出版信息；专利申请、公开文献及家族分层；项目保留资助机构和编号；获奖保留奖项、授奖机构及完成人或单位 |
| DR-03 | 人员与机构消歧 | 可信、格式有效、无冲突的 ORCID 或 ROR 可以支持精确关联；姓名、域名或相似关系只形成候选，证据不足人工复核，不授予账户权限 |
| DR-04 | 时间及精度 | 年、月、日及日期含义分别保存；授权年、资助年、立项年、奖励年和公告日不能互换；未知不补成 1 月 1 日 |
| DR-05 | 分类与范围 | 采集范围不等于确认学科；来源主题、平台分类、版本和确认状态分别保存，未知分类单列，多标签按集合去重 |
| DR-06 | 来源与字段状态 | 原值、规范值和人工修订分离；缺失、零值、待核实、不适用不同；保留原始内容、字段依据和模拟标志 |
| BR-01 | 门户及贡献授权 | 一账号最多一个本人门户，一门户最多一个有效管理账号；门户管理权不自动确认所有成果；多人真实贡献可分别确认 |
| BR-02 | 个人维护边界 | 本人标签、说明和顺序可自主维护；公共元数据、归属、作者顺序、机构及合并需要审核；移除本人关系不删除公共成果 |
| BR-03 | 申请及并发 | 同人同对象同类在审申请去重；材料和对象版本校验；通过、授权和审计可靠提交；终态再次申请另建记录 |
| BR-04 | 可见性与私人资料 | 查询和统计固定范围与公开版本，同时校验当前对象权限；认领证明和私人笔记不作为公开字段 |
| BR-05 | 合并与恢复 | 保留来源映射、旧标识、修订及重定向；强标识冲突阻断自动合并，复核及恢复有依据 |
| BR-06 | 四类统计身份 | 论文、项目和获奖按规范成果 ID；基础授权专利按有授权依据的申请实体；公开文献与家族数量另列 |
| BR-07 | 统计解释 | 机构按成果发生时可靠关系全计数，领域允许重叠；引用不跨来源相加，缺失不等于零；当前年注明截至日期 |
| BR-08 | 共著与路径 | 共著仅由共同署名有效论文形成，边权为共同论文去重数；引用不是共著；最短路径不表示合作意愿 |

具体字段、类型关系和模拟校验样例仍在需求条目附录及 SPEC 保存，以本章规则解释，不据当前类图推定已经画出了全部数据库对象。

#### 4.1.2 门户认领六状态

'''
claim=sub(old_srs,'6.8')
claim=claim.split('#### 账号与门户绑定约束')[0]
claim=re.sub(r'^### 6\.8[^\n]*\n','',claim)
srs+=claim+'\n\n#### 4.1.3 采集任务六状态\n\n'
crawl=sub(old_srs,'6.9');crawl=re.sub(r'^### 6\.9[^\n]*\n','',crawl)
srs+=crawl+'\n\n'
srs+='''### 4.2 非功能性需求

| 需求类别 | 需求 ID | 需求描述 | 验收标准 |
| --- | --- | --- | --- |
| 可用性 | USA-01 | 公开任务无需统一登录，查询返回保留上下文 | 匿名完成查询、详情和门户；登录、返回与反馈后条件、排序和页码可恢复 |
| 可解释性 | USA-02 | 结果状态与统计范围明确 | 固定用例分别检查未知、零值、无样本、空结果、处理失败及版本失效，不混淆含义 |
| 性能 | PER-01 | 检索与详情具有可测响应目标 | 至少 10000 条数据、20 并发，预热并固定查询运行至少 5 分钟；检索 P95 不超过 2 秒，详情 P95 不超过 1 秒，记录环境、缓存、参数及失败率 |
| 性能 | PER-02 | 冷启动与扩充规模另行验证 | 冷启动单列记录，基础检索目标 P95 不超过 3 秒；10 万级扩充不能仅据小样本声明达标 |
| 可靠性 | REL-01 | 更新、重试及停止保持数据连续性 | 断点、水位、执行尝试和幂等恢复分别检查；故障和停止不导致旧执行器推进成功水位 |
| 一致性 | REL-02 | 公开版本和实时权限不混用 | 固定范围的查询、明细和统计一致；权限解绑立即生效，索引失败保留恢复入口 |
| 安全性 | SEC-01 | 账户与对象权限有效 | 密码不明文保存；管理员、本人资料和对象操作分别鉴权；越权输入被拒绝并保留必要审计 |
| 安全性 | SEC-02 | 输入与外部访问受控 | 参数、文件类型和大小按配置校验；外部 URL 通过受控采集，不无限制服务器抓取；不公开凭证、完整证明或私人笔记 |
| 数据质量 | DQ-01 | 核心字段完整性和来源可追踪 | 按成果类型和适用字段计算完整率目标至少 95%；公开规范成果来源追踪目标 100%，模拟材料单列 |
| 数据质量 | DQ-02 | 清洗和候选算法经固定样本验证 | 分层人工标注 500 条清洗样本目标至少 99%；启用自动去重时准确率至少 98%，作者自动关联至少 97%，样本不足注明适用范围 |
| 数据质量 | DQ-03 | 精确查询与异常状态可以复核 | 固定合法、缺失、错误和冲突标识查询至少 50 组；存在合法标识命中目标 100%；至少 95% 异常有可查处理状态 |
| 可观测性 | OBS-01 | 处理过程留有可查询记录 | 记录请求错误、采集和 ETL 状态、索引异常、任务耗时与来源失败；受理与解决分别统计 |

以上均为待验证的验收要求，当前调研样本、模型文件和文档重构不能证明系统已经达标。完整原 AC 场景、模拟数据及预期结果在附录保存。

### 4.3 设计约束

- DC-01 实体分离：账号、来源人物、门户授权、具体贡献及机构关系分别建模。类图中的当前任职与成果署名或归属关系分别保存时间和来源。
- DC-02 数据与索引：关系业务数据为权威来源，索引可由其重建，统计保留快照；提交与后续工作可靠登记，公开版本校验后切换。
- DC-03 参数与架构：数据库、搜索引擎、分词、候选阈值、来源适配及更新周期为需要验证的设计决策，遵循 SPEC 与评审记录，不将候选方案写成已实现。
- DC-04 模型与图源：只采用当前 images 中的 PNG 与 Draw.io 文件。缺少统计分析图、模块可编辑图源及其他支撑图时如实标记；不从参考仓库复制模型作为本组成果。
- DC-05 访问与工程证据：来源访问、公开展示和私有材料分别按授权与项目规则处理；核心模块 SPEC、实现对应、真实 AI 使用与人工修正、测试记录在后续交付中保存。原定核心模块覆盖率目标至少 80%，结果以测试报告为准。

本版新用例编号、原 FR 与 AC 条目的对应见《需求条目与验收场景》，不得仅凭编号格式相似将现有图上的局部用例编号改解释为另一项任务。
'''
srs=srs.replace('见 §6.8','见 §4.1.2').replace('见 §6.9','见 §4.1.3').replace('SUCCESS 表示','SUCCEEDED 表示')
srs_path.write_text(srs,encoding='utf-8')

catalog_path=DOC_S/'需求条目与验收场景.md'
catalog='# 需求条目与验收场景\n\n本附件是 v2.0 SRS 的详细条目与验收依据，保留原 104 项 FR 标识和原 AC 编号。条目描述、模拟数据、指标适用范围与待验证状态沿用本组 v1.2 输入；主 SRS 用新的五包 UC 编号组织任务，下面的映射不改变原 FR 或图上的局部编号。\n\n## 1. 新用例与原需求映射\n\n| 原需求编号 | 本版用例 | 用例名称 |\n| --- | --- | --- |\n'
names={c['id']:c['name'] for c in cases}
catalog+='\n'.join(f'| {fr} | {uc} | {names[uc]} |' for fr,uc in mapping.items())+'\n\n'
catalog+='## 2. 功能需求详细条目\n\n'+rename_levels(re.sub(r'^## 4\.[^\n]*\n','',chapter(old_srs,4)),2)+'\n\n'
catalog+='## 3. 数据字段与类型关系\n\n'+rename_levels(re.sub(r'^## 5\.[^\n]*\n','',chapter(old_srs,5)),3)+'\n\n'
catalog+='## 4. 详细业务规则\n\n'+rename_levels(re.sub(r'^## 6\.[^\n]*\n','',chapter(old_srs,6)),4)+'\n\n'
catalog+='## 5. 原验收场景与模拟数据\n\n'+rename_levels(re.sub(r'^## 10\.[^\n]*\n','',chapter(old_srs,10)),5)+'\n\n'
catalog+='## 6. 图中局部用例编号映射\n\n| 当前图编号 | 当前图名称或含义 | 本版用例 |\n| --- | --- | --- |\n'
local_maps=[('UC01','科研人员图 检索与查看成果','UC2.1、UC2.3'),('UC02','科研人员图 查看学者门户','UC2.2'),('UC03','科研人员图 提交门户认领','UC3.1'),('UC04','科研人员图 审核认领申请','UC5.2'),('UC05','科研人员图 维护本人门户与成果','UC3.2、UC3.4'),('UC06','科研人员图 提交数据纠错','UC3.3'),('UC07','科研人员图 查看领域与机构统计','UC4.1、UC4.2、UC4.3'),('UC08','科研人员图 追踪引用与研究资源','UC2.3、UC2.5'),('UC09','科研人员图 管理专题文献与笔记','UC2.5'),('UC10','科研人员图 对比与导出调研材料','UC2.5'),('UC11、UC13','科研人员图 讨论与主题订阅','P2 后续功能，不纳入基础用例承诺'),('UC12','科研人员图 查看专家合作网络','UC4.4'),('UC-AM-01/02/05/11/12','成果管理图 查询认领、补录及校验','UC3.2'),('UC-AM-03/09','成果管理图 本人信息与公共元数据维护','UC3.4、UC5.3'),('UC-AM-04/07','成果管理图 撤销申请与审核','UC3.3、UC5.2'),('UC-AM-06/10','成果管理图 本人申请与审计','UC3.5、UC5.3'),('UC-AM-08','成果管理图 补录纠错审核','UC5.2'),('UC-ST-01/02/06','原统计条目 概览年度与人员统计','UC4.1'),('UC-ST-03/04/05','原统计条目 机构排名热点与网络','UC4.2、UC4.3、UC4.4'),('UC-ST-07/08/09','原统计条目 管理统计质量与更新','UC3.5、UC5.5')]
catalog+='\n'.join('| '+' | '.join(r)+' |' for r in local_maps)+'\n\n统计分析原 PNG 当前缺失，保留原文字条目作为需求依据，不声明该图已交付。\n'
catalog=adapt_images(catalog,catalog_path)
# Old section references refer to the retained v1.2 baseline, now explicitly qualified.
catalog=re.sub(r'(?<!原基线 )§(\d+(?:\.\d+)*)',r'原基线 §\1',catalog)
catalog=catalog.replace('(需求调研报告.md)','(../01.需求调研/需求调研报告.md)').replace('(整合说明.md)','(../重构说明.md)')
catalog_path.write_text(catalog,encoding='utf-8')
assert set(re.findall(r'\bFR-[A-Z]+-\d{3}\b',catalog))>=set(frs)
assert set(re.findall(r'\bAC-[A-Z]+-?\d+\b',catalog))>=set(re.findall(r'\bAC-[A-Z]+-?\d+\b',chapter(old_srs,10)))

spec_path=DOC_S/'核心模块开发规范_SPEC.md'
spec=old_spec.replace('**版本：v1.2｜日期：2026-10-12**','**版本：v2.0｜日期：2026-10-12**')
spec=spec.replace('(需求调研报告.md)','(../01.需求调研/需求调研报告.md)').replace('(整合说明.md)','(../重构说明.md)')
spec=spec.replace('SRS §6.8','SRS §4.1.2').replace('SRS §6.9','SRS §4.1.3').replace('SRS §13.3','SRS §3.2.5.1').replace('SRS §13.4','SRS §3.2.3.1')
spec=spec.replace('SRS §6.2～6.3','SRS §4.1.1').replace('SRS §8.9','SRS §4.2').replace('SRS §8.9/14','SRS §4.2及需求条目附录')
spec=spec.replace('SRS §6.9 与 §13.3','SRS §4.1.3 与 §3.2.5.1').replace('SRS §6.2','SRS §4.1.1').replace('SRS §10.4～10.5','SRS 需求条目附录中的模拟场景')
spec=spec.replace('SRS §8.8','SRS §4.3').replace('SRS §6.9 与 §13.3','SRS §4.1.3 与 §3.2.5.1')
spec=spec.replace('SRS §6.8 的完整模型','SRS §4.1.2 的六状态模型')
spec=spec.replace('与 §13.3','与 §3.2.5.1').replace('SRS §4.2/14','SRS §4.2及需求条目附录')
spec=spec.replace('核心模块开发规范\n','核心模块开发规范\n',1)
spec+='\n\n本版格式按参考仓库的封面、版本历史、目录及正文样式统一；模块内容沿用本组输入，参考仓库未提供独立 SPEC 模板。新用例与 FR 的完整对应见[需求条目与验收场景](需求条目与验收场景.md)。\n'
spec_path.write_text(spec,encoding='utf-8')

# Create two fresh, unambiguous package directories; prior versions are archived when not locked.
A=OUT/'作业1_需求调研成果_v2.0';B=OUT/'作业2_需求建模成果_v2.0'
for p in [A,B]:p.mkdir(exist_ok=RESUME)
for previous in [OUT/'作业1_需求调研成果',OUT/'作业2_需求建模成果']:
    assert previous.resolve().is_relative_to(OUT.resolve())
    if previous.exists():
        dest=OUT/'归档_历史材料_不放入提交压缩包'/'旧提交目录_v1.2'/previous.name
        dest.parent.mkdir(exist_ok=True)
        try:shutil.move(str(previous),str(dest))
        except (PermissionError,OSError):pass
primary_names={'需求调研报告.md':f'01-需求调研报告_v2.0-{TAG}.md','系统需求规格说明书_SRS.md':f'01-SRS_v2.0-{TAG}.md','核心模块开发规范_SPEC.md':f'02-SPEC_v2.0-{TAG}.md','需求条目与验收场景.md':f'01-需求条目与验收场景_v2.0-{TAG}.md','调研方案与执行记录.md':f'01-调研方案与执行记录_v2.0-{TAG}.md','数据源与竞品调研记录.md':f'02-数据源与竞品调研记录_v2.0-{TAG}.md'}
source_list=[research_path,DOC_R/'调研方案与执行记录.md',DOC_R/'数据源与竞品调研记录.md',srs_path,spec_path,catalog_path]
destinations={}
for source in source_list:
    if source.name in ['需求调研报告.md']:dest=A/primary_names[source.name]
    elif source.parent==DOC_R:dest=A/'03-调研材料'/primary_names[source.name]
    elif source.name in ['系统需求规格说明书_SRS.md','核心模块开发规范_SPEC.md']:dest=B/primary_names[source.name]
    else:dest=B/'05-支撑材料'/primary_names[source.name]
    destinations[source.resolve()]=dest
for pkg in [A,B]:
    (pkg/'images').mkdir(exist_ok=RESUME)
    for name,src in current.items():shutil.copyfile(src,pkg/'images'/name)

# Current package sources can reference supporting documents across the two packages;
# copies are added where needed so each zip remains independently usable.
jobs=[]
for source in source_list:
    dest=destinations[source.resolve()];dest.parent.mkdir(parents=True,exist_ok=True)
    pkg=A if dest.is_relative_to(A) else B
    text=source.read_text(encoding='utf-8')
    def fix_link(m):
        target=m.group(2)
        if re.match(r'^(https?://|mailto:|#)',target):return m.group(0)
        resolved=(source.parent/target).resolve()
        if resolved.name in current:target_file=pkg/'images'/resolved.name
        elif resolved in destinations:
            intended=destinations[resolved]
            if intended.is_relative_to(pkg):target_file=intended
            else:
                target_file=pkg/'参考文本'/resolved.name;target_file.parent.mkdir(exist_ok=True)
                # Supporting cross-package references remain textual, and are copied below with rewritten links.
                target_file.write_text(resolved.read_text(encoding='utf-8'),encoding='utf-8')
        elif resolved.is_file():
            target_file=pkg/'参考附件'/resolved.name;target_file.parent.mkdir(exist_ok=True);shutil.copyfile(resolved,target_file)
        else:
            # A2/E1/E2 original files were absent in the input, never manufacture them.
            return m.group(1).strip('![]')+'（原文件待补）'
        return m.group(1)+'('+Path(os.path.relpath(target_file,dest.parent)).as_posix()+')'
    text=re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',fix_link,text)
    dest.write_text(text,encoding='utf-8');jobs.append((dest,dest.with_suffix('.docx')))

# Avoid raw, stale figure paths in the optional copied comparison text.
for pkg in [A,B]:
    for p in (pkg/'参考文本').glob('*.md') if (pkg/'参考文本').exists() else []:
        t=p.read_text(encoding='utf-8')
        def repl(m):
            target=m.group(2)
            if re.match(r'^(https?://|#|mailto:)',target):return m.group(0)
            base=Path(target).name
            if base in current:return m.group(1)+'(../images/'+base+')'
            return m.group(1).strip('![]')+'（详见本包正式正文与来源材料）'
        p.write_text(re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',repl,t),encoding='utf-8')

for pkg,source in [(A,ROOT/'汇报成果/软分展示2.pptx'),(B,ROOT/'汇报成果/软分展示2.pptx')]:
    shutil.copyfile(source,pkg/(f'{2 if pkg==A else 4:02d}-'+('需求调研汇报' if pkg==A else '需求建模汇报')+'-'+TAG+'.pptx'))
models=B/'03-建模图';models.mkdir(exist_ok=RESUME)
(models/'00-模型索引.md').write_text('# 模型索引\n\n所有当前 PNG 和 Draw.io 文件统一保存在本包 images，与根目录同名文件的内容一致。五包用例编号与现有图的局部编号映射见支撑材料中的需求条目与验收场景。模型格式仅要求 Draw.io。缺图仍见本包图文核对与缺图清单。\n',encoding='utf-8')

old_common=ARCH/'Submit/作业1_需求调研成果'
for source_no,title in [(4,'修改说明与版本记录'),(5,'AI使用声明'),(6,'提交材料自查清单')]:
    src=old_common/f'{source_no:02d}-{title}-{TAG}.md'
    body=src.read_text(encoding='utf-8')
    if title=='修改说明与版本记录':
        body+='''\n\n## 参考仓库格式重构记录

| 序号 | 修改项 | 反馈来源 教师或互评 | 修改内容 | 修改人 | 修改日期 | 验证方式 |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 文档写法与目录 | 用户指定参考仓库 | 调研采用六章结构 SRS 采用四章五用例包 104 项 FR 和原 AC 保留在附录 | AI 辅助整理 团队审查人待填 | 2026-10-12 | 参考 PDF 目录与本版章节逐项对照 |
| 11 | Word 格式 | 用户指定参考仓库 | 封面 版本历史 目录 页码 标题和白底黑框表格同步为参考样式 | AI 辅助整理 团队审查人待填 | 2026-10-12 | Word 渲染与参考页面视觉核对 |
| 12 | 提交结构 | 本次重构 | 两份 v2.0 作业目录独立保存正文 源稿 模型 PPT 与通用附件 并重新打包 | AI 辅助整理 团队审查人待填 | 2026-10-12 | 文件清单 链接及压缩包一致性校验 |
'''
    elif title=='AI使用声明':
        body+='\n\n本轮 AI 读取用户指定公开仓库 dev 分支的两份正式 PDF，用于结构和排版对照；将现有调研证据与需求按新目录重写，补足基本和备选路径、后置条件及编号映射。参考问卷统计、原型成果和他组模型未作为本组事实复制。当前 104 项 FR、原 AC 条目、核心 SPEC 及图源保留；团队人工理解与确认仍待完成。\n'
    else:
        body=body.replace('v1.2 图文同步版','v2.0 参考格式重构版')
        body=body.replace('已更新 待人工审查','已重构 待人工审查')
        body+='\n\n本轮新增格式自查：调研六章、SRS 四章五包、用例表字段、封面和版本历史、已更新目录、正文页码、原 FR 和 AC 保留、SPEC 章节引用、新旧用例映射、当前 images 来源及两份 zip 独立可用。参考报告中的问卷和原型工作不列为本组已完成。\n'
    for pkg,n in [(A,source_no),(B,source_no+2)]:
        p=pkg/f'{n:02d}-{title}_v2.0-{TAG}.md';p.write_text(body,encoding='utf-8')
        if pkg==A:jobs.append((p,p.with_suffix('.docx')))

missing=(ARCH/'Submit/图文核对与缺图清单.md').read_text(encoding='utf-8')
missing+='\n\n本轮参考格式重构只改变文档结构、用例写法及 Word 样式。没有从参考仓库复制或生成额外图片，当前缺图状态继续适用；用例表中的图与根目录 images 一一对应。\n'
for pkg in [OUT,A,B]:(pkg/'图文核对与缺图清单.md').write_text(missing,encoding='utf-8')

def font(style,cn,size,bold=False):
    style.font.name='宋体';style.font.size=Pt(size);style.font.bold=bold;style.font.italic=False;style.font.color.rgb=RGBColor(0,0,0)
    rf=style.element.get_or_add_rPr().get_or_add_rFonts();rf.set(qn('w:eastAsia'),cn);rf.set(qn('w:ascii'),'宋体');rf.set(qn('w:hAnsi'),'宋体')
def border_table(t):
    pr=t._tbl.tblPr
    for x in pr.xpath('./w:tblBorders'):pr.remove(x)
    b=OxmlElement('w:tblBorders')
    for side in ['top','bottom','left','right','insideH','insideV']:
        x=OxmlElement('w:'+side);x.set(qn('w:val'),'single');x.set(qn('w:sz'),'4');x.set(qn('w:color'),'000000');b.append(x)
    pr.append(b)
    t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
def page_settings(sec):
    sec.page_width=Cm(21);sec.page_height=Cm(29.7);sec.top_margin=Cm(2.54);sec.bottom_margin=Cm(2.54);sec.left_margin=Cm(2.54);sec.right_margin=Cm(2.54);sec.header_distance=Cm(1.45);sec.footer_distance=Cm(1.65)
def field(p,instruction,text=''):
    r=p.add_run();start=OxmlElement('w:fldChar');start.set(qn('w:fldCharType'),'begin');r._r.append(start)
    code=OxmlElement('w:instrText');code.set(qn('xml:space'),'preserve');code.text=' '+instruction+' ';r._r.append(code)
    sep=OxmlElement('w:fldChar');sep.set(qn('w:fldCharType'),'separate');r._r.append(sep)
    if text:p.add_run(text)
    end=OxmlElement('w:fldChar');end.set(qn('w:fldCharType'),'end');p.add_run()._r.append(end)
def page_number(sec,fmt='decimal',start=1):
    pr=sec._sectPr
    for x in pr.xpath('./w:pgNumType'):pr.remove(x)
    n=OxmlElement('w:pgNumType');n.set(qn('w:fmt'),fmt);n.set(qn('w:start'),str(start));pr.append(n)
    sec.footer.is_linked_to_previous=False;p=sec.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=0;p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;field(p,'PAGE')
    for r in p.runs:r.font.size=Pt(9)
def line_header(sec,label=''):
    sec.header.is_linked_to_previous=False;p=sec.header.paragraphs[0];p.text=label;p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0
    for r in p.runs:r.font.size=Pt(9)
    b=OxmlElement('w:pBdr');bottom=OxmlElement('w:bottom');bottom.set(qn('w:val'),'single');bottom.set(qn('w:sz'),'4');bottom.set(qn('w:color'),'000000');bottom.set(qn('w:space'),'3');b.append(bottom);p._p.get_or_add_pPr().append(b)

reference=Document()
page_settings(reference.sections[0])
font(reference.styles['Normal'],'宋体',10.5)
normal=reference.styles['Normal'].paragraph_format;normal.line_spacing=Pt(15.6);normal.left_indent=Pt(18);normal.right_indent=Pt(18);normal.first_line_indent=Pt(21);normal.space_after=Pt(0)
for label,cn,size,align in [('Title','宋体',24,WD_ALIGN_PARAGRAPH.CENTER),('Heading 1','宋体',16,WD_ALIGN_PARAGRAPH.CENTER),('Heading 2','宋体',14,WD_ALIGN_PARAGRAPH.LEFT),('Heading 3','宋体',12,WD_ALIGN_PARAGRAPH.LEFT),('Heading 4','宋体',10.5,WD_ALIGN_PARAGRAPH.LEFT)]:
    st=reference.styles[label];font(st,cn,size)
    pf=st.paragraph_format;pf.alignment=align;pf.left_indent=0 if label in ['Title','Heading 1'] else Pt(18);pf.right_indent=0;pf.first_line_indent=0;pf.space_before=Pt(12);pf.space_after=Pt(8);pf.keep_with_next=True
for i in range(1,4):
    name='TOC '+str(i)
    if name not in reference.styles:reference.styles.add_style(name,1)
    st=reference.styles[name];font(st,'宋体',10.5)
    st.paragraph_format.left_indent=Pt(18+21*(i-1))
for st in reference.styles:
    if st.type==1 and st.name not in ['Normal','Title','Heading 1','Heading 2','Heading 3','Heading 4']:
        if st.name in ['Body Text','First Paragraph','Compact']:font(st,'宋体',10.5)
    if st.name.startswith('TOC'):
        font(st,'宋体',10.5);st.paragraph_format.first_line_indent=0;st.paragraph_format.right_indent=0;st.paragraph_format.space_after=0;st.paragraph_format.line_spacing=Pt(15.6)
for style in ['Source Code','Caption']:
    if style not in reference.styles:reference.styles.add_style(style,1)
font(reference.styles['Source Code'],'宋体',8)
font(reference.styles['Caption'],'宋体',9)
reference.save(BUILD/'repository-reference.docx')

def style_cells(t,widths=None,repeat=True):
    border_table(t)
    if widths is None:
        widths=[15.9/len(t.columns)]*len(t.columns)
        if len(widths)>=3:
            lens=[max(len(row.cells[i].text) for row in t.rows) for i in range(len(widths))]
            weights=[max(4,min(n,140))**.5 for n in lens];widths=[15.9*w/sum(weights) for w in weights]
    for i,col in enumerate(t.columns):col.width=Cm(widths[i])
    for ri,row in enumerate(t.rows):
        trpr=row._tr.get_or_add_trPr()
        if ri==0 and repeat:trpr.append(OxmlElement('w:tblHeader'))
        for ci,c in enumerate(row.cells):
            c.width=Cm(widths[ci]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr=c._tc.get_or_add_tcPr()
            for x in pr.xpath('./w:shd|./w:tcMar'):pr.remove(x)
            margins=OxmlElement('w:tcMar')
            for side,value in [('left',65),('right',65),('top',20),('bottom',20)]:
                m=OxmlElement('w:'+side);m.set(qn('w:w'),str(value));m.set(qn('w:type'),'dxa');margins.append(m)
            pr.append(margins)
            for p in c.paragraphs:
                pf=p.paragraph_format;pf.left_indent=0;pf.right_indent=0;pf.first_line_indent=0;pf.space_before=0;pf.space_after=0;pf.line_spacing=Pt(14);pf.keep_with_next=False;pf.widow_control=True
                for r in p.runs:
                    r.font.size=Pt(10.5);r.font.name='宋体';r.font.bold=False;r.font.color.rgb=RGBColor(0,0,0);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')

def author(source,dest):
    text=source.read_text(encoding='utf-8');title=text.splitlines()[0].lstrip('# ').strip()
    temp_md=BUILD/('body-'+dest.stem+'.md');temp_md.write_text('\n'.join(text.splitlines()[1:]),encoding='utf-8')
    temp_docx=BUILD/('body-'+dest.name)
    subprocess.run(['pandoc',str(temp_md),'-f','markdown-implicit_figures','-t','docx','--shift-heading-level-by=-1','--reference-doc',str(BUILD/'repository-reference.docx'),'--resource-path',str(source.parent),'-o',str(temp_docx)],cwd=source.parent,check=True)
    d=Document(temp_docx)
    for rel in d.part.rels.values():
        if rel.reltype.endswith('/hyperlink') and rel.is_external and not re.match(r'^(https?://|mailto:|#)',rel.target_ref):
            target=(source.parent/rel.target_ref).resolve()
            if not target.is_file():raise ValueError((source,rel.target_ref))
            rel._target=Path(os.path.relpath(target,dest.parent)).as_posix()
    # Remove the parser-generated header row from use-case specification tables.
    for t in d.tables:
        is_uc=len(t.columns)==3 and t.cell(0,0).text=='项目' and len(t.rows)>1 and t.cell(1,0).text=='用例名称'
        if is_uc:
            t._tbl.remove(t.rows[0]._tr)
            uc_id=t.cell(0,2).text.split()[0]
            uc=next(c for c in cases if c['id']==uc_id)
            t.cell(7,2).text='\n'.join(f'{i}. {step}' for i,step in enumerate(uc['steps'],1))
            t.cell(8,2).text='\n'.join(uc['alt'])
            style_cells(t,[.9,.9,14.1],repeat=False)
            for i,row in enumerate(t.rows):
                if row.cells[0].text not in ['后置条件','事件流']:row.cells[0].merge(row.cells[1])
            for start in [5,7]:
                t.cell(start+1,0).text='';t.cell(start,0).merge(t.cell(start+1,0))
            for row in t.rows:
                for c in row.cells[:2]:
                    for p in c.paragraphs:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                if row._tr.xpath('.//wp:inline'):row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        else:style_cells(t)
    for p in d.paragraphs:
        pf=p.paragraph_format;pf.widow_control=True
        if p.style.name in ['Normal','Body Text','First Paragraph']:
            pf.left_indent=Pt(18);pf.right_indent=Pt(18);pf.first_line_indent=Pt(21);pf.line_spacing=Pt(15.6);pf.space_after=0
        if p.text.startswith(('表 ','图 ')):
            p.style='Caption';pf.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.left_indent=0;pf.right_indent=0;pf.first_line_indent=0
        if p.style.name=='Source Code':pf.line_spacing=Pt(10);pf.first_line_indent=0;pf.left_indent=Pt(18);pf.right_indent=0
    for inline in d._element.body.xpath('.//wp:inline'):
        ext=inline.find(qn('wp:extent'));cx=int(ext.get('cx'));cy=int(ext.get('cy'))
        in_table=bool(inline.xpath('ancestor::w:tc'))
        limit_w=Cm(13.7 if in_table else 15.5);limit_h=Cm(17.8 if in_table else 19.0)
        scale=min(limit_w/cx,limit_h/cy,1)
        ext.set('cx',str(int(cx*scale)));ext.set('cy',str(int(cy*scale)))
        for e in inline.xpath('.//a:xfrm/a:ext'):e.set('cx',str(int(cx*scale)));e.set('cy',str(int(cy*scale)))
    for pe in list(d._element.body.xpath('.//w:p')):
        if pe.xpath('.//wp:inline'):
            p=Paragraph(pe,d._body);pf=p.paragraph_format
            pf.line_spacing=1.0;pf.space_before=Pt(6);pf.space_after=Pt(6)
            pf.left_indent=0;pf.right_indent=0;pf.first_line_indent=0
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            caption_text=''.join(pe.xpath('.//w:t/text()')).strip()
            if caption_text:
                for child in list(pe):
                    if child.tag==qn('w:r') and child.xpath('.//w:t') and not child.xpath('.//wp:inline'):pe.remove(child)
                caption_text=re.sub(r'^(图 \d+-\d+) (活动图|状态图|时序图|类图|用例图) ',r'\1 ',caption_text)
                caption_text=re.sub(r'(?<= )\d{2}_','',caption_text).replace('.drawio','').replace('_',' ')
                cap=OxmlElement('w:p');pe.addnext(cap);cp=Paragraph(cap,d._body);cp.style='Caption';cp.add_run(caption_text)
                cp.alignment=WD_ALIGN_PARAGRAPH.CENTER;cpf=cp.paragraph_format
                cpf.line_spacing=1.0;cpf.space_before=0;cpf.space_after=Pt(4);cpf.first_line_indent=0;cpf.left_indent=0;cpf.right_indent=0
                for r in cp.runs:r.font.size=Pt(9)
            pf.keep_with_next=True

    # Prepend front matter inside the same OPC package, preserving all body image relationships.
    body=d._element.body;original=[e for e in list(body) if e.tag!=qn('w:sectPr')]
    for e in original:body.remove(e)
    sec=d.sections[0];page_settings(sec);sec.different_first_page_header_footer=False
    sec.header.is_linked_to_previous=False;sec.header.paragraphs[0].text='';sec.footer.paragraphs[0].text=''
    if title=='需求调研报告':line_header(sec)
    p=d.add_paragraph('软件系统分析与设计作业');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(36);p.paragraph_format.space_after=Pt(14);p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0
    for r in p.runs:r.font.size=Pt(14);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
    p=d.add_paragraph('学术成果分享平台');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(10);p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0
    for r in p.runs:r.font.size=Pt(26);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
    p=d.add_paragraph(title,'Title');p.paragraph_format.space_before=0;p.paragraph_format.space_after=Pt(26)
    meta=d.add_table(rows=4,cols=2);meta.cell(0,0).merge(meta.cell(0,1)).text='项目组成员信息'
    for row,values in zip(meta.rows[1:],[['小组编号','9组'],['小组名称','1011101011'],['小组联系人','待填写']]):
        for c,v in zip(row.cells,values):c.text=v
    style_cells(meta,[2.5,13.4],repeat=False)
    meta.cell(0,0).width=Cm(15.9)
    meta.cell(0,0).paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
    for row in meta.rows[1:]:row.cells[0].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
    p=d.add_paragraph('2026 年');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(32);p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0
    for r in p.runs:r.font.size=Pt(15)
    d.add_page_break()
    p=d.add_paragraph('版本变更历史');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0;p.paragraph_format.space_after=Pt(8)
    for r in p.runs:r.font.size=Pt(14);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
    history=d.add_table(rows=1,cols=5)
    for c,v in zip(history.rows[0].cells,['版本','提交日期','主要编制人','审核人','版本说明']):c.text=v
    for entry in [['v1.0','20261010','待填写','待填写','已有资料整合稿'],['v1.1','20261010','待填写','待填写','原稿记载的文字整理'],['v1.2','20261012','待填写','待填写','当前 images 图文同步'],['v2.0','20261012','待填写','待填写','按参考仓库重构章节、用例与格式']]:
        row=history.add_row()
        for c,v in zip(row.cells,entry):c.text=v
    for _ in range(2):history.add_row()
    style_cells(history,[1.15,2.45,3.0,2.2,7.1],repeat=True)
    toc_sec=d.add_section(WD_SECTION_START.NEW_PAGE);page_settings(toc_sec);toc_sec.different_first_page_header_footer=False;line_header(toc_sec);page_number(toc_sec,'upperRoman',1)
    p=d.add_paragraph('目录','Heading 1');p.paragraph_format.space_before=0
    # Keep the directory title out of its own automatic outline.
    p.style='Normal';p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0;p.paragraph_format.space_after=Pt(12)
    for r in p.runs:r.font.size=Pt(16);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
    toc=d.add_paragraph();toc.paragraph_format.left_indent=Pt(18);toc.paragraph_format.first_line_indent=0;field(toc,'TOC \\o "1-3" \\h \\z \\u','目录由 Word 更新')
    body_sec=d.add_section(WD_SECTION_START.NEW_PAGE);page_settings(body_sec);body_sec.different_first_page_header_footer=False;line_header(body_sec,'软件系统分析与设计课程：'+title);page_number(body_sec,'decimal',1)
    for e in original:body.insert(len(body)-1,e)
    for st in d.styles:
        if st.name in ['Title','Subtitle'] or st.name.startswith('Heading'):
            for x in st.element.xpath('./w:pPr/w:pBdr'):x.getparent().remove(x)
    for cover_p in d.paragraphs:
        if cover_p._p.xpath('.//w:br[@w:type="page"]'):break
        cover_p.paragraph_format.line_spacing=1.2
    for cover_style in ['Title','Heading 1','Heading 2','Heading 3']:
        d.styles[cover_style].paragraph_format.line_spacing=1.2
    update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');d.settings.element.append(update)
    d.core_properties.author='9组 1011101011';d.core_properties.title=title;d.core_properties.subject='v2.0 参考仓库格式重构';d.core_properties.comments='结构与视觉格式参考用户指定仓库；内容为本组材料，人工签核待完成'
    dest.parent.mkdir(parents=True,exist_ok=True);d.save(dest)
    print('AUTHORED',dest.name,'figures',len(d.inline_shapes))

for source,dest in jobs:author(source,dest)
for n,title in [(4,'修改说明与版本记录'),(5,'AI使用声明'),(6,'提交材料自查清单')]:
    shutil.copyfile(A/f'{n:02d}-{title}_v2.0-{TAG}.docx',B/f'{n+2:02d}-{title}_v2.0-{TAG}.docx')

restruct='''# 参考仓库格式重构说明

本版为 v2.0，组号 9组，团队名 1011101011。用户指定的 Soft-Where-21/BUAA-SSAD-2025-Project-Group1-AcademicPlatform 仓库 dev 分支，提供需求调研报告与 SRS PDF；本轮以其六章调研结构、四章 SRS 与五用例包、用例规约字段以及封面、版本历史、目录和黑框表格样式为参考。

调研内容依据本组公开资料、角色场景和来源记录；未将参考报告的问卷数量、比例或原型成果作为本组事实。SRS 新编号为 UC1.x 至 UC5.x，原 104 项 FR、AC 场景及模拟数据保存在需求条目附录；图中局部编号另给映射。SPEC 沿用本组规则并更新新章节引用，参考仓库没有独立 SPEC 模板。

图只使用当前 images，模型使用 Draw.io。编号 04 六状态认领、SUCCEEDED 采集成功与 STOPPED 重试耗尽规则保留。缺图继续记录，原图没有被更改或用外部图替换。

旧稿及旧 Submit 文件保存在历史归档。两份正式提交目录为作业1_需求调研成果_v2.0和作业2_需求建模成果_v2.0。Markdown 与 Word 同源，自动目录和正文页码在 Word 中更新后复核。团队姓名、人工编制和审核签字、真实调查与实验原件、课堂反馈仍按实际情况补齐。
'''
(ROOT/'docs/重构说明.md').write_text(restruct,encoding='utf-8')
for pkg in [OUT,A,B]:(pkg/'参考格式重构说明.md').write_text(restruct,encoding='utf-8')
(ROOT/'docs/README.md').write_text('# 文档目录\n\n- [需求调研报告](01.需求调研/需求调研报告.md)\n- [调研方案与执行记录](01.需求调研/调研方案与执行记录.md)\n- [数据源与竞品调研记录](01.需求调研/数据源与竞品调研记录.md)\n- [系统需求规格说明书](02.需求建模/系统需求规格说明书_SRS.md)\n- [核心模块开发规范](02.需求建模/核心模块开发规范_SPEC.md)\n- [需求条目与验收场景](02.需求建模/需求条目与验收场景.md)\n- [参考格式重构说明](重构说明.md)\n',encoding='utf-8')
for file,target in [('需求调研报告.md','01.需求调研/需求调研报告.md'),('系统需求规格说明书_SRS.md','02.需求建模/系统需求规格说明书_SRS.md'),('核心模块开发规范_SPEC.md','02.需求建模/核心模块开发规范_SPEC.md'),('整合说明.md','重构说明.md')]:
    (ROOT/'docs'/file).write_text('# 文档入口\n\n正式 v2.0 正文已按参考仓库阶段目录重构，请查看['+Path(target).stem+']('+target+')。旧稿保存在 Submit 历史归档。\n',encoding='utf-8')
(OUT/'README.md').write_text('''# Submit 提交材料说明

组号为 9组，团队名为 1011101011。本次正文为 v2.0，按用户指定仓库的需求调研和需求建模写法与 Word 格式重构。

| 目录或材料 | 用途 |
| --- | --- |
| 作业1_需求调研成果_v2.0 | 六章需求调研报告、PPT、调研方案与执行记录、数据源竞品支撑、通用附件和当前 images |
| 作业2_需求建模成果_v2.0 | 四章五用例包 SRS、SPEC、完整 FR 与 AC 附录、模型、PPT、通用附件和当前 images |
| 两份 9组-1011101011 压缩包 | 分别提交作业1和作业2，包含对应 v2.0 目录内容 |
| 归档_历史材料_不放入提交压缩包 | 原始稿、旧 Submit 及本轮重构前快照 |
| 参考格式重构说明.md | 参考来源、结构与格式对应、新旧编号及保留原则 |
| 图文核对与缺图清单.md | 当前 images 范围与缺图事项 |

Word 采用参考 PDF 的封面、版本历史、目录、页眉页脚、标题和白底黑框表格。问卷发放、原型测试、用户统计和他组模型未当作本组成果复制。SRS 的 FR 和原 AC 条目保存在支撑附录，新 UC 与旧编号有完整映射；SPEC 核心规则保留。

模型采用 Draw.io，不要求转换为 CodeArts。现有综合 PPT 保留，图只引用当前 images；缺图没有生成替代材料。正式目录以 v2.0 后缀为准，若旧文件被 Word 占用仍留在原位置，不作为新压缩包材料。

成员、联系人、人工编制与审核人、真实调查及实验原件、AI 历史使用和课堂反馈仍需按实际情况补齐。课程建议 PPT 10至15页、汇报12分钟问答3分钟；当前16页综合PPT需另行确认课堂展示版本。完成自查后由一名指定负责人分作业提交。本次仅更新本地材料，未向教学平台或教师群提交。
''',encoding='utf-8')
(BUILD/'outputs.json').write_text(json.dumps([str(dest) for _,dest in jobs],ensure_ascii=False,indent=2),encoding='utf-8')
(BUILD/'manifest.json').write_text(json.dumps({'version':VERSION,'groups':uc_data['groups'],'usecase_count':len(cases),'FR_count':len(frs),'packages':[str(A),str(B)],'image_inventory':image_inventory,'formal_sources':[str(p) for p in source_list],'word_sources':[[str(s),str(d)] for s,d in jobs]},ensure_ascii=False,indent=2),encoding='utf-8')
print('READY FOR WORD FIELD UPDATE AND QA',len(jobs),'unique Word documents')
