from pathlib import Path
import re,json,shutil,hashlib,sys
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image
import content,diagrams

ROOT=content.ROOT
OUT=diagrams.OUT
BUILD=Path(__file__).parent
SUP=OUT/'支撑材料';SRC=OUT/'模型源文件';FIG=OUT/'图件'
for p in [OUT,SUP,SRC,FIG]:p.mkdir(parents=True,exist_ok=True)
diagrams.main()
specs=json.loads((SRC/'新增交互模型.json').read_text(encoding='utf-8'))
messages=['# 新增交互消息表','此表与新增Draw.io、PNG、SVG同源。片段条件体现正常、替代和异常路径；ref展开见报告相应图及说明。']
for spec in specs:
    messages += ['## '+spec['title'],'| 消息 | 发送者 → 接收者 | 内容 | 所在分支 |','| --- | --- | --- | --- |']
    def visit(rows,conditions):
        for row in rows:
            if row['kind']=='msg':
                a=spec['lanes'][row['a']].split('«')[0].replace('\n','').strip();b=spec['lanes'][row['b']].split('«')[0].replace('\n','').strip()
                messages.append(f"| {row['id']} | {a} → {b} | {row['text']} | {'；'.join(conditions) or '主流程'} |")
            elif row['kind']=='frame':visit(row['rows'],conditions+[row['op']+' ['+row['guard']+']'])
            elif row['kind']=='else':conditions=conditions[:-1]+['else ['+row['guard']+']']
            elif row['kind']=='ref':messages.append('| ref | 交互引用 | '+row['text']+' | '+('；'.join(conditions) or '主流程')+' |')
    visit(spec['rows'],[])
(SUP/'新增交互消息表.md').write_text(''.join(('\n' if i and line.startswith('|') and messages[i-1].startswith('|') else '\n\n' if i else '')+line for i,line in enumerate(messages)),encoding='utf-8')

A2=ROOT/'需求分析/A2-赵琦';A3=ROOT/'需求分析/A组-A3-王彦骁-采集入库-v1.2'
for f in (A2/'图件').iterdir():
    if f.suffix.lower() in ['.png','.svg']:shutil.copy2(f,FIG/f.name)
for f in A3.glob('*.png'):shutil.copy2(f,FIG/f.name)
for f in [A2/'02-核心业务类图.drawio',A3/'03-CodeArts正式模型工程.zip']:
    shutil.copy2(f,SRC/f.name)
shutil.copy2(A2/'过程记录/生成源/model.json',SRC/'A2-核心业务模型.json')
for filename in ['02-类与关系说明.md','02-A2赵琦-核心业务类图与领域关系设计.md']:
    shutil.copy2(A2/filename,SUP/('原始A2-'+filename))
for filename in ['03-采集入库时序图说明.md','03-采集六状态对照表.md','03-异常与边界场景.md']:
    shutil.copy2(A3/filename,SUP/('原始A3-'+filename))

report=content.report()
(OUT/'本组-需求分析报告.md').write_text(report,encoding='utf-8')
(SUP/'业务对象与关系完整字典.md').write_text(content.dictionary(),encoding='utf-8')
(SUP/'15分钟汇报讲解稿.md').write_text(content.TALK,encoding='utf-8')

# Retain the original report's A4 page setup; replace the obsolete draft body.
doc=Document(ROOT/'需求分析/A1-昌昂旺/本组-需求分析报告.docx')
body=doc._element.body
for node in list(body):
    if node.tag!=qn('w:sectPr'):body.remove(node)
sec=doc.sections[0]
sec.top_margin=Cm(1.85);sec.bottom_margin=Cm(1.8)
sec.header_distance=Cm(.8);sec.footer_distance=Cm(.8)
sec.left_margin=Cm(2.1);sec.right_margin=Cm(2.1)
widthcm=16.8
for name in ['Normal','Title','Heading 1','Heading 2','Heading 3','Caption']:
    s=doc.styles[name];s.font.name='Calibri';s.font.color.rgb=RGBColor(0,0,0)
    s._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'微软雅黑' if name!='Normal' else '宋体')
    s.paragraph_format.space_before=Pt(0);s.paragraph_format.space_after=Pt(7)
    s.paragraph_format.line_spacing=1.2
    if name=='Normal':s.font.size=Pt(10.5)
    elif name=='Title':s.font.size=Pt(22);s.font.bold=True;s.paragraph_format.space_after=Pt(18)
    elif name=='Caption':s.font.size=Pt(9);s.font.italic=False
    else:s.font.size=Pt(15 if name=='Heading 1' else 12);s.font.bold=True;s.paragraph_format.space_after=Pt(13)
    ppr=s._element.find(qn('w:pPr'))
    if ppr is not None:
        for el in list(ppr):
            if el.tag==qn('w:pBdr'):ppr.remove(el)

