from pathlib import Path
from lxml import etree as E
import json,zipfile,shutil,os,hashlib

BUILD=Path(__file__).resolve().parent
ROOT=BUILD.parents[1]
OUT=ROOT/'Submit'
WORK=BUILD/'songti';WORK.mkdir(exist_ok=True)
FONT='宋体'
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
manifest=json.loads((BUILD/'manifest.json').read_text(encoding='utf-8'))
packages=list(map(Path,manifest['packages']))
paths=[p for pkg in packages for p in sorted(pkg.rglob('*')) if p.suffix in ['.docx','.pptx'] and not p.name.startswith('~$')]
changed=[];redirects={};snapshots={}

def apply_font(data,kind):
    r=E.fromstring(data)
    if kind=='docx':
        for run in list(r.iter(W+'r')):
            if not list(run.iter(W+'t')):continue
            pr=run.find(W+'rPr')
            if pr is None:pr=E.Element(W+'rPr');run.insert(0,pr)
        for pr in list(r.iter(W+'rPr')):
            rf=pr.find(W+'rFonts')
            if rf is None:rf=E.Element(W+'rFonts');pr.insert(0,rf)
        for rf in r.iter(W+'rFonts'):
            for key in list(rf.attrib):
                if key.rsplit('}',1)[-1].lower().endswith('theme'):del rf.attrib[key]
            for key in ['ascii','hAnsi','eastAsia','cs']:rf.set(W+key,FONT)
        for e in r.iter(W+'lvlText'):
            s=e.get(W+'val','')
            s=s.replace('\uf0b7','•').replace('\uf0a7','▪').replace('\uf06f','○')
            e.set(W+'val',s)
        for e in r.iter(W+'sym'):
            e.set(W+'font',FONT)
    # Drawing text, theme fonts, charts, slide masters and slide notes.
    for el in list(r.iter()):
        if el.tag in [A+'latin',A+'ea',A+'cs',A+'font',A+'buFont']:el.set('typeface',FONT)
        if el.tag in [A+'rPr',A+'defRPr',A+'endParaRPr']:
            for tag in ['latin','ea','cs']:
                f=el.find(A+tag)
                if f is None:f=E.SubElement(el,A+tag)
                f.set('typeface',FONT)
    return E.tostring(r,xml_declaration=True,encoding='UTF-8',standalone=True)

for p in paths:
    kind=p.suffix[1:];backup=WORK/'before'/p.relative_to(OUT)
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup)
    temp=WORK/('temp-'+p.name)
    text=[];media={}
    with zipfile.ZipFile(p) as src,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data=src.read(info.filename)
            if '/media/' in info.filename:media[info.filename]=hashlib.sha256(data).hexdigest()
            if info.filename.endswith('.xml') and info.filename.startswith(('word/','ppt/')):
                old=E.fromstring(data)
                text.extend(old.xpath('//*[local-name()="t"]/text()'))
                updated=apply_font(data,kind)
                assert E.fromstring(updated).xpath('//*[local-name()="t"]/text()')==old.xpath('//*[local-name()="t"]/text()')
                data=updated
            dst.writestr(info,data)
    target=p
    try:os.replace(temp,p)
    except PermissionError:
        target=p.with_name(p.stem.replace('_封面修正版','')+'_宋体版'+p.suffix)
        os.replace(temp,target);redirects[str(p)]=str(target)
    snapshots[str(target)]={'media':media,'text':text,'source':str(p),'backup':str(backup)}
    changed.append(target);print('SONGTI',target.name)

# Refresh current paths; users may have renamed the earlier cover correction to the original name.
wordpaths=[str(p) for p in changed if p.suffix=='.docx']
(BUILD/'outputs.json').write_text(json.dumps(wordpaths,ensure_ascii=False,indent=2),encoding='utf-8')
for pair in manifest['word_sources']:
    original=Path(pair[1])
    if not original.exists():
        stem=original.name.split('_v2.0')[0]
        choices=[p for p in changed if p.suffix=='.docx' and p.parent==original.parent and p.name.startswith(stem)]
        if len(choices)==1:pair[1]=str(choices[0])
    elif str(original) in redirects:pair[1]=redirects[str(original)]
(BUILD/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(BUILD/'cover-fix/redirects.json').write_text(json.dumps(redirects,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'manifest.json').write_text(json.dumps({'word':wordpaths,'ppt':[str(p) for p in changed if p.suffix=='.pptx'],'snapshots':snapshots,'redirects':redirects},ensure_ascii=False,indent=2),encoding='utf-8')

for p in [OUT/'README.md',packages[1]/'00-阅读说明.md']:
    if not p.exists():continue
    s=p.read_text(encoding='utf-8')
    for old,new in redirects.items():s=s.replace(Path(old).name,Path(new).name)
    # Earlier corrected name might no longer exist after a user rename.
    src=next(Path(pair[1]) for pair in manifest['word_sources'] if Path(pair[1]).name.startswith('01-SRS'))
    s=s.replace('01-SRS_v2.0_封面修正版-9组-1011101011.docx',src.name)
    if p.name=='00-阅读说明.md':s='# 正式文档\n\n当前正式 SRS 为 [SRS 宋体版本]('+src.name+')。提交 Word 和 PPT 的可编辑文字已统一为宋体，图片保留原样。\n'
    p.write_text(s,encoding='utf-8')

# Future authoring follows the latest font request.
for p in [BUILD/'authoring.py',BUILD/'restructure.py']:
    s=p.read_text(encoding='utf-8').replace("'Times New Roman'","'宋体'").replace("'黑体'","'宋体'")
    p.write_text(s,encoding='utf-8')
print('COMPLETE',len(wordpaths),'Word;',len(changed)-len(wordpaths),'PowerPoint')
