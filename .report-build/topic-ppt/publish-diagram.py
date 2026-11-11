from pathlib import Path
import hashlib,json,zipfile,re,shutil
from lxml import etree
root=Path(r'F:\homework\软分\SoftwareAnalyse')
b=root/'.report-build/topic-ppt'
folder=root/'需求分析/PPT主题汇报稿'
source=folder/'演示文稿/学术成果分享平台.pptx'
deck=b/'validated-r11/main.pptx'
receipt=json.loads((b/'receipt-main-r11.json').read_text(encoding='utf-8-sig'))
figures=json.loads((b/'figures-r11.json').read_text(encoding='utf-8'))
speeches=json.loads((b/'speeches-diagram.json').read_text(encoding='utf-8'))
sha=hashlib.sha256(deck.read_bytes()).hexdigest()
assert sha==receipt['finalSha256']
assert hashlib.sha256(source.read_bytes()).hexdigest()=='83c1e5146a0f7d995d858c6a1c73250fe7c19273deb9df4047da6209c846db8d'
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
assert len(figures)==29
assert all(v['group']=='1组' for v in figures if v['slide']<=10)
assert sorted({v['slide'] for v in figures})==list(range(2,14))
for fig in figures:
    assert hashlib.sha256(Path(fig['file']).read_bytes()).hexdigest()==fig['sha256']
with zipfile.ZipFile(deck) as z:
    slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
    assert len(slides)==13
    media={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('ppt/media/')}
    assert all(v['sha256'] in media for v in figures if v.get('kind')!='original-svg-focus')
    pics=0
    for i in range(1,14):
        xml=etree.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
        assert not xml.findall('.//a:tbl',ns)
        pics+=len(xml.findall('.//p:pic',ns))
        visible='\n'.join(xml.xpath('.//a:t/text()',namespaces=ns))
        assert not re.search('分钟|用时|讲解时长|制作备注',visible)
        if i<=10:assert not re.search('1组|2组|两组|Group2',visible)
        notes=etree.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml'))
        note_text='\n'.join(notes.xpath('.//a:t/text()',namespaces=ns))
        assert all(x in note_text for x in speeches[i-1]['speech'].split('\n\n'))
    assert pics==29
target=folder/'演示文稿/学术成果分享平台-图解汇报版.pptx'
manuscript=folder/'逐页演讲稿-图解版-12分钟内.md'
assert not target.exists() and not manuscript.exists()
shutil.copyfile(deck,target)
shutil.copyfile(b/'speech-r11.md',manuscript)
assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
figure_doc='# 图解版图件对应说明\n\n主讲版共13页，不含概括表格。第2至13页使用原有PNG或SVG图件的关键局部；完整原图、SVG和可编辑模型源仍保留在原目录。\n\n'
for i in range(1,14):
    figure_doc+=f'## 第{i}页 {speeches[i-1]["title"]}\n\n'
    unique=list(dict.fromkeys((v['group'],v['name'],v.get('kind','original-png-crop')) for v in figures if v['slide']==i))
    if not unique:figure_doc+='需求范围与业务链概述，使用简短文字。\n\n'
    for group,name,kind in unique:
        suffix='svg' if kind=='original-svg-focus' else 'png'
        figure_doc+=f'- [{group}：{name}](图件/{group}/{name}.{suffix})'+('：仅在原SVG中保留相关完整类框及原连线。' if suffix=='svg' else '：保留原图内容，通过PPT裁剪放大。')+'\n'
    figure_doc+='\n'
figure_doc+='两组来源按原件保留。第7页对原图换行的APPROVED额外提供完整文字说明；第10、12、13页补充局部消息对应的参与者名称。\n'
(folder/'图解版图件对应说明.md').write_text(figure_doc,encoding='utf-8')
audit={'revision':'r11','output':str(target),'speech':str(manuscript),'sha256':sha,'slides':13,'nativeTables':0,'originalFigurePlacements':pics,'figureSlides':12,'sourcePngBytesPreserved':True,'sourcePptUnchanged':True,'spokenCharacters':2276,'estimatedMinutesAt220Plus1MinPauses':2276/220+1,'nativePowerPointOpenedAndRendered':True,'visualReview':'All source diagrams inspected; independent r09 review identified readability/crop/actor issues. Root repaired and visually verified final r11 native rendering. Agent follow-up unavailable; no claim of final independent approval.'}
(b/'delivery-audit-r11.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False,indent=2))
