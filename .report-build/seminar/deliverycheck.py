from zipfile import ZipFile
from pathlib import Path
from pypdf import PdfReader
z=Path('Submit/第9组-需求实践与分析成果研讨.zip')
with ZipFile(z) as f:
 assert f.testzip() is None
 names=f.namelist()
 print('zip entries',len(names),'contains model PNG',sum(n.endswith('.png') for n in names),'contains drawio',sum(n.endswith('.drawio') for n in names))
p=PdfReader('汇报成果/需求实践与分析成果研讨/01-研讨报告.pdf')
print('PDF pages',len(p.pages),'file',Path('汇报成果/需求实践与分析成果研讨/01-研讨报告.pdf').stat().st_size)
print('crosswalk filename', '数据采集任务状态机.drawio.png' in Path('汇报成果/需求实践与分析成果研讨/01-研讨报告.md').read_text(encoding='utf-8'))
for f in ['汇报成果/需求实践与分析成果研讨/01-研讨报告.docx','汇报成果/需求实践与分析成果研讨/02-课堂发言提纲.md','汇报成果/需求实践与分析成果研讨/03-研讨决策记录表.md']:
 print(f,Path(f).stat().st_size)
