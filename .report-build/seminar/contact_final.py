from pathlib import Path
from PIL import Image, ImageDraw
p=Path('.report-build/seminar'); fs=sorted(p.glob('page-final-*.png')); ts=[]
for f in fs:
 im=Image.open(f).convert('RGB'); im.thumbnail((306,396)); c=Image.new('RGB',(320,424),'white'); c.paste(im,((320-im.width)//2,10)); ImageDraw.Draw(c).text((8,402),f.stem,fill='black'); ts.append(c)
for batchno,start in enumerate(range(0,len(ts),9),1):
 sh=Image.new('RGB',(960,1272),(220,225,230))
 for j,x in enumerate(ts[start:start+9]): sh.paste(x,((j%3)*320,(j//3)*424))
 sh.save(p/f'contact-final-{batchno}.png')
print('pages',len(fs))
