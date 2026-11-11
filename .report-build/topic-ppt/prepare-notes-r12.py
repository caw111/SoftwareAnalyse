from pathlib import Path
import zipfile,json,hashlib,re
from lxml import etree
root=Path(r'F:\homework\软分\SoftwareAnalyse')
b=root/'.report-build/topic-ppt'
source=root/'需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-图解汇报版.pptx'
authored=b/'notes-authored-r12.pptx'
candidate=b/'main-r12.pptx'
scripts=json.loads((b/'speeches-diagram.json').read_text(encoding='utf-8'))
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
changed=[]
with zipfile.ZipFile(source) as src,zipfile.ZipFile(authored) as notes,zipfile.ZipFile(candidate,'w',zipfile.ZIP_DEFLATED) as dst:
    for info in src.infolist():
        data=src.read(info.filename)
        match=re.fullmatch(r'ppt/notesSlides/notesSlide(\d+)\.xml',info.filename)
        if match:
            page=int(match[1]);old=etree.fromstring(data);new=etree.fromstring(notes.read(info.filename))
            body='//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody'
            a=old.xpath(body,namespaces=ns);d=new.xpath(body,namespaces=ns)
            assert len(a)==len(d)==1
            words='\n'.join(d[0].xpath('.//a:t/text()',namespaces=ns))
            assert f'第{page}页' in words and all(t in words for t in scripts[page-1]['speech'].split('\n\n'))
            a[0].getparent().replace(a[0],d[0]);data=etree.tostring(old,encoding='UTF-8',xml_declaration=True,standalone=True)
            changed.append(info.filename)
        dst.writestr(info,data)
assert len(changed)==13
with zipfile.ZipFile(source) as a,zipfile.ZipFile(candidate) as c:
    assert set(a.namelist())==set(c.namelist())
    assert sorted(n for n in a.namelist() if a.read(n)!=c.read(n))==sorted(changed)
(b/'notes-audit-r12.json').write_text(json.dumps({'notesChanged':13,'allSlideImageAndLayoutPartsUnchanged':True,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
print('All 13 notes updated; images and layouts are unchanged.')
