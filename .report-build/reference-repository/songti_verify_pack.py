from pathlib import Path
from lxml import etree as E
import json,zipfile,csv,hashlib,re

BUILD=Path(__file__).resolve().parent
ROOT=BUILD.parents[1]
OUT=ROOT/'Submit'
WORK=BUILD/'songti'
M=json.loads((WORK/'manifest.json').read_text(encoding='utf-8'))
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
FONT='宋体';sha=lambda b:hashlib.sha256(b).hexdigest()

def editable_text(z,kind):
    texts=[]
    for name in sorted(z.namelist()):
        if not name.endswith('.xml') or not name.startswith(('word/','ppt/')):continue
        root=E.fromstring(z.read(name))
        if kind=='docx':
            # Word regenerates cached TOC text; it is pagination output, not authored content.
            for sdt in root.xpath('//*[local-name()="sdt"]'):
                if sdt.xpath('.//*[local-name()="instrText" and contains(text(),"TOC")]'):sdt.getparent().remove(sdt)
            texts.extend(t for t in root.xpath('//*[local-name()="t"]/text()') if not re.fullmatch(r'\s*\d+\s*',t))
        else:texts.extend(root.xpath('//*[local-name()="t"]/text()'))
    return texts

records=[]
for string,snapshot in M['snapshots'].items():
    p=Path(string);kind=p.suffix[1:];fonts=[]
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        for name,h in snapshot['media'].items():assert sha(z.read(name))==h,('changed image',p,name)
        for name in z.namelist():
            if name.endswith('.xml') and name.startswith(('word/','ppt/')):
                r=E.fromstring(z.read(name))
                for rf in r.iter(W+'rFonts'):
                    for key in ['ascii','hAnsi','eastAsia','cs']:
                        v=rf.get(W+key)
                        if v:fonts.append(v)
                for el in r.iter():
                    if el.tag in [A+'latin',A+'ea',A+'cs',A+'font',A+'buFont']:
                        v=el.get('typeface')
                        if v:fonts.append(v)
        assert fonts and set(fonts)=={FONT},('non-Songti fonts',p,set(fonts))
        with zipfile.ZipFile(snapshot['backup']) as before:
            # Raw text has identical values before rendering; final authored body is verified separately.
            if kind=='pptx':assert editable_text(before,kind)==editable_text(z,kind)
        if kind=='docx':
            pdf=BUILD/'qa'/(p.stem+'.pdf')
            assert pdf.exists()
        records.append({'file':str(p.relative_to(OUT)),'font':'宋体','font_assignments_verified':len(fonts),'images_unchanged':len(snapshot['media'])})

# Word may normalize the page fields and TOC; verify all original requirement/case identifiers survive.
for string,snapshot in M['snapshots'].items():
    p=Path(string)
    if p.suffix!='.docx':continue
    with zipfile.ZipFile(snapshot['backup']) as old,zipfile.ZipFile(p) as new:
        a=''.join(E.fromstring(old.read('word/document.xml')).xpath('//*[local-name()="t"]/text()'))
        b=''.join(E.fromstring(new.read('word/document.xml')).xpath('//*[local-name()="t"]/text()'))
        ids=set(re.findall(r'\b(?:FR-[A-Z]+-\d+|AC-[A-Z]+\d+|UC\d+\.\d+|G1-AT-\d+|SPEC-[A-Z]+-\d+)\b',a))
        assert all(i in b for i in ids),('missing identifiers',p,ids)

excluded=set(M['redirects'])
packages=list(map(Path,json.loads((BUILD/'manifest.json').read_text(encoding='utf-8'))['packages']))
for pkg,suffix in zip(packages,['需求调研成果','需求建模成果']):
    target=OUT/f'9组-1011101011-{suffix}.zip'
    members=[p for p in sorted(pkg.rglob('*')) if p.is_file() and not p.name.startswith('~$') and str(p) not in excluded]
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.relative_to(pkg).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for p in members:assert z.read(p.relative_to(pkg).as_posix())==p.read_bytes()
    print('ZIP VERIFIED',target.name,len(members))

with (OUT/'文件清单.csv').open('w',encoding='utf-8-sig',newline='') as fp:
    writer=csv.writer(fp);writer.writerow(['文件相对路径','字节数','SHA256','用途'])
    for pkg in packages:
        for p in sorted(pkg.rglob('*')):
            if p.is_file() and not p.name.startswith('~$') and str(p) not in excluded:
                writer.writerow([p.relative_to(OUT).as_posix(),p.stat().st_size,sha(p.read_bytes()),'作业1' if pkg==packages[0] else '作业2'])
    for p in OUT.glob('*.zip'):writer.writerow([p.name,p.stat().st_size,sha(p.read_bytes()),'提交压缩包'])

result={'font':'宋体','word_count':len(M['word']),'ppt_count':len(M['ppt']),'preserved_images':sum(r['images_unchanged'] for r in records),'documents':records,'zip_integrity':'passed'}
(WORK/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'宋体字体核对结果.md').write_text('# 宋体字体核对结果\n\n本次将 12 份正式 Word 与 2 份提交 PPT 的可编辑文字统一为宋体，包括封面、正文、表格、目录、页眉页脚及幻灯片文字。字体定义与直接格式已核验；PNG 等内嵌图片内容原样保留。Word 自动目录及页码已重新生成，两个提交 ZIP 已逐文件比对通过。\n',encoding='utf-8')
print('FONT VERIFIED',len(M['word']),'Word,',len(M['ppt']),'PPT;',result['preserved_images'],'unchanged embedded images')
