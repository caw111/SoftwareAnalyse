from pathlib import Path
import json,hashlib,shutil,re,csv,zipfile
import xml.etree.ElementTree as E
from PIL import Image
from docx import Document
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2];BUILD=Path(__file__).parent
OUT=ROOT/'需求分析/A组-需求分析整合版-v1.1';SUP=OUT/'支撑材料'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def meta(p,base):return {'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}

# Preserve complete Group2 source directory so its original internal links work.
g2=BUILD/'references/Group2-b93110b/前期成果'
ext=SUP/'外部对照/Group2-b93110b'
shutil.copytree(g2,ext,dirs_exist_ok=True)
idxpath=SUP/'对照来源索引.json';idx=json.loads(idxpath.read_text(encoding='utf-8'))
idx['files']=[meta(p,SUP) for p in (SUP/'外部对照').rglob('*') if p.is_file()]
idxpath.write_text(json.dumps(idx,ensure_ascii=False,indent=2),encoding='utf-8')
sources=[]
for p in (ROOT/'docs/02.需求建模').glob('*.md'):
    if p.name in ['系统需求规格说明书_SRS.md','核心模块开发规范_SPEC.md','需求条目与验收场景.md']:
        t=SUP/'需求依据'/p.name;t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,t);sources.append({'source':str(p),**meta(t,OUT)})
image=Path('E:/weichat/xwechat_files/wxid_quoop5hprm8122_9298/temp/RWTemp/2026-10/53bc36a9639b14941c539be76d46da6f/35ec334231ceb4f989f87caf3c9e5f67.png')
if image.exists():
    t=SUP/'需求依据/本次需求分析要求截图.png';shutil.copy2(image,t);sources.append({'source':str(image),**meta(t,OUT)})
pdfs=list(ROOT.glob('《软件系统分析与设计》实践任务书*.pdf'))
for p in pdfs:
    t=SUP/'需求依据'/p.name;shutil.copy2(p,t);sources.append({'source':str(p),**meta(t,OUT)})
(SUP/'补充需求依据校验.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')

# Check v1.0 exactly against the pre-revision snapshot.
oldroot=ROOT/'需求分析/A组-需求分析整合版-v1.0'
old=json.loads((BUILD/'v1.0-before-revision.json').read_text(encoding='utf-8'))
assert all(sha(oldroot/x['path'])==x['sha256'] for x in old)
assert len([p for p in oldroot.rglob('*') if p.is_file()])==len(old)
models=json.loads((OUT/'模型源文件/A2-核心业务模型.json').read_text(encoding='utf-8-sig'))
assert len(models['classes'])==28 and len(models['relations'])==45
specs=json.loads((OUT/'模型源文件/新增交互模型.json').read_text(encoding='utf-8'))
index=json.loads((OUT/'模型消息索引.json').read_text(encoding='utf-8'))
message_ids=[]
for diagram in index:
    ids=[m['id'] for m in diagram['messages']];message_ids+=ids
    p=OUT/'模型源文件'/(diagram['file']+'.drawio')
    xml=E.parse(p);cells=xml.findall('.//mxCell')
    assert len(cells)>10 and not any('data:image' in c.get('style','') for c in cells)
    raw=p.read_text(encoding='utf-8')
    assert all(mid in raw for mid in ids)
    assert len(xml.findall('.//diagram'))==1
assert len(message_ids)==53 and len(set(message_ids))==53
assert {'Q15a','QX04a'}<=set(message_ids)
assert len(E.parse(OUT/'模型源文件/02-核心业务类图.drawio').findall('.//diagram'))==6
figs=list((OUT/'图件').glob('*.png'));assert len(figs)==13
for p in figs:
    with Image.open(p) as im:im.verify()
md=(OUT/'本组-需求分析报告.md').read_text(encoding='utf-8')
links=re.findall(r'!\[.*?\]\((.*?)\)',md)
assert len(links)==13 and all((OUT/x).is_file() for x in links)
docpath=OUT/'本组-需求分析报告.docx';doc=Document(docpath)
assert len(doc.inline_shapes)==13
with zipfile.ZipFile(docpath) as z:assert z.testzip() is None
pdf=BUILD/'render/report-v1.1.pdf';reader=PdfReader(pdf)
assert len(reader.pages)==41
pages=list((BUILD/'render').glob('v11-page-*.png'));assert len(pages)==41
for n,p in enumerate(reader.pages,1):
    txt=p.extract_text() or '';assert f'第 {n} 页' in txt
    assert '\ufffd' not in txt
    box=p.mediabox;assert abs(float(box.width)-595.3)<2 and abs(float(box.height)-841.9)<2
for x in json.loads((SUP/'输入文件校验清单.json').read_text(encoding='utf-8')):
    assert sha(ROOT/x['path'])==x['sha256']
