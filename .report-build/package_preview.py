from pathlib import Path
import json
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from reportlab.pdfgen import canvas
from pypdf import PdfReader

root=Path.cwd(); out=root/'汇报成果'; build=root/'.report-build'
images=sorted((build/'final-renders').glob('slide-*.png'))
assert len(images)==28
meta=json.loads((build/'meta.json').read_text(encoding='utf-8'))
assert len(meta)==28 and sum(s['duration'] for s in meta)==900
file=out/'学术成果分享平台_总体汇报_预览.pdf'
c=canvas.Canvas(str(file),pagesize=(960,540))
c.setTitle('学术成果分享平台：需求调研与建模总体汇报')
for image in images:
    c.drawImage(str(image),0,0,width=960,height=540)
    c.showPage()
c.save()
assert len(PdfReader(file).pages)==28
with ZipFile(out/'学术成果分享平台_需求调研与建模_总体汇报.pptx') as z:
    slides=[n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
    notes=[n for n in z.namelist() if n.startswith('ppt/notesSlides/notesSlide') and n.endswith('.xml')]
    assert len(slides)==28 and len(notes)==28
    texts='\n'.join(''.join(ET.fromstring(z.read(n)).itertext()) for n in slides)
    for text in ['科研项目','待补充','重试','SRS','SPEC','P95']:
        assert text in texts, text
print('Checks passed: 28 slides, 28 speaker notes, 900 seconds, 28 PDF pages')
