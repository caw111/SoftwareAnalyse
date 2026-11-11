from pathlib import Path
import xml.etree.ElementTree as E,html,re,json
for name in ['05_核心业务类图.drawio','06_检索请求时序图.drawio','04_认领申请状态图.drawio','03_门户认领活动图.drawio','数据采集任务状态机.drawio']:
 print('\n===',name,'===')
 r=E.parse(Path('images')/name)
 for c in r.iter('mxCell'):
  v=c.get('value','')
  if v: print(re.sub('<[^>]+>',' ',html.unescape(v)).strip())
