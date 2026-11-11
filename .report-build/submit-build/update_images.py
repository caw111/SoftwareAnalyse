from pathlib import Path
import re,os,json,shutil,ast,subprocess,hashlib,csv,sys
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

ROOT=Path(__file__).resolve().parents[2]
BUILD=Path(__file__).resolve().parent
OUT=ROOT/'Submit'
IMAGES=ROOT/'images'
A=OUT/'作业1_需求调研成果';B=OUT/'作业2_需求建模成果'
TAG='9组-1011101011'
ARCH=OUT/'归档_历史材料_不放入提交压缩包'/'图文更新前版本_2026-10-12'
resume='--resume' in sys.argv
if ARCH.exists() and not resume:raise SystemExit('Snapshot already exists; use a deliberate follow-up instead of overwriting')
ARCH.mkdir(parents=True,exist_ok=True)
# Snapshot editable text and Word files before updating any content.
for folder in ([] if resume else [ROOT/'docs',ROOT/'scripts',ROOT/'汇报成果',A,B]):
    for p in folder.rglob('*'):
        if p.is_file() and p.suffix in ['.md','.docx'] and not p.name.startswith('~$'):
            dest=ARCH/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)

current={p.name:p for p in IMAGES.iterdir() if p.suffix in ['.png','.drawio']}
assert len(current)>=20
aliases={
 '科研人员用例图.png':'01_科研人员用例图.drawio.png',
 '现状调研活动图.png':'02_现状调研活动图.drawio.png',
 '门户认领活动图.png':'03_门户认领活动图.drawio.png',
 '认领申请状态图.png':'04_认领申请状态图.drawio.png',
 '核心任务类图.png':'05_核心业务类图.drawio.png',
 '核心业务类图.png':'05_核心业务类图.drawio.png',
 '检索请求时序图.png':'06_检索请求时序图.drawio.png',
 '作者检索活动图.png':'作者检索详细活动图.drawio.png',
 '普通用户活动图.png':'普通用户活动图.drawio.png',
 '普通用户用例图.png':'普通用户用例图.drawio.png',
}
for n in range(1,7):
    for name in current:
        if name.startswith(f'{n:02d}_') and name.endswith('.drawio.png'):aliases[name.replace('.drawio.png','.png')]=name

def canonical(target):
    base=Path(target.split('#')[0]).name
    if base in current:return base
    if base in aliases:return aliases[base]
    # The first Submit package prefixed names with a numeric index and team suffix.
    stem=re.sub(r'^\d\d-','',base)
    stem=stem.replace('-'+TAG,'')
    if stem in current:return stem
    if stem in aliases:return aliases[stem]
    return None

# Each independent package carries exact, byte-for-byte copies of the current image directory.
for pkg in [A,B]:
    dst=pkg/'images';dst.mkdir(exist_ok=True)
    for name,src in current.items():shutil.copyfile(src,dst/name)
old=B/'03-建模图'
assert old.resolve().is_relative_to(OUT.resolve())
if not (ARCH/'旧Submit建模图附件').exists():
    shutil.move(str(old),str(ARCH/'旧Submit建模图附件'))
old.mkdir(exist_ok=True)
(old/'00-模型索引.md').write_text('# 模型索引\n\n当前图源和截图统一放在本作业包的 images 目录，与项目根目录 images 的同名文件内容一致。模型使用 Draw.io 可编辑格式，不要求转换为 CodeArts。正式认领模型采用 04_认领申请状态图.drawio 的六状态；旧九状态认领图仅作为参考。缺少的图或可编辑源文件见两份作业包中的图文核对与缺图清单。\n',encoding='utf-8')
for p in list((A/'参考附件').iterdir()):
    if p.suffix in ['.png','.drawio']:
        dst=ARCH/'旧作业1参考图片'/p.name;dst.parent.mkdir(exist_ok=True);shutil.move(str(p),str(dst))

def image_dir(path):
    if path.is_relative_to(A):return A/'images'
    if path.is_relative_to(B):return B/'images'
    return IMAGES
def ref(path,name,alt=None):
    if name not in current:
        return f'缺图：{alt or name}（当前 images 未找到 {name}）'
    target=Path(os.path.relpath(image_dir(path)/name,path.parent)).as_posix()
    return f'![{alt or Path(name).stem}]({target})' if name.endswith('.png') else f'[{alt or name}]({target})'
def graph(path,png,source,caption,description):
    return f'{ref(path,png,caption)}\n\n{ref(path,source,"Draw.io 可编辑源文件")}\n\n{description}\n'

