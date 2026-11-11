from pathlib import Path
import hashlib, json, zipfile, re, shutil
from lxml import etree
root=Path(r'F:\homework\软分\SoftwareAnalyse')
b=root/'.report-build/topic-ppt'
folder=root/'需求分析/PPT主题汇报稿'
source=folder/'演示文稿/学术成果分享平台-需求分析汇报-差异集中版.pptx'
validated=b/'validated-r06/main.pptx'
receipt=json.loads((b/'receipt-main-r06.json').read_text(encoding='utf-8-sig'))
digest=hashlib.sha256(validated.read_bytes()).hexdigest()
assert digest==receipt['finalSha256']
scripts=json.loads((b/'speeches-r06.json').read_text(encoding='utf-8'))
with zipfile.ZipFile(source) as old, zipfile.ZipFile(validated) as new:
    changed=[n for n in old.namelist() if old.read(n)!=new.read(n)]
    assert len(changed)==13 and all(re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n) for n in changed)
    for page,script in enumerate(scripts,1):
        xml=etree.fromstring(new.read(f'ppt/notesSlides/notesSlide{page}.xml'))
        text='\n'.join(xml.xpath('//*[local-name()="t"]/text()'))
        assert all(p in text for p in script['speech'].split('\n\n'))
deck=folder/'演示文稿/学术成果分享平台-需求分析汇报-差异集中版-含演讲稿.pptx'
manuscript=folder/'逐页演讲稿-12分钟内.md'
assert not deck.exists() and not manuscript.exists()
shutil.copyfile(validated,deck)
shutil.copyfile(b/'speech-manuscript-r06.md',manuscript)
assert hashlib.sha256(deck.read_bytes()).hexdigest()==digest
audit={'deck':str(deck),'manuscript':str(manuscript),'sha256':digest,'scripts':13,'spokenCharacters':2225,'estimatedMinutesAt220CharsPerMin':2225/220,'transitionAllowanceMinutes':1,'visibleSlidesUnchanged':True,'allNativeNotesReadableInPowerPoint':True,'independentScriptReview':'passed'}
(b/'delivery-audit-r06.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False,indent=2))
