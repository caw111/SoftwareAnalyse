from pathlib import Path
from pdf2image import convert_from_path
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont
import json
build=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
records=[]
current={Path(f).stem for f in json.loads((build/'docx_outputs.json').read_text(encoding='utf-8'))}
for fi,f in enumerate(sorted(f for f in (build/'qa').glob('*.pdf') if f.stem in current),1):
    images=convert_from_path(str(f),dpi=90,poppler_path='C:/Users/27872/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
    folder=build/'qa'/f'{fi:02d}-pages';folder.mkdir(exist_ok=True)
    reader=PdfReader(f)
    for pi,im in enumerate(images,1):
        im.save(folder/f'page-{pi}.png')
        text=reader.pages[pi-1].extract_text()
        if len(text)<100:print('SPARSE',f.name,pi,len(text))
    # Full rendering of every page, with overview sheets for layout comparison.
    for start in range(0,len(images),6):
        group=images[start:start+6];w=560;h=815
        sheet=Image.new('RGB',(w*3,h*2),'#ccd0d5');draw=ImageDraw.Draw(sheet)
        for j,im in enumerate(group):
            im=im.copy();im.thumbnail((w-12,h-33))
            x=(j%3)*w;y=(j//3)*h
            sheet.paste(im,(x+6,y+28));draw.text((x+8,y+3),f'{fi:02d} / page {start+j+1}',font=font,fill='black')
        p=build/'qa'/f'sheet-{fi:02d}-{start//6+1:02d}.jpg';sheet.save(p,quality=92)
    records.append({'file':f.name,'pages':len(images),'id':fi})
(build/'qa'/'pages.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(records,ensure_ascii=False))