claim_rules='''### 6.8 门户认领生命周期

本节以当前 `04_认领申请状态图.drawio` 和 `03_门户认领活动图.drawio` 为准。`PortalClaim` 使用六个业务状态，校验与人工审核是处理动作，不另设“待验证”“验证中”或“审核中”业务状态。科研人员身份审核与指定门户管理权仍分别校验。

| 状态 | 对应图中名称 | 含义及处理边界 |
| --- | --- | --- |
| DRAFT | 草稿 | 可编辑；提交校验失败仍为草稿，不进入审核 |
| PENDING_REVIEW | 待审核 | 首次提交或补交校验通过；管理员可审核、要求补充或驳回；申请人可撤回 |
| NEED_MORE_INFO | 待补充 | 管理员列明补充项；补交校验失败仍为待补充；可补交或撤回 |
| APPROVED | 已通过 | 审核与唯一绑定均成功，才授予指定门户管理权 |
| REJECTED | 已驳回 | 记录业务理由，本次申请结束 |
| WITHDRAWN | 已撤回 | 申请人在待审核或待补充时撤回，本次申请结束 |

| 当前状态 | 事件及条件 | 目标状态或处理结果 |
| --- | --- | --- |
| DRAFT | 提交且校验通过 | PENDING_REVIEW；保存申请编号及材料版本 |
| DRAFT | 校验失败 | 保持 DRAFT，提示原因，保留原有权限 |
| PENDING_REVIEW | 管理员要求补充 | NEED_MORE_INFO；记录补充要求并通知申请人 |
| NEED_MORE_INFO | 补交且校验通过 | PENDING_REVIEW；保存新的材料版本 |
| NEED_MORE_INFO | 校验失败 | 保持 NEED_MORE_INFO，说明原因 |
| PENDING_REVIEW | 审核及唯一绑定成功 | APPROVED；状态、绑定、授权和审计原子提交 |
| PENDING_REVIEW | 绑定冲突 | 保持 PENDING_REVIEW，记录冲突并复核，保留原有权限 |
| PENDING_REVIEW | 驳回并记录原因 | REJECTED；不授予管理权 |
| PENDING_REVIEW 或 NEED_MORE_INFO | 本人撤回且版本校验成功 | WITHDRAWN；与并发终审最多一个操作成功 |

已通过、已驳回、已撤回均为本次申请的终态。终态再次申请使用新编号并保留历史；草稿放弃仅结束编辑，不增加图中没有的“草稿到已撤回”迁移。审核占用及到期时间作为内部锁记录，领取或释放审核不改变待审核业务状态。材料验证服务异常只记录原因和重试安排，不直接判为身份不合法，也不创建额外业务状态。账号与门户授权唯一性、私有证据访问及多人真实贡献规则继续生效。

'''
crawl_rules='''### 6.9 采集任务 停止与成功水位

本节以当前 `数据采集任务状态机.drawio` 为准，采用 PENDING、RUNNING、SUCCEEDED、FAILED、RETRYING、STOPPED 六个状态。SUCCEEDED 为图中的成功状态；本文不再另用 SUCCESS 表示同一结果。任务执行连接、请求或翻页、解析、清洗、去重、入库和校验，完成后更新成功水位并触发后续 ETL 或索引任务；检索可见性与统计更新另记状态。

| 当前状态 | 图中的触发事件及条件 | 目标状态与处理 |
| --- | --- | --- |
| 创建任务 | 校验任务参数 | PENDING；写入任务记录并等待调度 |
| PENDING | worker 可用且未停止时调度 | RUNNING；记录开始时间并启动心跳 |
| PENDING | 管理员取消 | STOPPED；记录停止原因和审计 |
| RUNNING | 采集完成且校验通过 | SUCCEEDED；可靠保存处理结果后更新增量水位并触发后续工作 |
| RUNNING | 异常、超时或校验失败 | FAILED；记录错误码、信息和日志，保留已提交批次及断点 |
| RUNNING | 管理员强制停止 | 中断执行；在已提交批次与事务边界安全退出后置 STOPPED，释放资源，不推进成功水位 |
| FAILED | retryCount 小于 maxRetry 且未人工停止 | RETRYING；增加重试计数并计算指数退避时间 |
| RETRYING | 退避结束且未停止 | RUNNING；重新调度并从有效断点恢复 |
| RETRYING | 管理员停止 | STOPPED；不再调度 |
| FAILED | 重试耗尽或人工终止 | STOPPED；保留失败历史及停止原因 |

SUCCEEDED 和 STOPPED 结束本次任务，再执行需创建关联旧任务的新任务。成功水位与分页断点分别保存；停止请求不能允许失效执行器继续写入或成功回调。图中的“强制停止”通过受控取消与安全退出实现，不能破坏已提交数据。非重试错误先记 FAILED，再由管理员终止；重试耗尽按图转 STOPPED，不再保持 FAILED 作为最终状态。索引与统计尚未完成时不能声明整个补采申请已经完成。

'''
flow_claim='''### 7.6 身份与门户认领流程

流程对应当前门户认领活动图。科研人员登录并选择待认领门户，提交机构信息和身份证明；平台检查材料、重复申请及绑定状态。校验通过后生成申请编号并进入待审核；校验失败则说明原因并保留原有权限。管理员核对身份与成果关联证据，必要时列明补充要求，转为待补充并通知申请人。补交材料重新校验，有效申请回到待审核。

身份及归属核验通过后再次检查门户绑定条件。条件成立时统一保存审核结果、绑定和管理权限；冲突时保持待审核并提示复核。核验不成立则记录已驳回及原因。最后保存审核日志并通知申请人；撤回和再次申请按 §6.8 的六状态模型处理。

'''

