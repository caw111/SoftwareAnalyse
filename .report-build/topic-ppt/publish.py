from pathlib import Path
import hashlib, json, re, shutil, zipfile
import xml.etree.ElementTree as ET

root = Path(r'F:\homework\软分\SoftwareAnalyse')
build = root / '.report-build/topic-ppt'
dest = root / '需求分析/PPT主题汇报稿/演示文稿'
trace = json.loads((build / 'build-trace-r03.json').read_text(encoding='utf-8-sig'))
audit = {'revision': 'r03', 'outputs': [], 'visualReview': 'All 10 main slides inspected in native PowerPoint PDF rendering; all 17 atlas slides inspected in Artifact Tool rendering. Independent visual QA completed.', 'layoutWarningResolution': 'Slide 2 estimated native table overflow warning resolved by inspecting native PowerPoint rendering: table ends above group mapping footnote, no overlap or clipping.'}
for key, name, count in [('main', '学术成果分享平台-需求分析汇报.pptx', 10), ('atlas', '完整模型图册-备查.pptx', 17)]:
    src = build / 'validated-r03' / f'{key}.pptx'
    receipt = json.loads((build / f'receipt-{key}-r03.json').read_text(encoding='utf-8-sig'))
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    assert digest == receipt['finalSha256']
    with zipfile.ZipFile(src) as z:
        slides = [n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
        assert len(slides) == count
        ns = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
        tables = sum(len(ET.fromstring(z.read(n)).findall('.//a:tbl',ns)) for n in slides)
        if key == 'main':
            assert tables == 10
            text = '\n'.join(t.text or '' for n in slides for t in ET.fromstring(z.read(n)).findall('.//a:t',ns))
            assert not any(t in text for t in ['用时', '分钟', '制作备注', '讲解时长'])
        else:
            media = {hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('ppt/media/')}
            assert all(f['sha256'] in media for f in trace['figures'])
    target = dest / name
    if target.exists():
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'Refusing to replace different existing file'
    else:
        shutil.copyfile(src, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    audit['outputs'].append({'path': str(target), 'slides': count, 'sha256': digest, 'bytes':target.stat().st_size, 'nativeTables':tables})
(build / 'delivery-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False,indent=2))