for p in (ROOT/'需求分析/A2-赵琦/图件').glob('*'):
    if p.suffix in ['.png','.svg']:assert sha(p)==sha(OUT/'图件'/p.name)
for p in (ROOT/'需求分析/A组-A3-王彦骁-采集入库-v1.2').glob('*.png'):assert sha(p)==sha(OUT/'图件'/p.name)
rows=re.findall(r'^\| ((?:T|V)\d{2}) (.*?) \| (.*?) \| (.*?) \|$',md,re.M)
assert len(rows)==32 and len({x[0] for x in rows})==32
with (SUP/'整合版32项设计走查.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['场景编号','场景输入','预期与模型路径','定位或核对说明','验证性质']);w.writerows([list(r)+['静态设计核对，未运行平台'] for r in rows])

qa={'version':'v1.1','date':'2026-10-26','scope':'文件结构、图文一致性、来源字节校验及排版；非业务运行测试',
    'word_pages':41,'inline_images':13,'classes':28,'relations':45,'new_editable_drawio':4,'new_messages':53,'scenario_designs':32,
    'v1.0_unchanged':True,'input_hashes_unchanged':True,'original_A2_A3_copies_identical':True,
    'github_commit':idx['github']['commit'],'external_reference_files':len(idx['files']),
    'render':{'packaged_renderer':'失败，bundle未提供soffice.exe；未调用系统LibreOffice','fallback':'独立隐藏Word.Application COM只读打开并导出PDF，关闭本次实例；Poppler 115dpi','visual_review':'v11-page-01到41逐页查看；新检索主图和子图高清PNG另行查看','result':'未发现裁切、重叠、缺字、表格断裂或空白溢出页；大图另附高清图和全文消息表','pdf_sha256':sha(pdf),'docx_sha256':sha(docpath)},
    'runtime_tests':'未执行','human_review':'未签署','CodeArts':'保留原A3工程；新增Draw.io未迁移到CodeArts'}
(SUP/'本版校验记录.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
(SUP/'本版校验说明.md').write_text('''# v1.1交付校验说明

2026-10-26。本次核对文件结构、来源字节、消息编号、图文引用及Word排版，不表示平台业务测试或真人评审已经通过。

已核对：28类、45关系；4个新增可编辑Draw.io，53条唯一消息；13张PNG及Word中的13幅嵌入图；报告41页；32项设计场景；A2/A3原件复制字节一致；v1.0文件与修订前清单一致；外部源文件与固定提交、原包可追溯。

排版：打包渲染器因依赖包没有soffice.exe无法启动，改用独立隐藏的Word兼容COM实例只读导出PDF，再用Poppler生成41页PNG并逐页查看。未发现裁切、重叠、乱码或额外空白页。总览大图供定位，细节可用同包高清PNG/SVG、对象字典和完整消息表查看。排版中间PDF/页图仅保留于工作区内部目录，不放进提交包。

正式人审、50组查询、性能和业务运行测试仍须实际开展。新增图为Draw.io源，未将其改扩展名冒充CodeArts原生工程。模型设计和静态校验完成不等于课堂评审已通过。
''',encoding='utf-8')
readme=(OUT/'README.md').read_text(encoding='utf-8')
readme+='\n## 交付校验和编辑入口\n\nWord共41页，已逐页检查排版。新增图包含53条唯一消息，类模型28类45关系，正文13幅图齐全；32项场景另有CSV。详见支撑材料/本版校验说明.md。\n\n重建v1.1应在当前仓库使用.report-build/analysis-complete/revision.py；build.py是原v1.0基线生成器。模型源文件目录保留脚本快照，跨目录使用时需调整路径与输入，不应直接覆盖历史版本。支撑材料/外部对照中的Group2为原目录结构，B5为本次采用的原说明、PNG与puml选编；完整B5原ZIP路径及哈希另见外部压缩包校验.json。\n'
(OUT/'README.md').write_text(readme,encoding='utf-8')
for name in ['finalize.py','render-native.ps1']:shutil.copy2(BUILD/name,OUT/'模型源文件'/name)
manifest=[meta(p,OUT) for p in OUT.rglob('*') if p.is_file() and p.name!='交付文件清单.json']
(OUT/'交付文件清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
target=ROOT/'Submit/作业3_需求分析/A组-需求分析整合版-v1.1.zip'
assert not target.exists(), 'Use a new release name instead of overwriting an existing archive.'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,Path(OUT.name)/p.relative_to(OUT))
with zipfile.ZipFile(target) as z:assert z.testzip() is None
result={'zip':str(target),'bytes':target.stat().st_size,'sha256':sha(target),'files':len(manifest)+1,'crc':'pass'}
(BUILD/'final-package-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
target.with_suffix('.zip.sha256').write_text(result['sha256']+'  '+target.name+'\n',encoding='utf-8')
print(json.dumps({**qa,**result},ensure_ascii=False))
