from pathlib import Path
import zipfile, re, json, hashlib
from lxml import etree
root=Path(r'F:\homework\软分\SoftwareAnalyse')
b=root/'.report-build/topic-ppt'
src=root/'需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-需求分析汇报-差异集中版.pptx'
authored=b/'notes-authored-r06.pptx'
target=b/'main-r06.pptx'
speeches=json.loads((b/'speeches-r06.json').read_text(encoding='utf-8'))
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
changed=[]
with zipfile.ZipFile(src) as old, zipfile.ZipFile(authored) as new, zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
    for info in old.infolist():
        data=old.read(info.filename)
        match=re.fullmatch(r'ppt/notesSlides/notesSlide(\d+)\.xml',info.filename)
        if match:
            page=int(match[1])
            original=etree.fromstring(data)
            updated=etree.fromstring(new.read(info.filename))
            original_body=original.xpath('//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody',namespaces=ns)
            new_body=updated.xpath('//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody',namespaces=ns)
            assert len(original_body)==len(new_body)==1
            note_text='\n'.join(new_body[0].xpath('.//a:t/text()',namespaces=ns))
            assert all(part in note_text for part in speeches[page-1]['speech'].split('\n\n'))
            original_body[0].getparent().replace(original_body[0],new_body[0])
            data=etree.tostring(original,encoding='UTF-8',xml_declaration=True,standalone=True)
            changed.append(info.filename)
        out.writestr(info,data)
assert len(changed)==13
with zipfile.ZipFile(src) as old, zipfile.ZipFile(target) as new:
    assert set(old.namelist())==set(new.namelist())
    differences=[n for n in old.namelist() if old.read(n)!=new.read(n)]
    assert sorted(differences)==sorted(changed)
(b/'notes-audit-r06.json').write_text(json.dumps({'notesChanged':changed,'allOtherPartsByteIdentical':True,'sourceSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'draftSha256':hashlib.sha256(target.read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
print('Updated 13 speaker notes; all other PPTX parts are byte-identical to the approved source.')
