from pathlib import Path
import re, shutil, zipfile
from docx import Document
from PIL import Image
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

root = Path.cwd()
src = root / '.report-build' / 'seminar' / 'report.md'
out = root / '汇报成果' / '需求实践与分析成果研讨'
out.mkdir(parents=True, exist_ok=True)
fig_src = root / '需求分析' / 'A组-需求分析整合版-v1.1' / '图件'
figs = ['03b-停止重试子交互.png', '05a-认领原子授权与撤回子交互.png', '06a-检索权限计数与分页子交互.png', '02-核心业务类图.png']
fig_dir = out / '图件'
fig_dir.mkdir(exist_ok=True)
for name in figs:
    shutil.copy2(fig_src / name, fig_dir / name)
model_names = [
    '01_科研人员用例图.drawio', '01_科研人员用例图.drawio.png',
    '普通用户用例图.drawio', '普通用户用例图.drawio.png',
    '普通用户活动图.drawio', '普通用户活动图.drawio.png',
    '作者检索详细活动图.drawio', '作者检索详细活动图.drawio.png',
    '03_门户认领活动图.drawio', '03_门户认领活动图.drawio.png',
    '04_认领申请状态图.drawio', '04_认领申请状态图.drawio.png',
    '数据采集任务状态机.drawio', '数据采集任务状态机.drawio.png',
]
model_dir = fig_dir / '需求建模模型'
model_dir.mkdir(exist_ok=True)
for name in model_names:
    shutil.copy2(root / 'images' / name, model_dir / name)

report = src.read_text(encoding='utf-8')
# Ensure the submitted markdown resolves to bundled images.
report = report.replace('<!-- page -->', '')
(out / '01-研讨报告.md').write_text(report, encoding='utf-8')

navy = '164E63'
teal = '0E7490'
light = 'EAF3F6'
gray = 'D9E2E8'

def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), fill); tcPr.append(shd)
def set_cell_margins(cell, top=100, start=110, bottom=100, end=110):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr(); mar = OxmlElement('w:tcMar')
    for k,v in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        el=OxmlElement('w:'+k); el.set(qn('w:w'),str(v)); el.set(qn('w:type'),'dxa'); mar.append(el)
    tcPr.append(mar)
def set_repeat_table_header(row):
    trPr=row._tr.get_or_add_trPr(); el=OxmlElement('w:tblHeader'); el.set(qn('w:val'),'true'); trPr.append(el)
def set_borders(table):
    tblPr=table._tbl.tblPr; borders=OxmlElement('w:tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):
        e=OxmlElement('w:'+edge); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),gray); borders.append(e)
    tblPr.append(borders)
def clean_inline(s):
    return re.sub(r'\*\*(.*?)\*\*', r'\1', s).replace('`','')
def style_run(run, size=10.5, color='243746', bold=False):
    run.font.name='Microsoft YaHei'; run._element.rPr.rFonts.set(qn('w:eastAsia'),'Microsoft YaHei'); run.font.size=Pt(size); run.font.color.rgb=RGBColor.from_string(color); run.bold=bold

doc=Document()
sec=doc.sections[0]
sec.top_margin=Inches(.72); sec.bottom_margin=Inches(.72); sec.left_margin=Inches(.78); sec.right_margin=Inches(.78)
styles=doc.styles
for stylename in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3']:
    st=styles[stylename]; st.font.name='Microsoft YaHei'; st._element.rPr.rFonts.set(qn('w:eastAsia'),'Microsoft YaHei')