def srs_model_chapter(path):
    parts=['## 13. UML 模型与图文对应\n\n本章只使用当前 images 目录中的图和 Draw.io 源文件。编号 01 至 06 的科研人员系列图、普通用户两图、作者检索图及采集任务图作为本版解释依据。统计分析和成果管理现有 PNG 可展示，但对应可编辑源文件未在 images 中找到，不能声明源文件已经齐全。\n']
    entries=[
      ('13.1 统计分析模块用例图','统计分析模块_UML用例图.png',None,'图中访客或普通用户查询平台、年度、机构、热点与合作网络；已认领门户科研人员查询本人统计，管理员查询质量统计和更新统计快照。参与者继承表示公开能力复用。此图使用 UC-ST-01 至 UC-ST-09，编号对应 §9.1。PNG 在 images 中，原文所称的合并 Draw.io 工程缺失。'),
      ('13.2 成果管理模块用例图','成果管理模块_UML用例图.png',None,'图中 UC-AM-02 包含 UC-AM-11 的认领资格与重复校验，UC-AM-05 包含 UC-AM-12 的补录或纠错信息校验；提交申请与管理员审核分别发起，不能用包含关系表示审核先后。对应 §9.3 的 UC-AM-01 至 UC-AM-12。PNG 在 images 中，合并 Draw.io 源文件缺失。'),
      ('13.3 采集任务状态图','数据采集任务状态机.drawio.png','数据采集任务状态机.drawio','图使用 PENDING、RUNNING、SUCCEEDED、FAILED、RETRYING、STOPPED。运行完成且校验通过进入 SUCCEEDED；异常进入 FAILED；预算内重试经 RETRYING 回 RUNNING；重试耗尽或人工终止进入 STOPPED。准确处理条件见 §6.9。'),
      ('13.4 门户认领申请状态图','04_认领申请状态图.drawio.png','04_认领申请状态图.drawio','本版采用草稿、待审核、待补充、已通过、已驳回、已撤回六状态。初次和补交校验失败分别保持草稿和待补充；绑定冲突保持待审核；审核及唯一绑定成功才通过。已通过、已驳回、已撤回均为终态，准确规则见 §6.8。旧九状态认领图仅为参考附件，不作为本版状态规范。'),
      ('13.5 普通用户用例图','普通用户用例图.drawio.png','普通用户用例图.drawio','图区分公开访问者与已注册普通用户。公开任务包括成果和学者检索、门户及详情、统计和专家网络、公开分享、引用或元数据导出、数据问题提交。筛选排序、同名确认、来源访问、统计口径和支撑明细、共同成果和最短路径按图中的包含或扩展关系连接；私人收藏、检索历史、关注和通知需要个人账号。图中能力的优先级仍按 §11.1，订阅等后续功能不因出现在图上变为全部一期必做。'),
      ('13.6 科研人员用例图','01_科研人员用例图.drawio.png','01_科研人员用例图.drawio','图区分访客、注册科研人员、已认领学者和审核管理员，列出 UC01 至 UC13。公开检索和门户、统计、引用资源、合作网络属于资料使用；门户认领、数据纠错、专题笔记、对比导出、讨论订阅和本人维护具有各自目标。审核管理员承担 UC04。图中的局部 UC01 等编号不是本说明书 UC-AM 或 UC-ST 编号，不能混用；讨论和订阅保留后续优先级。'),
      ('13.7 普通用户活动图','普通用户活动图.drawio.png','普通用户活动图.drawio','活动从访问平台和选择任务开始，分为查成果、找学者、看统计或网络。核对结果后可分享引用导出、登录保存个人资料、提交反馈或结束。继续使用时回到任务选择；个人保存验证登录状态，公开查询与分享不要求为所有访客增加登录前置。'),
      ('13.8 作者检索详细活动图','作者检索详细活动图.drawio.png','作者检索详细活动图.drawio','活动按姓名、机构和领域查找人物候选，确认人物后再查询其成果；条件校验、无结果提示、筛选排序、详情查看和返回上下文按图中的分支执行。姓名文本只召回候选，不直接认定同名人属于同一实体。'),
      ('13.9 研究现状调研活动图','02_现状调研活动图.drawio.png','02_现状调研活动图.drawio','科研人员确定问题、领域与年份，调整查询范围并判断相关性。纳入时收藏并记录原因，排除时保留排除理由；可访问资源核对版本与实验条件，缺失或受限资源记录状态。候选遍历结束后查看统计和文献对比，核对原文并导出清单与阅读记录，平台不替代研究人员形成学术判断。'),
      ('13.10 门户认领审核活动图','03_门户认领活动图.drawio.png','03_门户认领活动图.drawio','图以科研人员、平台、审核管理员三条泳道组织职责，包含初次校验失败、补充材料后重新校验、身份及归属驳回、绑定条件竞争和成功授权路径。绑定竞争保持待审核并保留原有权限；撤回与终态另由 §13.4 状态图解释。流程见 §7.6。'),
      ('13.11 核心业务类图','05_核心业务类图.drawio.png','05_核心业务类图.drawio','账号提交零到多份认领申请，每份申请对应一个学者门户；账号与门户有效管理绑定两端均为 0..1。学者通过成果贡献关系参与学术成果，机构任职关系与成果署名或归属关系分别记录。论文、专利、科研项目和获奖继承抽象学术成果。账号创建专题文献库和阅读笔记，文献库组合收藏记录，成果组合平台保存的研究资源链接。成果与领域为多对多，论文引用是论文间多对多关系。图中没有单独的 SourceRecord 或 CrawlTask 类，数据库及任务契约的相关对象仍为文字设计，不能声称已全部画入本类图。'),
      ('13.12 检索请求时序图','06_检索请求时序图.drawio.png','06_检索请求时序图.drawio','生命线依次为科研人员、检索页面 boundary、检索服务 control、成果索引 entity 和成果数据 entity。服务先校验字段、年份与分页；参数无效返回字段错误并保留输入。有效参数进入过滤评分排序分页，索引返回成果 ID、总数和数据版本，再读取详情、来源及可见状态。零条结果与返回成果使用不同分支；超时返回错误而不冒充空结果。此图未画出具体搜索引擎、数据库或部署架构。'),
    ]
    for title,png,drawio,description in entries:
        if png not in current:
            parts.append('### '+title+'\n\n缺图：当前 images 未找到 '+png+'。本模块功能和用例条目仍见第 9 章，未插入旧版本截图。\n')
            continue
        parts.append('### '+title+'\n\n'+ref(path,png,title)+'\n\n'+(ref(path,drawio,'Draw.io 可编辑源文件')+'\n\n' if drawio else '')+description+'\n')
    parts.append('### 13.13 系统总用例图源文件\n\n'+ref(path,'academic_platform_usecase.drawio','系统总用例 Draw.io 源文件')+'\n\n源图存在，包含访客或普通用户、科研人员、管理员及外部数据源，覆盖检索、门户成果、审核中心、采集管理及统计运行监控。它是系统范围总览，新增四类成果与私人功能的细节由本章角色图及需求正文补充。当前 images 没有同名 PNG 导出预览，本文只提供可编辑源文件链接，不嵌入自行生成的替代图。\n')
    return '\n'.join(parts)+'\n'

