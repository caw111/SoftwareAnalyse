from pathlib import Path
from pdf2image import convert_from_path
from pypdf import PdfReader
from PIL import Image,ImageDraw,ImageFont
import json,sys
build=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
records=[]
previous=json.loads((build/'qa/pages.json').read_text(encoding='utf-8')) if (build/'qa/pages.json').exists() else []
current={Path(f).stem for f in json.loads((build/'outputs.json').read_text(encoding='utf-8'))}
for fi,f in enumerate(sorted(f for f in (build/'qa').glob('*.pdf') if f.stem in current),1):
    if '--final-layout' in sys.argv and not any(k in f.name for k in ['SRS','SPEC','修改说明','自查清单']):
        records.append(next(r for r in previous if r['file']==f.name));continue
    pages=convert_from_path(str(f),dpi=120,poppler_path='C:/Users/27872/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
    folder=build/'qa'/f'{fi:02d}-pages';folder.mkdir(exist_ok=True)
    reader=PdfReader(f)
    texts=[]
    for pi,im in enumerate(pages,1):
        im.save(folder/f'page-{pi}.png')
        text=reader.pages[pi-1].extract_text();texts.append(text)
        if len(text)<100:print('SPARSE',f.name,pi,len(text))
    (folder/'text.txt').write_text('\n\n'.join(texts),encoding='utf-8')
    for start in range(0,len(pages),6):
        w=650;h=950;sheet=Image.new('RGB',(w*3,h*2),'#ccd0d5');draw=ImageDraw.Draw(sheet)
        for j,im in enumerate(pages[start:start+6]):
            im=im.copy();im.thumbnail((w-12,h-35))
            x=(j%3)*w;y=(j//3)*h;sheet.paste(im,(x+6,y+30))
            draw.text((x+8,y+3),f'{fi:02d} / page {start+j+1}',font=font,fill='black')
        sheet.save(build/'qa'/f'sheet-{fi:02d}-{start//6+1:02d}.jpg',quality=94)
    records.append({'file':f.name,'pages':len(pages),'id':fi})
(build/'qa'/'pages.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(records,ensure_ascii=False))
