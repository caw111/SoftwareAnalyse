from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
from pypdf import PdfReader
p=Path('.report-build/a1/render')
files=sorted(p.glob('page-*.png'))
for k in range(0,len(files),3):
 imgs=[Image.open(f).convert('RGB') for f in files[k:k+3]]
 out=Image.new('RGB',(sum(i.width for i in imgs),max(i.height for i in imgs)+30),'#dddddd');x=0
 for f,im in zip(files[k:k+3],imgs):out.paste(im,(x,30));ImageDraw.Draw(out).text((x+10,8),f.name,fill='black');x+=im.width
 out.save(p/f'sheet-{k//3+1}.png')
d=PdfReader(p/'report.pdf')
for i,page in enumerate(d.pages):
 t=page.extract_text();print(i+1,len(t),t[:65].replace('\n',' '),t[-65:].replace('\n',' '))
