from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
p=Path('.report-build/seminar')
files=sorted(p.glob('page-*.png'))
thumbs=[]
for f in files:
 im=Image.open(f).convert('RGB'); im.thumbnail((306,396)); canvas=Image.new('RGB',(320,424),'white'); canvas.paste(im,((320-im.width)//2,10)); ImageDraw.Draw(canvas).text((8,402),f.stem,fill='black'); thumbs.append(canvas)
for start in range(0,len(thumbs),9):
 batch=thumbs[start:start+9]; sheet=Image.new('RGB',(320*3,424*3),(220,225,230))
 for j,im in enumerate(batch): sheet.paste(im,((j%3)*320,(j//3)*424))
 sheet.save(p/f'contact-{start//9+1}.png')
