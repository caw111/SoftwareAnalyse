from pathlib import Path
from docx import Document
from pypdf import PdfReader
root=Path.cwd(); out=root/'.report-build/a1'
base=root/'Submit/第9组-第一次作业提交'
for key,pattern in [('srs','需求建模/01-SRS*.docx'),('spec','需求建模/02-SPEC*.docx'),('survey','需求调研/01-需求调研报告*.docx')]:
 p=next(base.glob(pattern)); d=Document(p)
 from docx.oxml.ns import qn
 lines=[]
 for child in d.element.body:
  if child.tag==qn('w:p'):
   lines.append(''.join(child.itertext()) if False else ''.join(t.text or '' for t in child.iter(qn('w:t'))))
  elif child.tag==qn('w:tbl'):
   for row in child.findall(qn('w:tr')): lines.append(' | '.join(''.join(t.text or '' for t in cell.iter(qn('w:t'))) for cell in row.findall(qn('w:tc'))))
 (out/(key+'.txt')).write_text('\n'.join(lines),encoding='utf-8')
for key,p in [('course',root/'Submit/整理依据_课堂展示与提交要求.pdf'),('task',next(root.glob('*实践任务书*.pdf')))]:
 d=PdfReader(p); (out/(key+'.txt')).write_text('\n'.join(f'\n=== 第{i+1}页 ===\n'+page.extract_text() for i,page in enumerate(d.pages)),encoding='utf-8')
print('extract complete')

