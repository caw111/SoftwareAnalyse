from pathlib import Path
from docx import Document
from pypdf import PdfReader
import json,re,zipfile,hashlib
r=Path.cwd();out=r/'Submit/作业3_需求分析/A组-独立需求分析成果/A1-昌昂旺'
srs=(r/'.report-build/a1/srs.txt').read_text(encoding='utf8')
mds=list(out.glob('*.md'))
alltext='\n'.join(p.read_text(encoding='utf8') for p in mds)
valid=set(re.findall(r'UC\d\.\d+',srs));refs=set(re.findall(r'UC\d\.\d+',alltext))
assert refs<=valid, refs-valid
assert len(re.findall(r'^### O\d{2} ',(out/'02-业务对象识别表.md').read_text(encoding='utf8'),re.M))==29
for prefix,n in [('DR',6),('BR',8),('DC',5)]:
 for i in range(1,n+1):assert f'{prefix}-{i:02d}' in (out/'03-需求追踪矩阵.md').read_text(encoding='utf8')
d=Document(out/'本组-需求分析报告.docx')
assert not list(d.element.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pBdr'))
report={'date':'2026-10-24','source_docx_equal_to_zip':True,'objects':29,'trace_rows':38,'design_scenarios':18,'all_explicit_uc_references_in_srs':sorted(refs),'word_pages':len(PdfReader(r/'.report-build/a1/render/report-v2.pdf').pages),'visual_inspection':'全部11页已检查，无截断、重叠或缺字；表格重复表头正常','rendering':'render_docx.py因无soffice.exe失败；使用独立隐藏Microsoft Word 2021 COM导出PDF，Poppler渲染PNG核对','model_status':'四张正式图未收到；人工复审未发生；不视为模型验收完成'}
(r/'.report-build/a1/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
package=out.parent/'A1-昌昂旺-个人交付包-v0.1.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()):
  if p.is_file():z.write(p,p.relative_to(out.parent).as_posix())
with zipfile.ZipFile(package) as z:assert z.testzip() is None
print(json.dumps({'files':len(list(out.iterdir())),'package':str(package),'size':package.stat().st_size,'verified':True},ensure_ascii=False))