styles['Normal'].font.size=Pt(10.5); styles['Normal'].font.color.rgb=RGBColor.from_string('243746')
styles['Normal'].paragraph_format.space_after=Pt(6); styles['Normal'].paragraph_format.line_spacing=1.15
styles['Title'].font.size=Pt(24); styles['Title'].font.bold=True; styles['Title'].font.color.rgb=RGBColor.from_string(navy)
styles['Heading 1'].font.size=Pt(16); styles['Heading 1'].font.bold=True; styles['Heading 1'].font.color.rgb=RGBColor.from_string(navy)
styles['Heading 1'].paragraph_format.space_before=Pt(10); styles['Heading 1'].paragraph_format.space_after=Pt(8)
styles['Heading 2'].font.size=Pt(12); styles['Heading 2'].font.bold=True; styles['Heading 2'].font.color.rgb=RGBColor.from_string(teal)
styles['Heading 2'].paragraph_format.space_before=Pt(9); styles['Heading 2'].paragraph_format.space_after=Pt(4)
# Header and page number
header=sec.header.paragraphs[0]; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=header.add_run('学术成果分享平台｜需求实践与分析成果研讨'); style_run(r,8,'657985')
footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=footer.add_run('第 '); style_run(r,8,'657985')
fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); footer._p.append(fld)
r=footer.add_run(' 页'); style_run(r,8,'657985')

