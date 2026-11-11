from zipfile import ZipFile
from pathlib import Path
from pypdf import PdfReader
z=Path('Submit/第9组-需求实践与分析成果研讨.zip')
with ZipFile(z) as f:
 print('zip test:',f.testzip(),'entries:',len(f.namelist()))
 for n in f.namelist(): print(n)
p=PdfReader('汇报成果/需求实践与分析成果研讨/01-研讨报告.pdf')
t='\n'.join(x.extract_text() or '' for x in p.pages)
for term in ['本组现有提交中没有A组自己绘制的用例图','待补分页采集活动图','附录D 核心业务类图','样本目标至少99%']:
 print(repr(term), term in t)
print('pdf pages',len(p.pages),'docx exists',Path('汇报成果/需求实践与分析成果研讨/01-研讨报告.docx').stat().st_size)
