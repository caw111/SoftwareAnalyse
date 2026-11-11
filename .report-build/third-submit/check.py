from pathlib import Path
import json,re,hashlib,zipfile,subprocess
from PIL import Image,ImageOps,ImageDraw
R=Path.cwd();O=R/'Submit/第9组-第三次作业-需求分析';B=R/'.report-build/third-submit';D=B/'render-native';D.mkdir(exist_ok=True)
from pypdf import PdfReader
pdf=PdfReader(O/'01-需求分析报告.pdf');stats=[]
for i,p in enumerate(pdf.pages):
 txt=p.extract_text();stats.append({'page':i+1,'chars':len(txt),'first':txt[:120]})
imgs=sorted((B/'render').glob('page-*.png'))
for start in range(0,len(imgs),6):
 canvas=Image.new('RGB',(1500,1440),'#d0d0d0');draw=ImageDraw.Draw(canvas)
 for j in range(6):
  if start+j>=len(imgs):break
  im=Image.open(imgs[start+j]);im.thumbnail((490,680))
  x=(j%3)*500;y=(j//3)*720;canvas.paste(im,(x,y+30));draw.text((x+12,y+5),str(start+j+1),fill='black')
 canvas.save(D/f'contact-{start//6+1}.png')
(B/'pdf-pages.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'pages':len(pdf.pages),'sparse':[x for x in stats if x['chars']<80]},ensure_ascii=False))
z=zipfile.ZipFile(R/'需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-图解汇报版-含逐页演讲稿.pptx')
print(set(v for n in z.namelist() if n.endswith('.xml') for v in re.findall(r'typeface="([^"]+)',z.read(n).decode())))
