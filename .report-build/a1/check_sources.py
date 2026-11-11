from pathlib import Path
import zipfile,hashlib,xml.etree.ElementTree as E,base64,zlib,urllib.parse,re,html
root=Path.cwd()
z=zipfile.ZipFile(root/'Submit/第9组-第一次作业提交.zip')
for p in (root/'Submit/第9组-第一次作业提交').rglob('*.docx'):
 if p.name.startswith(('01-SRS','02-SPEC','01-需求调研报告')):
  keys=[n for n in z.namelist() if n.endswith(p.name)]
  print(p.name,'zip matches',len(keys),'same',bool(keys) and z.read(keys[0])==p.read_bytes())
p=root/'images/数据采集任务状态机.drawio'
r=E.parse(p).getroot()
for d in r.findall('diagram'):
 if not list(d):
  s=urllib.parse.unquote(zlib.decompress(base64.b64decode(d.text),-15).decode())
  model=E.fromstring(s)
 else:model=d
 for c in model.iter('mxCell'):
  v=c.get('value','')
  if v:print(re.sub('<[^>]+>',' ',html.unescape(v)))
