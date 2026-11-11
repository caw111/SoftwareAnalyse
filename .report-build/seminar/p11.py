from pypdf import PdfReader
p=PdfReader('汇报成果/需求实践与分析成果研讨/01-研讨报告.pdf')
print(repr(p.pages[10].extract_text()))
