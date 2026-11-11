from pypdf import PdfReader
p=PdfReader('汇报成果/需求实践与分析成果研讨/01-研讨报告.pdf')
for i in range(10,14): print(i+1,repr(p.pages[i].extract_text()))
