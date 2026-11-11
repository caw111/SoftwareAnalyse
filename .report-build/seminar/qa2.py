from pathlib import Path
from PIL import Image,ImageDraw
from pypdf import PdfReader
p=Path('.report-build/seminar'); fs=sorted(p.glob('final2-*.png')); cards=[]
for f in fs:
 im=Image.open(f).convert('RGB'); im.thumbnail((306,396)); c=Image.new('RGB',(320,424),'white'); c.paste(im,((320-im.width)//2,10)); ImageDraw.Draw(c).text((8,402),f.stem,fill='black'); cards.append(c)
for bn,start in enumerate(range(0,len(cards),9),1):
 sh=Image.new('RGB',(960,1272),(220,225,230))
 for j,c in enumerate(cards[start:start+9]): sh.paste(c,((j%3)*320,(j//3)*424))
 sh.save(p/f'contact-final2-{bn}.png')
pdf=PdfReader('汇报成果/需求实践与分析成果研讨/01-研讨报告.pdf'); print('pages',len(pdf.pages),'rendered',len(fs),'per_page_chars',[len(x.extract_text() or '') for x in pdf.pages])