missing=[]
missing_names=['总体技术架构图','数据库 ER 图','采集入库处理时序图']
def replace_mermaid(text,path):
    counter=0
    detailed='详细设计与实现方案' in path.name
    supplement='总体方案与需求建模补充' in path.name
    def change(m):
        nonlocal counter
        i=counter;counter+=1
        before=text[:m.start()];heading=next((l for l in reversed(before.splitlines()) if l.startswith('#')),'未命名模型')
        code=m.group(1)
        if detailed:
            if i in [1,2,4]:
                title={1:missing_names[0],2:missing_names[1],4:missing_names[2]}[i]
                missing.append({'file':str(path.relative_to(ROOT)),'section':heading,'figure':title,'status':'images 中无对应 PNG 或 Draw.io 文件'})
                return f'**缺图：{title}。当前 images 没有对应文件，原 Mermaid 草图已保存在图文更新前历史归档中，提交正文不再展示该草图。**\n'
            if i==0:return ref(path,'academic_platform_usecase.drawio','系统总用例 Draw.io 源文件')+'\n\n当前仅有源文件，没有 PNG 预览；本节不再展示与当前源图不同的 Mermaid 总图。\n'
            if i==3:return ref(path,'数据采集任务状态机.drawio.png','采集任务六状态图')+'\n\n'+ref(path,'数据采集任务状态机.drawio','可编辑源文件')
            if i==5:return ref(path,'06_检索请求时序图.drawio.png','检索请求时序图')+'\n\n'+ref(path,'06_检索请求时序图.drawio','可编辑源文件')
            if i==6:return ref(path,'04_认领申请状态图.drawio.png','认领申请六状态图')+'\n\n'+ref(path,'04_认领申请状态图.drawio','可编辑源文件')
        if supplement:
            name='04_认领申请状态图.drawio.png' if i==0 else '数据采集任务状态机.drawio.png'
            return ref(path,name,'当前模型')+'\n\n'+ref(path,name[:-4],'Draw.io 可编辑源文件')
        # Any unmapped sketch must be reported instead of silently rendered as an extra diagram.
        missing.append({'file':str(path.relative_to(ROOT)),'section':heading,'figure':heading.lstrip('# '),'status':'未找到对应 images 文件'})
        return '**缺图：该模型没有对应 images 文件，原草图保存在历史归档。**\n'
    return re.sub(r'```mermaid\s*\n(.*?)```',change,text,flags=re.S)

def consistent_rules(text,path):
    # Current success enum and failure-to-stop semantics are reflected across prose and tables.
    text=re.sub(r'\bSUCCESS\b','SUCCEEDED',text)
    text=text.replace('统一使用 `SUCCEEDED`，协作者图中的 `SUCCEEDED` 仅作为历史同义标记，不新增第二个业务状态。','按当前采集图统一使用 `SUCCEEDED`，不再另设 SUCCESS 作为第二种成功状态。')
    text=text.replace('重试耗尽保持 FAILED，管理员明确放弃才 STOPPED。','重试耗尽或人工终止时转为 STOPPED，并保留原失败记录及停止原因。')
    text=text.replace('重试耗尽保持 FAILED，不再自动调度；管理员明确终止才 STOPPED。','重试耗尽或人工终止时转为 STOPPED，不再自动调度。')
    text=text.replace('达到上限保留失败状态供人工处理。','达到上限转为已停止，并保留失败原因供人工处理。')
    text=text.replace('达到上限保持失败','达到上限转为已停止')
    text=text.replace('审核占用超时回待审','审核占用超时仅释放内部锁，业务状态仍为待审核')
    text=text.replace('草稿、待审核和待补充可撤回','待审核和待补充可撤回；放弃草稿仅结束编辑')
    text=text.replace('申请从草稿提交为待审核，再由管理员开始审核','申请从草稿校验通过进入待审核，管理员在待审核状态中执行审核')
    # Formal SRS chapters are replaced as a unit, avoiding a mix of the old nine-state and new six-state rules.
    if '系统需求规格说明书' in text[:150] and re.search(r'^### 6\.8',text,re.M):
        text=re.sub(r'^### 6\.8.*?(?=^#### 账号与门户绑定约束)',claim_rules,text,flags=re.S|re.M)
        text=re.sub(r'^### 6\.9.*?(?=^### 6\.10)',crawl_rules,text,flags=re.S|re.M)
        text=re.sub(r'^### 7\.6.*?(?=^### 7\.7)',flow_claim,text,flags=re.S|re.M)
        text=re.sub(r'^## 13\..*?(?=^## 14\.)',srs_model_chapter(path),text,flags=re.S|re.M)
        text=text.replace('提交、验证、人工审核、补充材料及终审前撤回','提交校验、待审核处理、补充材料，以及待审核或待补充时撤回')
        text=text.replace('完整认领状态图及状态说明','六状态认领申请图及说明')
        text=text.replace('申请版本、有效绑定，状态、授权和审计','申请版本、有效绑定，状态、授权和审计')
    if '核心模块开发规范' in text[:160]:
        text=re.sub(r'^### 7\.2.*?(?=^### 7\.3)', '''### 7.2 统一状态

门户认领按当前 04_认领申请状态图及 SRS §6.8 使用 DRAFT、PENDING_REVIEW、NEED_MORE_INFO、APPROVED、REJECTED、WITHDRAWN 六状态。DRAFT 首次提交校验通过进入 PENDING_REVIEW，校验失败保持 DRAFT；管理员在 PENDING_REVIEW 中审核，要求补充进入 NEED_MORE_INFO；补交校验通过回 PENDING_REVIEW，失败仍为 NEED_MORE_INFO。绑定冲突保持 PENDING_REVIEW 并保留原有权限。审核及唯一绑定成功进入 APPROVED，驳回进入 REJECTED。仅待审核和待补充可撤回为 WITHDRAWN；草稿放弃不新增状态迁移。

校验和审核不是单独业务状态。验证服务暂不可用保留当前状态并安排重试或人工处理；审核占用仅是内部锁，领取或释放不改变业务状态。三种终态保留历史，再申请使用新编号；通过后的解绑和贡献撤销另走治理。审核、补充、撤回的并发版本最多一个操作成功。

''',text,flags=re.S|re.M)
    if '详细设计与实现方案' in path.name:
        text=re.sub(r'^### 12\.2.*?(?=^### 12\.3)', '''### 12.2 申请状态与允许操作

'''+graph(path,'04_认领申请状态图.drawio.png','04_认领申请状态图.drawio','认领申请状态图','本节与编号 04 图一致，采用六个业务状态。')+'''
| 当前状态 | 谁能操作 | 允许动作 | 禁止或冲突 |
| --- | --- | --- | --- |
| DRAFT 草稿 | 申请人 | 修改或提交 | 校验失败保持草稿，放弃编辑不新增撤回迁移 |
| PENDING_REVIEW 待审核 | 申请人或管理员 | 本人撤回；管理员要求补充、驳回或审核通过 | 绑定冲突保持待审核，保留原有权限 |
| NEED_MORE_INFO 待补充 | 申请人 | 补交、重新提交或撤回 | 补交校验失败仍为待补充，通过才回待审核 |
| APPROVED 已通过 | 查看历史 | 本次申请终结 | 后续撤权不改写旧申请 |
| REJECTED 已驳回 | 申请人 | 查看原因并另建申请 | 不复用旧申请 |
| WITHDRAWN 已撤回 | 申请人 | 查看历史并另建申请 | 不恢复旧流程 |

事件保留前后状态、操作者、时间、理由、材料版本和请求 ID。审核占用作为内部锁，取得或释放锁不新增 REVIEWING 状态；只有当前有效占用者可以提交审核结论。

''',text,flags=re.S|re.M)
        text=text.replace('检查REVIEWING、版本、当前审核人','检查PENDING_REVIEW、版本及当前有效审核占用')
        text=text.replace('claim转PENDING，','claim保持PENDING_REVIEW，')
        text=text.replace('200审核中、version；认领审核员','200待审核、审核占用及version；认领审核员')
        text=text.replace('认领有草稿、待审核、审核中、待补充、通过、驳回、撤回','认领有草稿、待审核、待补充、已通过、已驳回、已撤回六状态；审核在待审核状态中执行')
        text=text.replace('PENDING待审核','PENDING_REVIEW待审核').replace('NEEDS_INFO待补充','NEED_MORE_INFO待补充')
    return text