lines=report.splitlines(); i=0; first_title=True; in_code=False
while i < len(lines):
    line=lines[i].rstrip(); s=line.strip()
    if not s: i+=1; continue
    if s=='<!-- page -->':
        i+=1; continue
    if s.startswith('```'):
        in_code=not in_code
        if in_code:
            p=doc.add_paragraph(); p.paragraph_format.left_indent=Inches(.2); p.paragraph_format.space_after=Pt(2)
            p.paragraph_format.keep_together=True
        i+=1; continue
    if in_code:
        # Render the conceptual graph as readable relationships rather than raw Mermaid syntax.
        if s.lower().startswith('flowchart') or s in ('```',''): i+=1; continue
        if '-->' in s:
            a,b=s.split('-->',1); a=re.sub(r'\[[^]]*\]|\([^)]*\)','',a).strip(); b=re.sub(r'\[[^]]*\]|\([^)]*\)','',b).strip()
            p=doc.add_paragraph(style='Normal'); p.paragraph_format.left_indent=Inches(.28); p.paragraph_format.space_after=Pt(2)
            rr=p.add_run('• '+a+'  →  '+b); style_run(rr,9.3,teal)
        i+=1; continue
    if s.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            row=[clean_inline(x.strip()) for x in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-{3,}:?',x or '-') for x in row): rows.append(row)
            i+=1
        if not rows: continue
        n=max(len(r) for r in rows); t=doc.add_table(rows=0, cols=n); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=True; set_borders(t)
        for ri,rowdata in enumerate(rows):
            cells=t.add_row().cells
            for ci in range(n):
                cell=cells[ci]; cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; set_cell_margins(cell)
                val=rowdata[ci] if ci<len(rowdata) else ''
                p=cell.paragraphs[0]; p.paragraph_format.space_after=Pt(1); p.paragraph_format.line_spacing=1.05
                rr=p.add_run(val); style_run(rr,8.6 if n>=4 else 9, 'FFFFFF' if ri==0 else '243746', ri==0)
                if ri==0: set_cell_shading(cell,navy)
                elif ri%2==0: set_cell_shading(cell,'F4F8FA')
            if ri==0: set_repeat_table_header(t.rows[0])
        doc.add_paragraph().paragraph_format.space_after=Pt(2)
        continue
    im=re.match(r'!\[(.*?)\]\((.*?)\)',s)
    if im:
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        path=out / Path(im.group(2))
        if path.exists():
            with Image.open(path) as picture:
                w,h=picture.size
            scale=min(6.35/w, 5.6/h)
            p.add_run().add_picture(str(path), width=Inches(w*scale), height=Inches(h*scale))
        i+=1; continue
    if s.startswith('# '):
        title=clean_inline(s[2:]); p=doc.add_paragraph(style='Title' if first_title else 'Heading 1'); p.add_run(title); first_title=False; i+=1; continue
    if s.startswith('## '):
        p=doc.add_paragraph(style='Heading 1'); p.add_run(clean_inline(s[3:])); p.paragraph_format.keep_with_next=True
        if s[3:].startswith('附录'): p.paragraph_format.page_break_before=True
        i+=1; continue
    if s.startswith('### '):
        p=doc.add_paragraph(style='Heading 2'); p.add_run(clean_inline(s[4:])); i+=1; continue
    if s.startswith('图') and '　' in s:
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(8)
        rr=p.add_run(clean_inline(s)); style_run(rr,9,'657985'); i+=1; continue
    if re.match(r'^\d+\.\s',s):
        p=doc.add_paragraph(style='List Number'); p.paragraph_format.left_indent=Inches(.25); rr=p.add_run(clean_inline(re.sub(r'^\d+\.\s*','',s))); style_run(rr); i+=1; continue
    if s.startswith('- '):
        p=doc.add_paragraph(style='List Bullet'); rr=p.add_run(clean_inline(s[2:])); style_run(rr); i+=1; continue
    p=doc.add_paragraph(); rr=p.add_run(clean_inline(s)); style_run(rr); i+=1

# Cover metadata accent
if doc.paragraphs:
    for p in doc.paragraphs[:2]:
        if p.style.name=='Title': p.alignment=WD_ALIGN_PARAGRAPH.LEFT

docx=out/'01-研讨报告.docx'; doc.save(docx)

notes='''# 02 课堂发言提纲\n\n## 开场\n\n我们这次讨论的重点，是检查已有需求成果能不能支撑下一步架构设计。我们已经有需求调研、SRS、核心业务类图，以及采集、认领、检索三条主流程和异常子流程。它们能解释主要业务规则，但设计模型并不等于系统已经实现，更不等于性能和可靠性已经通过测试。\n\n## 调研成果与业务对象\n\n调研材料来自公开资料研究、角色任务分析和场景推演，没有真实访谈或问卷。因此我们用场景来说明同名作者、来源重复和成果字段差异，不把它们包装成用户调查结论。业务对象的划分也有具体原因：认领需要区分账号、学者、申请和门户授权；成果贡献与机构要分开，才能支持历史署名查询；采集需要保留来源记录、观测、任务和更新记录，才能追踪失败及恢复。28个类、45条关系描述的是领域边界，不是数据库表数或微服务数。\n\n## 采集恢复\n\n我们用固定时间范围的三页任务讨论：第一页已经提交，第二页失败，第三页还没有获取。失败后保留已提交的数据，不能推进完整成功水位。这里还要区分“第二页事务没有提交”和“原文已保存、清洗未完成”：前一种需要重取该页，后一种要从积压的处理工作恢复。若仅保存一个下一页游标，就可能漏掉已经取回但尚未处理的数据。\n\n架构上要先证明处理任务可靠登记、恢复扫描可重入、幂等写入有效，再考虑增加队列或并发数。当前有时序设计，没有故障注入运行结果。\n\n## 认领与并发\n\n第二个案例是管理员批准和申请人撤回同时发生。申请版本检查可以拒绝旧版本请求，但还不够：不同申请也可能争抢同一账号或门户。因此需要版本条件更新，以及两侧的有效授权唯一性保护。批准时，申请状态、门户授权、审核决定和必要审计要作为一个业务提交。通知可以在提交后补发。这样能避免页面显示批准、授权却没有建立的部分结果。\n\n## 检索一致性\n\n第三个案例是作者与机构必须来自同一条贡献关系。如果把作者列表和机构列表分别摊平再求交，就可能把不同作者的机构关系拼成错误答案。检索还要固定公开数据版本，使列表、详情和统计看同一版；访问资格则按当前权限判断。若返回前权限刚好被撤销，要让旧结果和旧计数一起失效。\n\n这两类版本分别控制数据内容和授权资格。缓存必须同时考虑查询条件、公开版本和权限范围，并在返回前复验。索引能否表达这些条件仍需用固定样例做原型验证。\n\n## 质量要求与架构候选\n\nSRS已有可测目标：一万条数据、二十并发、预热运行五分钟，检索P95不超过两秒、详情不超过一秒。数据质量目标也分别定义了字段完整率、来源追踪、清洗样本、去重和作者关联准确率。我们要按各自口径测量，不能合成一个泛化准确率。\n\n基于目前的事务和一致性约束，建议先用模块化单体加独立后台执行器做原型：认领事务集中处理，采集不占用公开请求资源，索引和通知可异步更新。它只是候选，不是已拍板的最终架构。我们还没有部署预算、机器规格和运维条件，不能先宣称多机容灾或服务拆分收益。\n\n## 研讨结论与待办\n\n下一步优先验证三件事：采集在不同提交位置故障后是否能无丢失地恢复；并发批准、撤回是否只产生一个合法结果；检索能否保持同贡献、同公开版本和实时权限语义。验证结果要保留环境、输入、预期、实际输出和日志。随后再补性能测试环境、恢复时长和公开更新时延目标。\n\n我们今天交付的是有依据的需求与分析成果研讨稿，以及进入架构设计前的候选和风险清单。真实会议决定和运行测试结果需要由小组后续补录。\n'''
(out/'02-课堂发言提纲.md').write_text(notes,encoding='utf-8')

record='''# 03 研讨决策记录表\n\n> 用于实际研讨后填写。以下建议不代表已经通过。\n\n| 议题 | 建议意见 | 小组结论（会后填写） | 责任人/截止时间 | 验收证据 |\n| --- | --- | --- | --- | --- |\n| 采集任务交接 | 任务先可靠登记，再由后台执行；分别验证页提交与清洗积压恢复 |  |  | 崩溃注入记录、断点与积压核对 |\n| 认领审批事务 | 申请版本、授权、审核决定和审计保持原子提交；账号与门户两侧限制有效唯一性 |  |  | 并发场景结果、数据库约束说明 |\n| 检索版本与权限 | 内容固定在公开版本，权限按当前状态复验；统计使用同一允许集合 |  |  | R06、R1/R2、撤权测试记录 |\n| 原型架构候选 | 先验证模块化单体加独立后台执行器，测得瓶颈后再决定是否拆分 |  |  | 原型边界、资源与故障测试 |\n| SRS待补指标 | 确认失败率阈值、恢复时长、公开更新时延及部署条件 |  |  | 更新后的SRS及评审记录 |\n| AI使用记录 | 核对分析结论和图表；记录成员实际复核、修订及责任承担 |  |  | 成员复核记录 |\n\n## 会议基本信息\n\n- 日期：\n- 参与成员：\n- 主持/记录：\n- 本次确认的决定：\n- 仍待验证的问题：\n'''
(out/'03-研讨决策记录表.md').write_text(record,encoding='utf-8')

readme='''# 第9组 需求实践与分析成果研讨材料\n\n本目录包含可直接查阅和提交的研讨报告、Word/PDF版本、课堂发言提纲、实际研讨后填写的决策记录表及三张原始时序子图。\n\n报告依据本组既有调研、SRS、类图、交互模型和《ssad05.架构设计》课件编写。报告中的原型架构是待验证候选；32项设计场景不是运行测试结果；决策记录表留给实际小组研讨后填写。\n\n文件：\n- `01-研讨报告.pdf`：打印/提交版\n- `01-研讨报告.docx`：可编辑版\n- `01-研讨报告.md`：源文档，图件使用相对路径\n- `02-课堂发言提纲.md`：课堂汇报参考\n- `03-研讨决策记录表.md`：待实际讨论后填写\n- `图件/`：报告附录中引用的原始高清图\n'''
(out/'README.md').write_text(readme,encoding='utf-8')
print('Created', docx)
