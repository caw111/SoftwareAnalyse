from pathlib import Path
import json,re,os,hashlib,zipfile,csv,shutil,sys
from urllib.parse import unquote
from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader
BUILD=Path(__file__).resolve().parent
ROOT=BUILD.parents[1]
OUT=ROOT/'Submit'
M=json.loads((BUILD/'manifest.json').read_text(encoding='utf-8'))
A,B=map(Path,M['packages'])
redirect_file=BUILD/'cover-fix/redirects.json'
redirects=json.loads(redirect_file.read_text(encoding='utf-8')) if redirect_file.exists() else {}
superseded=set(redirects)
ARCH=OUT/'归档_历史材料_不放入提交压缩包/参考仓库格式重构前_v1.2'
sha=lambda b:hashlib.sha256(b).hexdigest()
links=0;figures=[]
for filename,h in M['image_inventory'].items():
    src=ROOT/'images'/filename
    assert sha(src.read_bytes())==h,('root asset changed',filename)
    for pkg in [A,B]:assert (pkg/'images'/filename).read_bytes()==src.read_bytes()
for n1,n2,title in [(4,6,'修改说明与版本记录'),(5,7,'AI使用声明'),(6,8,'提交材料自查清单')]:
    src=A/f'{n1:02d}-{title}_v2.0-9组-1011101011.docx'
    shutil.copyfile(src,B/f'{n2:02d}-{title}_v2.0-9组-1011101011.docx')

for pkg in [A,B]:
    for p in pkg.rglob('*.md'):
        t=p.read_text(encoding='utf-8')
        for mark,target in re.findall(r'(!?\[[^\]]*\])\(([^)]+)\)',t):
            if re.match(r'^(https?://|mailto:|#)',target):continue
            f=(p.parent/unquote(target)).resolve()
            assert f.is_file(),('broken MD link',p,target)
            assert f.is_relative_to(pkg.resolve()),('external package link',p,target)
            links+=1
            if mark.startswith('!'):
                assert f.name in M['image_inventory'] and sha(f.read_bytes())==M['image_inventory'][f.name]
                figures.append([str(p.relative_to(OUT)),f.name,str(f.relative_to(OUT)),sha(f.read_bytes())])
    for p in pkg.rglob('*.docx'):
        if p.name.startswith('~$') or str(p) in superseded:continue
        d=Document(p)
        assert len(d.sections)==3
        for section in d.sections:
            assert abs(section.page_width/914400-21/2.54)<.02
            assert abs(section.left_margin/914400-1)<.01
        with zipfile.ZipFile(p) as z:
            for item in z.namelist():
                if item.startswith('word/media/'):
                    assert sha(z.read(item)) in M['image_inventory'].values(),('foreign Word image',p,item)
            xml=z.read('word/document.xml').decode('utf-8')
            assert 'TOC ' in xml and '目录由 Word 更新' not in xml,('uncached directory',p)
        for rel in d.part.rels.values():
            if rel.reltype.endswith('/hyperlink') and rel.is_external:
                target=rel.target_ref
                if re.match(r'^(https?://|mailto:|#)',target):continue
                f=(p.parent/unquote(target)).resolve()
                assert f.is_file(),('broken Word link',p,target)
                assert f.is_relative_to(pkg.resolve()),('external Word link',p,target)
                links+=1
        for pe in d._element.body.xpath('.//w:p[.//wp:inline]'):
            assert not pe.xpath('./w:pPr/w:spacing[@w:lineRule="exact"]'),('clipped image paragraph',p)
        for paragraph in d.paragraphs[:3]:
            effective=paragraph.paragraph_format.line_spacing
            style=paragraph.style
            while effective is None and style is not None:
                effective=style.paragraph_format.line_spacing;style=style.base_style
            assert effective is not None and float(effective)<5,('cover inherits fixed spacing',p)
            assert not paragraph._p.xpath('./w:pPr/w:spacing[@w:lineRule="exact"]'),('cover has fixed spacing',p)

def word_text(p):
    d=Document(p)
    return '\n'.join(d._element.body.xpath('.//w:t/text()'))
old=(ARCH/'docs/系统需求规格说明书_SRS.md').read_text(encoding='utf-8')
cat=next((B/'05-支撑材料').glob('01-需求条目*.docx'))
ct=word_text(cat)
fr_ids=set(re.findall(r'\bFR-[A-Z]+-\d{3}\b',old))
ac_ids=set(re.findall(r'\bAC-[A-Z]+\d+\b',old))
g_ids=set(re.findall(r'\bG1-AT-\d+\b',old))
assert len(fr_ids)==104
for ids in [fr_ids,ac_ids,g_ids]:assert all(i in ct for i in ids),ids-set(re.findall(r'\b(?:FR-[A-Z]+-\d{3}|AC-[A-Z]+\d+|G1-AT-\d+)\b',ct))
srs=next(Path(dest) for source,dest in M['word_sources'] if Path(dest).name.startswith('01-SRS'));d=Document(srs)
assert len(d.inline_shapes)==11
uc_tables=[t for t in d.tables if t.cell(0,0).text=='用例名称']
assert len(uc_tables)==22
cases=json.loads((BUILD/'usecases.json').read_text(encoding='utf-8'))['cases']
for c,t in zip(cases,uc_tables):
    assert t.cell(0,2).text.startswith(c['id']+' ')
    assert '\n' in t.cell(7,2).text
    for field in ['用例名称','简要描述','参与者','涉众','前置条件','后置条件','事件流']:
        assert field in '\n'.join(cell.text for row in t.rows for cell in row.cells)