local_missing=[]
def update_links(text,path):
    def change(m):
        target=m.group(2)
        if re.match(r'^(https?://|#|mailto:)',target):return m.group(0)
        if re.search(r'\.(?:png|drawio|jpg|svg)$',target,re.I):
            name=canonical(target)
            if name:
                p=Path(os.path.relpath(image_dir(path)/name,path.parent)).as_posix()
                return f'{m.group(1)}({p})'
            title=m.group(1).strip('![]')
            local_missing.append({'file':str(path.relative_to(ROOT)),'section':'文件引用','figure':title,'status':'images 缺少 '+Path(target).name})
            return f'缺图：{title}（images 未找到 {Path(target).name}）'
        return m.group(0)
    return re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',change,text)

# Update formal Markdown sources and the current researcher report, retaining older versions in the snapshot.
sources=list((ROOT/'docs').glob('*.md'))+[ROOT/'scripts/科研人员需求分析与需求建模.md']+list((ROOT/'汇报成果').glob('*.md'))
for path in sources:
    text=path.read_text(encoding='utf-8')
    text=consistent_rules(text,path)
    text=replace_mermaid(text,path)
    text=update_links(text,path)
    if path.parent==ROOT/'docs':
        text=text.replace('**版本：v1.1｜日期：2026-10-10**','**版本：v1.2｜日期：2026-10-12**')
        if '本版图文同步说明：' not in text:
            text+='\n\n本版图文同步说明：按 2026 年 10 月 12 日 images 现存文件更新模型和解释；模型可编辑文件采用 Draw.io，未生成额外图片。缺少文件见 Submit 中的图文核对与缺图清单。\n'
        # Existing repository-level links predated the current flat docs layout.
        text=text.replace('(../../images/','(../images/').replace('(../../scripts/','(../scripts/').replace('(../学术成果检索与分享平台_', '(../scripts/学术成果检索与分享平台_')
    path.write_text(text,encoding='utf-8')

# Update all active package Markdown references, including supporting role reports.
for pkg in [A,B]:
    for path in pkg.rglob('*.md'):
        text=path.read_text(encoding='utf-8')
        if path.parent.name=='文本源稿' and path.name.startswith(('01-需求调研报告','02-系统需求规格说明书','03-核心模块开发规范')):
            srcname={'01':'需求调研报告.md','02':'系统需求规格说明书_SRS.md','03':'核心模块开发规范_SPEC.md'}[path.name[:2]]
            # Start from the package copy to preserve its non-image links.
            text=consistent_rules(text,path)
            text=text.replace('**版本：v1.1｜日期：2026-10-10**','**版本：v1.2｜日期：2026-10-12**')
        else:text=consistent_rules(text,path)
        text=replace_mermaid(text,path)
        text=update_links(text,path)
        path.write_text(text,encoding='utf-8')

