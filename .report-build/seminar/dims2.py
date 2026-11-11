from pathlib import Path
from PIL import Image
p=Path('需求分析/A组-需求分析整合版-v1.1/图件')
for n in ['02-核心业务类图.png','03-采集入库时序图.png','05-门户认领审核时序图.png','06-检索请求处理时序图.png']:
 im=Image.open(p/n); print(n, im.size, round(im.height/im.width,2))