for h in [sec.header,sec.footer]:
    for p in list(h.paragraphs):
        p.clear()
header=sec.header.paragraphs[0];header.text='第9组 A组    学术成果分享平台需求分析    v1.0'
header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
for r in header.runs:r.font.size=Pt(8);r.font.color.rgb=RGBColor.from_string('666666')
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=footer.add_run('第 ');r.font.size=Pt(9)
f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');footer._p.append(f)
footer.add_run(' 页').font.size=Pt(9)

def clean(t):return re.sub(r'`([^`]+)`',r'\1',t).replace('**','')
def table(lines):
    rows=[[clean(v.strip()) for v in line.strip().strip('|').split('|')] for line in lines if not re.match(r'^\|[\s:|\-]+\|$',line)]
    n=len(rows[0]);t=doc.add_table(rows=0,cols=n);t.autofit=False
    widths={2:[4,12.8],3:[4.3,7.3,5.2],4:[3.5,5,4.5,3.8],7:[1,3,1.3,2.1,3,1.3,5.1]}.get(n,[widthcm/n]*n)
    for c,w in zip(t.columns,widths):c.width=Cm(w)
    for i,row in enumerate(rows):
        cells=t.add_row().cells
        for j,cell in enumerate(cells):
            cell.width=Cm(widths[j]);cell.text=row[j] if j<len(row) else ''
            pr=cell._tc.get_or_add_tcPr()
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E6EDF4' if i==0 else ('F6F8FA' if i%2==0 else 'FFFFFF'));pr.append(shade)
            borders=OxmlElement('w:tcBorders')
            for side in ['top','left','bottom','right']:
                b=OxmlElement('w:'+side);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'D9D9D9');borders.append(b)
            pr.append(borders)
            mar=OxmlElement('w:tcMar')
            for side,v in [('top','75'),('bottom','75'),('left','90'),('right','90')]:
                a=OxmlElement('w:'+side);a.set(qn('w:w'),v);a.set(qn('w:type'),'dxa');mar.append(a)
            pr.append(mar)
            for p in cell.paragraphs:
                p.paragraph_format.space_before=Pt(1);p.paragraph_format.space_after=Pt(1);p.paragraph_format.line_spacing=1.06
                for r in p.runs:r.font.size=Pt(9.4);r.bold=(i==0)
        prop=t.rows[-1]._tr.get_or_add_trPr();prop.append(OxmlElement('w:tblHeader' if i==0 else 'w:cantSplit'))
    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(1);p.paragraph_format.line_spacing=Pt(2)

page_titles=[]
for pi,section in enumerate(content.PAGES):
    lines=section.splitlines();title=lines[0][3:];page_titles.append(title)
    p=doc.add_paragraph(title,'Title' if pi==0 else 'Heading 1')
    if pi:p.paragraph_format.page_break_before=True
    else:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    i=1
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('|'):
            ls=[]
            while i<len(lines) and lines[i].strip().startswith('|'):ls.append(lines[i].strip());i+=1
            table(ls);continue
        if line.startswith('!['):
            match=re.match(r'!\[(.*?)\]\((.*?)\)',line);path=OUT/match[2]
            with Image.open(path) as im:w,h=im.size
            # Keep full drawings on one page; all supplied as separately zoomable PNGs.
            max_h=20.3 if '03-采集' in path.name or '05-' in path.name or '06-' in path.name else 21.0
            ww=min(widthcm,max_h*w/h)
            p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(5)
            p.add_run().add_picture(str(path),width=Cm(ww))
            p.paragraph_format.keep_with_next=True
        else:
            p=doc.add_paragraph(clean(line),'Caption' if re.match(r'^图\d-',line) else 'Normal')
            if re.match(r'^图\d-',line):p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if pi==0 and i<6:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        i+=1
doc.core_properties.title='学术成果分享平台需求分析报告'
doc.core_properties.subject='业务对象 核心业务类图 关键用例交互'
doc.core_properties.author='第9组A组（AI辅助整合，待成员复审）'
doc.core_properties.comments='依据本组现有材料补齐模型；不代表运行验证或人工评审通过。'
doc.save(OUT/'本组-需求分析报告.docx')
(BUILD/'logical-pages.json').write_text(json.dumps(page_titles,ensure_ascii=False,indent=2),encoding='utf-8')