# Cross-document notices must reflect the user's Drawio-only requirement.
integration='''# 文档整合说明

正文采用 v1.2 图文同步版，日期为 2026 年 10 月 12 日。需求调研、SRS、SPEC 的图示依据为当前项目 images 中的同名 PNG 和 Draw.io 文件，两个作业包均保存同名文件的原样副本。用户明确要求 Draw.io 可编辑文件即可，不要求转换为 CodeArts Modeling。

正式门户认领采用编号 04 的六状态图，验证和审核是处理动作；编号 03 活动图解释校验、补交、驳回和绑定竞争。采集任务使用现有图的 SUCCEEDED 成功状态，重试耗尽按图转 STOPPED。核心类图与检索时序说明按编号 05 和 06 更新，不声称图中画出了未出现的来源记录类或具体数据库。

原版文本、模型与 Mermaid 草图存放于 Submit 根目录历史归档中的图文更新前版本目录。当前提交正文中未匹配 images 的新增草图已撤下并标为缺图，未创建替代图片。统计分析和成果管理的 PNG 存在，但原文提到的合并 Draw.io 工程缺失；其他缺图详见图文核对与缺图清单。

组号为 9组，团队名为 1011101011。课堂反馈、成员分工、真实调查或实验原件、历史 AI 使用和人工验证记录继续按实际情况补充。
'''
for pkg in [A,B]:
    path=pkg/'文本源稿'/f'04-整合说明-{TAG}.md';path.write_text(integration,encoding='utf-8')

check='''# 提交材料自查清单

本表沿用提交要求附录 D 的材料项。本次用户确认模型采用 Draw.io 可编辑文件即可，不要求转换为 CodeArts；现存图源与导出图按 images 核验。

| 序号 | 材料 | 是否完成 | 自查人 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 需求调研报告 Word | 已更新 待人工审查 | 待填 | v1.2 图文同步版 |
| 2 | 需求调研汇报 PPT | 已提供 待确认 | 待填 | 保留现有 16 页综合 PPT 本轮更新文本材料 |
| 3 | 调研材料 | 部分具备 | 待填 | 角色材料图引用已修正 访谈问卷及实验原件仍待补 |
| 4 | 系统需求规格说明书 SRS Word | 已更新 待人工审查 | 待填 | 插图全部来自 images 状态表与所选现有图一致 |
| 5 | 核心模块开发规范 SPEC Word | 已更新 待人工审查 | 待填 | 同步六状态认领 SUCCEEDED 和重试耗尽规则 |
| 6 | 用例图 Draw.io 源文件及导出图 | 部分齐全 | 待填 | 普通用户 科研人员与系统总用例源文件存在 系统总图缺 PNG 统计和成果管理缺可编辑源文件 |
| 7 | 活动图源文件及导出图 | 已找到 | 待填 | 普通用户 作者检索 现状调研 门户认领均有当前 Draw.io 和 PNG |
| 8 | 状态图源文件及导出图 | 已找到 | 待填 | 正式采用编号 04 认领六状态及采集任务六状态 两者均有 Draw.io 和 PNG |
| 9 | 需求建模 PPT 与支撑材料 | 已提供 部分支撑图待补 | 待填 | 详细设计原稿的架构 ER 和采集入库时序没有 images 文件 |
| 10 | 修改说明与版本记录表 | 已追加记录 | 待填 | 本次图文同步已记录 课堂反馈另补 |
| 11 | AI 使用声明 | 已更新 待人工确认 | 待填 | 已写明本次引用核对及规则同步 历史记录仍待补 |

组号为 9组，团队名为 1011101011。缺图见本包图文核对与缺图清单，提交前请完成相关文件补齐与人工审查。
'''
for pkg,n in [(A,6),(B,8)]:
    (pkg/f'{n:02d}-提交材料自查清单-{TAG}.md').write_text(check,encoding='utf-8')
for pkg,n in [(A,4),(B,6)]:
    p=pkg/f'{n:02d}-修改说明与版本记录-{TAG}.md';text=p.read_text(encoding='utf-8')
    text=text.replace('三份 v1.1 稿件','三份 v1.1 稿件及本次 v1.2 图文同步稿')
    text+='''

## 本次图文同步记录

| 序号 | 修改项 | 反馈来源 教师或互评 | 修改内容 | 修改人 | 修改日期 | 验证方式 |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | 模型格式 | 用户明确要求 | Draw.io 可编辑文件即可 删除将 CodeArts 转换列为待办的说明 | AI 辅助整理 人工负责人待填 | 2026-10-12 | 用户指令及文件后缀核对 |
| 7 | 图示来源 | 用户明确要求 | 更新为当前 images 原图 替换旧 scripts 图片及内嵌 Mermaid 草图 修正科研人员角色报告的图链接 | AI 辅助整理 人工负责人待填 | 2026-10-12 | 文件存在与内容哈希核对 |
| 8 | 图文内容一致性 | 用户明确要求 | 正式认领使用编号 04 六状态 采集成功为 SUCCEEDED 耗尽后 STOPPED 同步类图及检索时序的解释 | AI 辅助整理 人工负责人待填 | 2026-10-12 | Draw.io 标签 边与对应 PNG 逐项核对 |
| 9 | 缺图说明 | 本次核对发现 | 列出缺少的架构 ER 采集处理时序 合并模块图源及系统总图 PNG 不伪造文件 | AI 辅助整理 人工负责人待填 | 2026-10-12 | 当前 images 清单对照 |
'''
    p.write_text(text,encoding='utf-8')
for pkg,n in [(A,5),(B,7)]:
    p=pkg/f'{n:02d}-AI使用声明-{TAG}.md';text=p.read_text(encoding='utf-8')
    text=text.replace('从 SRS 提取的 Mermaid 源文本沿用原稿。','本轮按用户要求核对当前 images 并更新插图和模型解释，原 Mermaid 草图保存在历史归档。')
    text=text.replace('未替团队确认模型已符合 CodeArts 要求','未生成模型图或伪造可编辑源文件，模型按用户要求使用 Draw.io')
    text=text.replace('从 SRS 提取的 Mermaid 源文本沿用原稿','本轮插图来自当前 images')
    p.write_text(text,encoding='utf-8')

