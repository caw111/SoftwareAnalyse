from pathlib import Path
import json,re,csv,zipfile,hashlib,shutil,xml.etree.ElementTree as ET
from pypdf import PdfReader
R=Path.cwd();O=R/'Submit/第9组-第三次作业-需求分析';B=R/'.report-build/third-submit'
def put(n,s):(O/n).write_text(s.strip()+'\n',encoding='utf8')
put('支撑材料/本次作业要求.md','''# 第三次作业需求分析要求

整理依据为本次用户提供的五项要求。

1. 业务对象识别：展示学者、四类学术成果、机构、学术领域、认领申请、采集任务、更新记录等核心对象，说明识别依据和调研及SRS对应关系。
2. 核心业务类图：说明属性、方法及关联、聚合关系，重点说明学术成果的继承与组合建模。
3. 时序图：覆盖数据采集入库、门户认领审核、检索请求处理，说明关键交互对象与消息顺序。
4. 一致性：核对本次类图、时序图与前期用例图、活动图、状态图及SRS。
5. AI使用：说明使用方式、生成内容与人工验证情况，落实声明、理解、责任。

对应交付分别位于报告第1至5章。图件、源文件和支撑表随报告提交。
''')
shutil.copy2(R/'《软件系统分析与设计》实践任务书（一）学术成果分享平台-v1.pdf',O/'支撑材料/原始实践任务书.pdf')
# Normalize the original scenario sheet into a consistent schema.
src=R/'需求分析/A组-需求分析整合版-v1.1/支撑材料/整合版32项设计走查.csv'
rows=list(csv.DictReader(src.open(encoding='utf-8-sig')))
with (O/'支撑材料/整合版32项设计走查.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['场景编号','场景输入','预期结果及模型定位','验证性质'])
 for row in rows:
  if row['场景编号'].startswith('V'):
   inp=row['场景输入']+'：'+row['预期与模型路径'];expected=row['定位或核对说明']
  else:inp=row['场景输入'];expected=row['预期与模型路径']+'；'+row['定位或核对说明']
  w.writerow([row['场景编号'],inp,expected,row['验证性质']])
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
deck=O/'汇报材料/02-需求分析汇报.pptx';z=zipfile.ZipFile(deck)
slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
notes=[n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n)]
assert len(slides)==len(notes)==13
assert all('演讲稿' in z.read(n).decode() for n in notes)
assert not any(ET.fromstring(z.read(n)).findall('.//a:tbl',ns) for n in slides)
doc=zipfile.ZipFile(O/'01-需求分析报告.docx');body=ET.fromstring(doc.read('word/document.xml'))
text=''.join(body.itertext())
assert all(k in text for k in ['业务对象','核心业务类图','交互模型','AI使用','继承','组合'])
assert len(PdfReader(O/'01-需求分析报告.pdf').pages)==33
assert len(rows)==32
classes=list(csv.DictReader((O/'支撑材料/业务对象与SRS对应表.csv').open(encoding='utf-8-sig')))
assert len(classes)==28
missing=[]
for f in [O/'01-需求分析报告.md']:
 for rel in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',f.read_text(encoding='utf8')):
  if not (f.parent/rel).exists():missing.append(rel)
assert not missing,missing
for f in (R/'需求分析/A组-需求分析整合版-v1.1/图件').glob('*'):
 if f.is_file():assert (O/'图件'/f.name).read_bytes()==f.read_bytes()
put('支撑材料/本次材料检查记录.md','''# 本次材料检查记录

日期：2026年11月4日。检查由Codex及本地文档工具完成，属于自动结构检查和版式检查。

报告共33页，Word经本机Word打开并导出PDF。正文包含28类、45条关系的说明以及13张原有分析图，图件与来源文件逐字节核对一致。

汇报PPT共13页，每页包含演讲稿。已完成PowerPoint打开与渲染检查，并完成文件结构、字体及版面几何校验。继承示意中的箭头已按UML泛化符号修订。正文引用图件均可在包内找到。

对象与SRS对应表含28项，设计场景表含32项，跨模型追踪表覆盖三条关键业务及公共成果维护边界。前期用例、活动和状态图保留原件，作为追踪依据。

检查确认的是文档和模型材料，不代表数据库并发、采集服务、检索性能已经运行通过。已有材料未提供新增成员交叉复审签字，本记录没有补写人工通过结论。
''')
put('文件导航.md','''# 提交文件导航

- 01-需求分析报告.docx：正式报告，可继续编辑。
- 01-需求分析报告.pdf：与Word同版，33页。
- 01-需求分析报告.md：正文文本及相对图件引用。
- 汇报材料/02-需求分析汇报.pptx：13页图解汇报，每页备注含演讲稿。
- 汇报材料/逐页演讲稿.md：独立讲稿。
- 03-AI使用声明与验证记录.md：AI参与范围、实际反馈和人工确认状态。
- 图件：13张分析图，PNG及可用SVG原件。
- 模型源文件：核心类图、认领及检索Draw.io、采集CodeArts工程、模型数据。
- 支撑材料/业务对象与关系完整字典.md：每个类的属性、操作、规则及45条关系说明。
- 支撑材料/业务对象与SRS对应表.csv：28个类及其需求依据。
- 支撑材料/跨模型一致性追踪表.csv：用例、前期图、业务类、消息和状态的对应关系。
- 支撑材料/整合版32项设计走查.csv：场景输入、预期和模型定位。
- 支撑材料/前期基线：本次引用的调研、SRS、SPEC、用例图、活动图和状态图原件。
- 支撑材料/AI历史记录：保留原有AI辅助与复审状态记录。
- 支撑材料/文件校验清单.json：本包文件路径、大小及SHA256，可核对附件是否损坏。
''')
files=[]
for f in sorted(O.rglob('*')):
 if f.is_file() and f.name!='文件校验清单.json':
  data=f.read_bytes();files.append({'path':f.relative_to(O).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
put('支撑材料/文件校验清单.json',json.dumps({'date':'2026-11-04','files':files},ensure_ascii=False,indent=2))
dest=R/'Submit/第9组-第三次作业-需求分析.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
 for f in sorted(O.rglob('*')):
  if f.is_file():archive.write(f,str(Path(O.name)/f.relative_to(O)))
with zipfile.ZipFile(dest) as archive:
 assert archive.testzip() is None
 assert len(archive.namelist())==len(files)+1
(B/'final-audit.json').write_text(json.dumps({'doc_pages':33,'ppt_slides':13,'classes':28,'design_scenarios':32,'files':len(files)+1,'zip_bytes':dest.stat().st_size,'zip_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'checks':'passed'},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'zip':str(dest),'files':len(files)+1,'MB':round(dest.stat().st_size/1024/1024,1)},ensure_ascii=False))
