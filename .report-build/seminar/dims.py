from PIL import Image
from pathlib import Path
for f in Path('汇报成果/需求实践与分析成果研讨/图件').glob('*'):
 im=Image.open(f); print(f.name, im.size, round(im.height/im.width,2))
