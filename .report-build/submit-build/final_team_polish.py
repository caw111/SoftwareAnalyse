from pathlib import Path
from docx import Document
from docx.shared import Cm
root=Path(__file__).resolve().parents[2]
out=root/'Submit'
for p in out.rglob('*.md'):
    if '归档_' in str(p):continue
    text=p.read_text(encoding='utf-8').replace('组号、团队名、成员分工、课堂反馈','成员分工、课堂反馈')
    p.write_text(text,encoding='utf-8')
f=next((out/'作业2_需求建模成果').glob('01-SRS*.docx'))
d=Document(f)
if not d.inline_shapes:
    for i,p in enumerate(d.paragraphs):
        if p.text.startswith(('13.1 统计分析模块','13.2 成果管理模块')):
            stem='统计分析模块_UML用例图' if p.text.startswith('13.1') else '成果管理模块_UML用例图'
            img=next((out/'作业2_需求建模成果'/'03-建模图'/'模型截图').glob('*-'+stem+'-9组-1011101011.png'))
            picture=d.paragraphs[i+1].add_run().add_picture(str(img),width=Cm(16.7))
            picture._inline.docPr.set('descr',stem)
    assert len(d.inline_shapes)==2
    d.save(f)
for f in out.rglob('*.docx'):
    if '归档_' in str(f) or '原始调研材料' in str(f):continue
    d=Document(f);d.core_properties.author='9组 1011101011';d.save(f)
print('Final team metadata and two SRS figures verified')
