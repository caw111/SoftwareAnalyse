from pypdf import PdfReader
from pathlib import Path
p=Path('E:/weichat/xwechat_files/wxid_quoop5hprm8122_9298/msg/file/2026-11/ssad05.架构设计.pdf')
r=PdfReader(p)
s='\n\n'.join('=== PDF PAGE '+str(i+1)+' ===\n'+(x.extract_text() or '') for i,x in enumerate(r.pages))
Path('.report-build/seminar/lecture.txt').write_text(s,encoding='utf8')
print('pages',len(r.pages))
for i,x in enumerate(r.pages):
 t=x.extract_text() or ''
 if any(w in t for w in ['研讨','需求实践','成果','实践要求','质量属性']): print('\nPAGE',i+1,'\n',t)
