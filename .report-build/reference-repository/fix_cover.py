from pathlib import Path
from docx import Document
import json,shutil,os,hashlib

BUILD=Path(__file__).resolve().parent
ROOT=BUILD.parents[1]
OUT=ROOT/'Submit'
WORK=BUILD/'cover-fix'
WORK.mkdir(exist_ok=True)
paths=json.loads((BUILD/'outputs.json').read_text(encoding='utf-8'))
manifest=json.loads((BUILD/'manifest.json').read_text(encoding='utf-8'))
changed=[];redirects={};before={}
for p in map(Path,paths):
    d=Document(p)
    original_text=d._element.body.xpath('.//w:t/text()')
    before[str(p)]=original_text
    backup=WORK/'before'/p.relative_to(OUT)
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(p,backup)
    for paragraph in d.paragraphs:
        if paragraph._p.xpath('.//w:br[@w:type="page"]'):break
        paragraph.paragraph_format.line_spacing=1.2
    for style in ['Title','Heading 1','Heading 2','Heading 3']:
        d.styles[style].paragraph_format.line_spacing=1.2
    assert d._element.body.xpath('.//w:t/text()')==original_text
    tmp=WORK/p.name;d.save(tmp)
    try:
        os.replace(tmp,p)
        target=p
    except PermissionError:
        target=p.with_name(p.name.replace('_v2.0-','_v2.0_封面修正版-'))
        os.replace(tmp,target)
        redirects[str(p)]=str(target)
    changed.append(str(target))
    print('COVER FIXED',target.name)

# Save actual paths for rendering and packaging, including the separate corrected file if open.
(WORK/'outputs.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'redirects.json').write_text(json.dumps(redirects,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'before_text.json').write_text(json.dumps(before,ensure_ascii=False),encoding='utf-8')
(BUILD/'outputs.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding='utf-8')
for pair in manifest['word_sources']:
    if pair[1] in redirects:pair[1]=redirects[pair[1]]
(BUILD/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
if redirects:
    readme=OUT/'README.md';text=readme.read_text(encoding='utf-8')
    for old,new in redirects.items():text=text.replace(Path(old).name,Path(new).name)
    readme.write_text(text,encoding='utf-8')

# Keep the authoring helper consistent so another build cannot inherit the faulty cover spacing.
for filename in ['authoring.py','restructure.py']:
    p=BUILD/filename;t=p.read_text(encoding='utf-8')
    marker='    # Prepend front matter inside the same OPC package, preserving all body image relationships.'
    # Set the dedicated front matter paragraphs after insertion; body prose keeps its reference spacing.
    anchor="    update=OxmlElement('w:updateFields')"
    addition="    for cover_p in d.paragraphs:\n        if cover_p._p.xpath('.//w:br[@w:type=\"page\"]'):break\n        cover_p.paragraph_format.line_spacing=1.2\n    for cover_style in ['Title','Heading 1','Heading 2','Heading 3']:\n        d.styles[cover_style].paragraph_format.line_spacing=1.2\n"
    if 'for cover_p in d.paragraphs:' not in t:t=t.replace(anchor,addition+anchor)
    p.write_text(t,encoding='utf-8')
print('OPEN-FILE REDIRECTS',json.dumps(redirects,ensure_ascii=False))
