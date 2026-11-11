from pypdf import PdfReader
p=PdfReader('汇报成果/需求实践与分析成果研讨/01-研讨报告.pdf')
for i,pg in enumerate(p.pages):
 t=pg.extract_text() or ''
 if i in (8,9): print('PAGE',i+1,repr(t[:1600]))
