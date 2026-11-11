from pathlib import Path
from PIL import Image, ImageDraw
from pypdf import PdfReader
p=Path('.report-build/seminar'); fs=sorted(p.glob('page-recheck-*.png')); ts=[]
for f in fs:
 im=Image.open(f).convert('RGB'); im.thumbnail((306,396)); c=Image.new('RGB',(320,424),'white'); c.paste(im,((320-im.width)//2,10)); ImageDraw.Draw(c).text((8,402),f.stem,fill='black'); ts.append(c)
for batchno,start in enumerate(range(0,len(ts),9),1):
 sh=Image.new('RGB',(960,1272),(220,225,230))
 for j,x in enumerate(ts[start:start+9]): sh.paste(x,((j%3)*320,(j//3)*424))
 sh.save(p/f'contact-recheck-{batchno}.png')
pdf=PdfReader('汇报成果/需求实践与分析成果研讨/01-研讨报告.pdf')
text='\n'.join(page.extract_text() or '' for page in pdf.pages)
print('pages:',len(pdf.pages),'textchars:',len(text),'replacement glyphs:',text.count('\ufffd'))
for term in ['本组提交中没有A组自己绘制','DQ-02','PER-01','附录D 核心业务类图','AI辅助内容']:
 print(term,term in text)
print('page text lengths:',[len(pg.extract_text() or '') for pg in pdf.pages])