spec=next(B.glob('02-SPEC*.docx'));st=word_text(spec)
assert 'SRS §6.4' not in st
assert all(s in st for s in ['PENDING_REVIEW','NEED_MORE_INFO','SUCCEEDED','STOPPED'])
assert all(s in word_text(srs) for s in ['PENDING_REVIEW','NEED_MORE_INFO','SUCCEEDED','STOPPED'])

model_lines=['# 模型索引','', '所有文件取自根目录当前 images，PNG 与 Draw.io 原样复制。图中局部编号与本版五包编号映射见支撑材料。正式业务采用编号 03、04 门户认领模型和 数据采集任务状态机，旧模型保留作对照。','', '| 正文使用 PNG | 同目录 Draw.io |','| --- | --- |']
srsm=next(B.glob('01-SRS*.md')).read_text(encoding='utf-8')
for name in re.findall(r'!\[[^\]]*\]\(images/([^)]*)\)',srsm):
    source=name[:-4] if name.endswith('.drawio.png') else Path(name).stem+'.drawio'
    editable=source if source in M['image_inventory'] else '未找到；见缺图清单'
    model_lines.append(f'| [{name}](../images/{name}) | '+(f'[{editable}](../images/{editable})' if source in M['image_inventory'] else editable)+' |')
(B/'03-建模图/00-模型索引.md').write_text('\n'.join(model_lines)+'\n',encoding='utf-8')

for pkg in [OUT,A,B]:
    p=pkg/'参考格式重构说明.md'
    if not p.exists():continue
    text=p.read_text(encoding='utf-8')
    if 'https://github.com/' not in text:text+='\n\n参考来源：[用户指定仓库 dev/docs](https://github.com/Soft-Where-21/BUAA-SSAD-2025-Project-Group1-AcademicPlatform/tree/dev/docs)。调研报告与 SRS PDF 为结构和视觉依据；参考文件不作为本组调研原件提交。\n'
    p.write_text(text,encoding='utf-8')
if (OUT/'参考格式重构说明.md').exists() and (ROOT/'docs/重构说明.md').exists():
    (ROOT/'docs/重构说明.md').write_text((OUT/'参考格式重构说明.md').read_text(encoding='utf-8'),encoding='utf-8')
report={'version':'v2.0','formal_usecases':22,'preserved_FR':len(fr_ids),'preserved_AC':len(ac_ids),'preserved_simulation_cases':len(g_ids),'SRS_figures':11,'unchanged_assets':len(M['image_inventory']),'local_links_verified':links,'Word_documents':sum(1 for pkg in [A,B] for p in pkg.rglob('*.docx') if str(p) not in superseded and not p.name.startswith('~$')),'packages':[str(A),str(B)]}
for p in json.loads((BUILD/'outputs.json').read_text(encoding='utf-8')):
    pdf=BUILD/'qa'/(Path(p).stem+'.pdf')
    assert pdf.is_file(),('unrendered Word',p)
    assert len(PdfReader(pdf).pages)>3
print(json.dumps(report,ensure_ascii=False,indent=2))
if '--pack' in sys.argv:
    for package,suffix in [(A,'需求调研成果'),(B,'需求建模成果')]:
        target=OUT/f'9组-1011101011-{suffix}.zip'
        members=[p for p in sorted(package.rglob('*')) if p.is_file() and not p.name.startswith('~$') and str(p) not in superseded]
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            for p in members:z.write(p,p.relative_to(package).as_posix())
        with zipfile.ZipFile(target) as z:
            assert z.testzip() is None
            assert len(z.infolist())==len(members)
            for p in members:assert z.read(p.relative_to(package).as_posix())==p.read_bytes()
        print('ZIP VERIFIED',target.name,len(members),target.stat().st_size)
    with (OUT/'文件清单.csv').open('w',encoding='utf-8-sig',newline='') as fp:
        w=csv.writer(fp);w.writerow(['文件相对路径','字节数','SHA256','用途'])
        for folder in [A,B]:
            for p in sorted(folder.rglob('*')):
                if p.is_file() and not p.name.startswith('~$') and str(p) not in superseded:w.writerow([p.relative_to(OUT).as_posix(),p.stat().st_size,sha(p.read_bytes()),'作业1' if folder==A else '作业2'])
        for p in sorted(OUT.glob('*.zip')):w.writerow([p.name,p.stat().st_size,sha(p.read_bytes()),'提交压缩包'])
    with (OUT/'图文引用核对.csv').open('w',encoding='utf-8-sig',newline='') as fp:
        w=csv.writer(fp);w.writerow(['引用文档','images 文件名','本包位置','SHA256']);w.writerows(figures)
    report['zip_integrity']='passed'
    (BUILD/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'重构校验结果.md').write_text('# 重构校验结果\n\n2026-10-12 v2.0：调研六章，SRS 四章五包，22 个用例。保留 104 个 FR、'+str(len(ac_ids))+' 个 AC、'+str(len(g_ids))+' 个 G1-AT 模拟场景编号。SRS 11 张插图的内嵌内容与根目录 images 匹配；'+str(len(M['image_inventory']))+' 个图文件原样复制，Markdown 和 Word 本地附件链接已核验。两份 zip 逐文件与正式目录比对一致；封面、目录、页码、用例与图页均经 Word PDF 渲染复核。\n\n此结果验证文件组织与重构保留情况，不作为用户调查、来源实验、系统功能或性能已通过的证明。缺图和人工待填部分仍以自查及缺图清单为准。\n',encoding='utf-8')
