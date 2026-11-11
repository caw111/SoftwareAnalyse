from pathlib import Path
import json, hashlib, re, shutil, zipfile
import xml.etree.ElementTree as ET

root=Path(r'F:\homework\软分\SoftwareAnalyse')
build=root/'.report-build/topic-ppt'
source=root/'需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-需求分析汇报.pptx'
candidate=build/'validated-r05/main.pptx'
receipt=json.loads((build/'receipt-main-r05.json').read_text(encoding='utf-8-sig'))
digest=hashlib.sha256(candidate.read_bytes()).hexdigest()
assert digest==receipt['finalSha256']
assert hashlib.sha256(source.read_bytes()).hexdigest()=='ce10a06f0df128f85a681264d09f77dffc15a0591e634c58059e69ca5b8213eb'
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(candidate) as z, zipfile.ZipFile(source) as old:
    slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
    assert len(slides)==13
    for i in range(1,14):
        name=f'ppt/slides/slide{i}.xml'
        xml=ET.fromstring(z.read(name))
        text='\n'.join(t.text or '' for t in xml.findall('.//a:t',ns))
        assert len(xml.findall('.//a:tbl',ns))==1
        assert not any(t in text for t in ['用时','分钟','制作备注','讲解时长'])
        if i<=10:
            assert not re.search('1组|2组|两组|Group2',text), f'comparison remains on slide {i}'
            current_tables=[[t.text for t in x.findall('.//a:t',ns)] for x in xml.findall('.//a:tbl',ns)]
            old_xml=ET.fromstring(old.read(name))
            previous_tables=[[t.text for t in x.findall('.//a:t',ns)] for x in old_xml.findall('.//a:tbl',ns)]
            assert current_tables==previous_tables, f'business table changed on slide {i}'
        else:
            assert '1组表达' in text and '2组表达' in text
for i in list(range(1,12))+[13]:
    fn=f'slide-{i:02d}.png'
    assert hashlib.sha256((build/'r04'/fn).read_bytes()).digest()==hashlib.sha256((build/'r05'/fn).read_bytes()).digest()
output=source.parent/'学术成果分享平台-需求分析汇报-差异集中版.pptx'
assert not output.exists(), 'New deliverable already exists'
shutil.copyfile(candidate,output)
assert hashlib.sha256(output.read_bytes()).hexdigest()==digest
content=(build/'content-r05.md').read_text(encoding='utf-8')
content=re.sub(r'(?m)^(\| 对照项 \|[^\n]*\|)$',r'\1\n| --- | --- | --- | --- |',content)
manuscript=root/'需求分析/PPT主题汇报稿/PPT逐页内容-差异集中版.md'
manuscript.write_text(content,encoding='utf-8')
audit={'revision':'r05','output':str(output),'sha256':digest,'slides':13,'comparisonSlides':[11,12,13],'originalBusinessTablesPreserved':True,'firstTenSlidesHaveNoGroupComparison':True,'sourceUnchanged':True,'visualReview':'r04 all 13 slides reviewed independently. r05 only slide 12 changed and was reviewed independently and in native PowerPoint rendering. Original ten slides and all three comparison slides inspected after native PowerPoint export.','layoutWarningResolution':'Slide 2 table estimate warning checked against native rendering: no overlap or clipping.'}
(build/'delivery-audit-r05.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False,indent=2))