notes='''# 来源与修订记录

版本v1.0，2026-10-26。本次真实请求为依据当前截图和目录材料完成文档与缺失图片。报告保留A1章节任务，重写旧占位并整合当前模型。

## 采用材料

- A1《本组-需求分析报告-初稿.md》《本组-需求分析报告.docx》及对象、追踪、交接和AI记录。
- A2 v1.0的model.json、类与关系说明、Draw.io及六张PNG/SVG。
- A3 v1.2主图及两个必要子图、时序说明、六状态说明和原始CodeArts工程。
- 当前docs/02.需求建模中的SRS、SPEC、需求条目与验收场景。
- 用户本次提供的“（三）需求分析”截图；未将历史第一份任务书冒充本次新通知。

## 本次变更

1. 补建认领主图与原子授权／撤回子图，消息CL01～CL17、CX01～CX10。
2. 补建检索主图与权限计数／分页子图，消息Q01～Q16、QX01～QX08。
3. 保留A2/A3原图，在整合正文统一对象别名和操作职责。
4. 纠正ReviewRecord混用：采集质量复核采用GovernanceReview，门户历史采用ReviewRecord。
5. 保留六状态、有效授权双向唯一、同贡献机构、原文版本／观测分离、同版读取／实时权限等当前约束。
6. 将权限修订令牌和有界重算显式标为本次设计方案；未把候选权重当作已部署算法。
7. 生成Word与同源Markdown，补入追踪、静态场景核对及15分钟具体讲解稿。

## AI辅助和真实验证边界

执行工具为Codex桌面文件读取、Python文档和图件生成、本地格式及结构检查、渲染检查。未登录CodeArts，没有运行平台业务或性能测试。未填写成员实际复审、教师评审通过或A4/A5个人完成记录。原个人目录及历史提交保持不变。

输出Draw.io包含原生可编辑图元，不是仅嵌入PNG。SVG、PNG与Draw.io由同源新增模型生成；原A2/A3文件按字节复制。model.json及源脚本用于追溯与重建，不是平台实现代码。

## 审核时关注

确认A2分析决策是否采用；核对权限与材料版本、有效授权约束、补交／撤回状态；核对检索计数权限策略及版本失效行为；确认课程是否还要求新增图的CodeArts原生工程或最终PPT。本包包含Word、Markdown及图片源，新增图未迁移到CodeArts，本轮未制作新的PPT。
'''
(SUP/'来源与修订记录.md').write_text(notes,encoding='utf-8')

input_files=[ROOT/'docs/02.需求建模'/n for n in ['系统需求规格说明书_SRS.md','核心模块开发规范_SPEC.md','需求条目与验收场景.md']]
input_files += [ROOT/'需求分析/A1-昌昂旺'/n for n in ['本组-需求分析报告.docx','本组-需求分析报告-初稿.md']]
input_files += list((A2/'图件').glob('*'))+[A2/'02-核心业务类图.drawio',A2/'过程记录/生成源/model.json']+list(A3.glob('*.png'))+[A3/'03-CodeArts正式模型工程.zip']
def info(p):return {'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(SUP/'输入文件校验清单.json').write_text(json.dumps([info(p) for p in input_files if p.is_file()],ensure_ascii=False,indent=2),encoding='utf-8')
for f in ['diagrams.py','content.py','build.py']:shutil.copy2(BUILD/f,SRC/f)
readme='''# A组需求分析整合版 v1.0

2026-10-26。入口为本组-需求分析报告.docx或同名Markdown。

已补齐门户认领审核与检索请求处理两套时序模型，并各附一个必要子交互；保留并整合已有A2类图和A3采集交互，共13张PNG。Word给出对象、属性和行为解释、状态、事务边界、异常、追踪及设计走查。

- 图件：PNG用于查看／插入文档，SVG用于缩放；A3原交付只有PNG。
- 模型源文件：A2六页Draw.io、A3原始CodeArts工程、4个新增Draw.io及JSON／脚本。
- 支撑材料：完整对象字典、原模型正文、来源修订记录、15分钟讲解稿、文件校验清单。

原岗位目录未覆盖。本版为AI辅助整合，新增图供成员复审，不冒称A4/A5已交接；正式人审／课堂通过待真实记录。用户本轮重点为文档与缺失图片，未制作新PPT；新增图未做CodeArts平台导入。

新图编辑：直接打开模型源文件中的Draw.io文件修改图元。自动重建的原始工作脚本位于仓库.report-build/analysis-complete，源文件目录的脚本是本次备份；若在不同位置使用，应先调整脚本中的ROOT／输出路径。手工修改Draw.io不会自动回写JSON或报告。
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
assert len(list(FIG.glob('*.png')))==13
assert len(doc.inline_shapes)==13
assert len(content.MODEL['classes'])==28 and len(content.MODEL['relations'])==45
assert len(re.findall(r'!\[',report))==13
assert all((OUT/p).exists() for p in re.findall(r'!\[.*?\]\((.*?)\)',report))
print(json.dumps({'output':str(OUT),'logical_pages':len(content.PAGES),'images':len(doc.inline_shapes),'report_characters':len(report)},ensure_ascii=False))
