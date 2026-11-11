from pathlib import Path
from PIL import Image,ImageDraw
names=['01_科研人员用例图.drawio.png','普通用户用例图.drawio.png','普通用户活动图.drawio.png','作者检索详细活动图.drawio.png','02_现状调研活动图.drawio.png','03_门户认领活动图.drawio.png','04_认领申请状态图.drawio.png','学术成果分享平台_数据采集任务状态图.drawio.png']
p=Path('images'); cards=[]
for n in names:
 im=Image.open(p/n).convert('RGB'); print(n, im.size)
 im.thumbnail((550,400)); c=Image.new('RGB',(570,440),'white'); c.paste(im,((570-im.width)//2,8)); ImageDraw.Draw(c).text((8,416),n,fill='black'); cards.append(c)
sh=Image.new('RGB',(570*2,440*4),(220,225,230))
for i,c in enumerate(cards): sh.paste(c,((i%2)*570,(i//2)*440))
sh.save('.report-build/seminar/models.png')