# Correct other package guidance that previously required a conversion the user declined.
for pkg in [A,B]:
    for p in pkg.rglob('*.md'):
        if p.name.startswith(('04-整合说明','06-提交材料自查清单','08-提交材料自查清单')):continue
        text=p.read_text(encoding='utf-8')
        text=text.replace('标明待补 CodeArts 工程','标明可编辑图源和截图是否齐全')
        text=text.replace('尚无 CodeArts 工程','采用 Draw.io 可编辑文件')
        text=text.replace('CodeArts 中核对并导出','Draw.io 中核对并导出')
        p.write_text(text,encoding='utf-8')

# Research excerpts are regenerated from their updated package source.
p=A/'03-调研材料'/f'06-调研支撑材料摘编-{TAG}.md'
full=(A/'文本源稿'/f'01-需求调研报告-{TAG}.md').read_text(encoding='utf-8')
parts=re.split(r'(?=^## )',full,flags=re.M)
excerpt='# 调研支撑材料摘编\n\n本材料摘录 v1.2 调研报告的方法、三类角色、平台比较、数据来源和资料索引。模型引用使用当前 images，不新增访谈或实验原件。\n\n'+'\n\n'.join(s for s in parts if re.match(r'## (1\.|3\.|5\.|8\.|12\.)',s))
def excerptlink(m):
    t=m.group(2)
    if re.match(r'^(https?://|#)',t):return m.group(0)
    absolute=((A/'文本源稿')/t).resolve()
    return f'{m.group(1)}({Path(os.path.relpath(absolute,p.parent)).as_posix()})'
excerpt=re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',excerptlink,excerpt)
p.write_text(excerpt,encoding='utf-8')

# Add the requested missing-figure report rather than manufacturing extra figures.
missing+=local_missing
report='''# 图文核对与缺图清单

核对范围为 docs 正式稿与 Submit 两份作业包中的 Markdown、Word 文本和图引用。依据为 2026 年 10 月 12 日当前根目录 images；历史归档和 PPT 不作为本轮更新正文。已替换旧图片路径、Word 旧内嵌图和能对应现有文件的 Mermaid 草图。未匹配的草图从提交正文撤下，原稿保存在图文更新前历史归档。

## 缺少的图

| 图名 | 原出现位置 | 当前缺少文件 |
| --- | --- | --- |
| 总体技术架构图 | 详细设计与实现方案 §4.1 | images 中没有对应 PNG 或 Draw.io |
| 数据库 ER 图 | 详细设计与实现方案 §5.1 | images 中没有对应 PNG 或 Draw.io 核心业务类图不能替代数据库 ER 图 |
| 采集入库处理时序图 | 详细设计与实现方案 §6.6 | images 中没有对应 PNG 或 Draw.io 现有检索请求时序图只描述查询 |

## 图存在但附件格式缺失

| 材料 | 已有文件 | 缺少文件 |
| --- | --- | --- |
| 统计分析与成果管理模块图 | 成果管理模块_UML用例图.png | 当前统计分析模块_UML用例图.png 缺失 原文引用的 学术成果平台_统计分析与成果管理_UML用例图.drawio 及两张模块图的独立可编辑源文件也未找到 |
| 系统总用例图 | academic_platform_usecase.drawio | academic_platform_usecase.drawio.png 等导出预览未找到 正文提供源文件链接 |

## 当前采用的模型

门户认领正式采用 04_认领申请状态图.drawio 及对应 PNG：草稿、待审核、待补充、已通过、已驳回、已撤回六状态。校验失败维持原状态；绑定冲突保持待审核；已通过需同时完成审核和唯一绑定。旧 认领状态图.drawio 的九状态模型保留为参考，不混入正式业务状态。

采集任务按 数据采集任务状态机.drawio 使用 SUCCEEDED 作为成功状态，重试耗尽或人工终止进入 STOPPED。类图解释以 05_核心业务类图.drawio 的当前关联、多重性、四类成果继承和论文引用关系为准。检索时序以 06_检索请求时序图.drawio 的五条生命线及参数错误、空结果、正常结果分支为准。

所有正文实际插图均引用当前 images 同名 PNG，两个作业包中保存其原样副本。可编辑文件只要求 Draw.io，不要求转换为 CodeArts。本次不修改 images 中的图本身；各模型未画出的实现细节不能说成现有图已覆盖。
'''
if local_missing:
    report+='\n## 其他未匹配的图引用\n\n'
    for row in local_missing:report+=f'- {row["file"]}：{row["figure"]}；{row["status"]}。\n'
for pkg in [OUT,A,B]:(pkg/'图文核对与缺图清单.md').write_text(report,encoding='utf-8')
readme=(OUT/'README.md').read_text(encoding='utf-8')
readme=readme.replace('三份 v1.1 正文','三份 v1.2 图文同步正文')
readme=re.sub(r'现有模型为 Drawio、PNG.*?各自查清单如实保留.*?状态。','当前模型统一使用 images 中的 PNG 与 Draw.io 原样副本，不要求转换为 CodeArts。状态表、核心类图和检索时序说明已经同步；缺少的图或图源见[图文核对与缺图清单](图文核对与缺图清单.md)。真实访谈、实验原件、课堂反馈和人工确认记录仍待补。',readme,flags=re.S)
readme+='\n\n本轮同步了 docs 正式稿和 Submit 的文本、Word 与附件。两份作业包均含 images 副本；出现的插图都可在项目根目录 images 中找到。缺图仅作说明，没有新增替代图。\n'
(OUT/'README.md').write_text(readme,encoding='utf-8')

# Reuse the existing A4 formatter without executing the old package builder.
tree=ast.parse((BUILD/'build_submit.py').read_text(encoding='utf-8'))
fmt=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='format_doc')
exec(compile(ast.Module(body=[fmt],type_ignores=[]),'existing_formatter','exec'),globals())
jobs=[]
for source in json.loads((BUILD/'docx_outputs.json').read_text(encoding='utf-8')):
    dest=Path(source)
    if dest.name.startswith('01-SRS'):md=B/'文本源稿'/f'02-系统需求规格说明书_SRS-{TAG}.md'
    elif dest.name.startswith('02-SPEC'):md=B/'文本源稿'/f'03-核心模块开发规范_SPEC-{TAG}.md'
    elif dest.name.startswith('01-需求调研报告'):md=A/'文本源稿'/f'01-需求调研报告-{TAG}.md'
    else:md=dest.with_name(dest.name.replace('_图文更新版','')).with_suffix('.md')
    jobs.append((md,dest))
for md,dest in jobs:
    text=md.read_text(encoding='utf-8');title=text.splitlines()[0].lstrip('# ').strip()
    draft=BUILD/('updated-'+dest.stem+'.md');draft.write_text('\n'.join(text.splitlines()[1:]),encoding='utf-8')
    temporary=BUILD/('updated-'+dest.name)
    subprocess.run(['pandoc',str(draft),'-f','markdown','-t','docx','--metadata','title='+title,'--resource-path',str(md.parent),'--reference-doc',str(BUILD/'reference.docx'),'-o',str(temporary)],cwd=md.parent,check=True)
    format_doc(temporary)
    d=Document(temporary)
    for rel in d.part.rels.values():
        if rel.reltype.endswith('/hyperlink') and rel.is_external and not re.match(r'^(https?://|mailto:|#)',rel.target_ref):
            target=(md.parent/rel.target_ref).resolve()
            if not target.is_file():raise ValueError((md,rel.target_ref,target))
            rel._target=Path(os.path.relpath(target,dest.parent)).as_posix()
    for style in d.styles:
        if style.name in ['Title','Subtitle'] or style.name.startswith('Heading'):
            style.font.italic=False
            for e in style.element.xpath('./w:pPr/w:pBdr'):e.getparent().remove(e)
    for t in d.tables:
        for row in list(t.rows)[1:]:
            if not any(c.text.strip() for c in row.cells):t._tbl.remove(row._tr)
        for c in t.rows[0].cells:
            for p in c.paragraphs:p.paragraph_format.keep_with_next=True
    for i,p in enumerate(d.paragraphs):
        if p._p.xpath('.//wp:inline'):
            p.paragraph_format.keep_with_next=True
            if i+1<len(d.paragraphs) and d.paragraphs[i+1].text:d.paragraphs[i+1].paragraph_format.keep_with_next=True
    d.core_properties.author='9组 1011101011';d.core_properties.comments='v1.2 图文同步 当前 images 为依据'
    d.save(temporary)
    try:shutil.copyfile(temporary,dest)
    except PermissionError:
        superseded.append(str(dest))
        dest=dest.with_name(dest.name.replace('-'+TAG+'.docx','_图文更新版-'+TAG+'.docx'))
        shutil.copyfile(temporary,dest)
        print('OPEN WORD FILE RETAINED; NEW COPY',dest.name)
    actual_outputs.append(str(dest))
    print('UPDATED WORD',dest.name,'figures',len(d.inline_shapes))
for n1,n2,title in [(4,6,'修改说明与版本记录'),(5,7,'AI使用声明'),(6,8,'提交材料自查清单')]:
    shutil.copyfile(A/f'{n1:02d}-{title}-{TAG}.docx',B/f'{n2:02d}-{title}-{TAG}.docx')
(BUILD/'docx_outputs.json').write_text(json.dumps(actual_outputs,ensure_ascii=False,indent=2),encoding='utf-8')
(BUILD/'superseded_word_outputs.json').write_text(json.dumps(superseded,ensure_ascii=False,indent=2),encoding='utf-8')

# Verify every Word picture and every active image link against the original images bytes.
hashes={hashlib.sha256(p.read_bytes()).hexdigest():p.name for p in current.values() if p.suffix=='.png'}
count=0;references=[]
for pkg in [A,B]:
    for md in pkg.rglob('*.md'):
        for m in re.finditer(r'(!?\[[^\]]*\])\(([^)]+)\)',md.read_text(encoding='utf-8')):
            target=m.group(2)
            if not re.search(r'\.(?:png|drawio|jpg|svg)$',target,re.I):continue
            resolved=(md.parent/target).resolve();assert resolved.is_file(),(md,target)
            assert resolved.name in current and resolved.read_bytes()==current[resolved.name].read_bytes(),(md,target)
            count+=1;references.append({'document':str(md.relative_to(OUT)),'image':resolved.name,'source':str(current[resolved.name].relative_to(ROOT))})
    for doc in pkg.rglob('*.docx'):
        if doc.name.startswith('~$') or str(doc) in superseded:continue
        d=Document(doc)
        for rel in d.part.rels.values():
            if rel.reltype.endswith('/image'):
                h=hashlib.sha256(rel.target_part.blob).hexdigest();assert h in hashes,(doc,h)
                references.append({'document':str(doc.relative_to(OUT)),'image':hashes[h],'source':'images/'+hashes[h]})
                count+=1
with (OUT/'图文引用核对.csv').open('w',encoding='utf-8-sig',newline='') as fp:
    w=csv.DictWriter(fp,fieldnames=['document','image','source']);w.writeheader();w.writerows(references)
(BUILD/'image_verification.json').write_text(json.dumps({'current_image_files':len(current),'matched_references':count,'missing_models':missing,'all_embedded_word_images_match_current_images':True},ensure_ascii=False,indent=2),encoding='utf-8')
print('VERIFIED IMAGE REFERENCES',count)
