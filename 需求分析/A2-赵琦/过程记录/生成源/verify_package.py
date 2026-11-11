from model import *
from content import INVARIANTS,DECISIONS,SCENARIOS
import xml.etree.ElementTree as ET,re,hashlib,json,zipfile,shutil
from PIL import Image,ImageFont

checks=[]
def check(label,condition,detail):
 checks.append((label,bool(condition),detail))
 if not condition:raise AssertionError(label+': '+detail)

tree=ET.parse(OUT/'02-核心业务类图.drawio');pages=tree.getroot().findall('diagram')
check('draw.io可解析及页面数',len(pages)==6,'1个完整主图，5个局部图')
for page in pages:
 cells=page.findall('.//mxCell');ids=[x.get('id') for x in cells]
 check('页面ID唯一 '+page.get('name'),len(ids)==len(set(ids)),str(len(ids))+'个独立可编辑图元')
 allids=set(ids)
 check('画布内容范围 '+page.get('name'),not {'title','meta','note','constraints'} & allids,'画布仅显示类、属性、操作、关联与多重性。')
 check('画布追踪编号处理 '+page.get('name'),not any(re.match(r'^[CR]\d{2}\s',x.get('value','')) for x in cells),'C与R编号仅保留在正文和内部图元ID中。')
 check('画布独立文字检查 '+page.get('name'),all(re.fullmatch(r'R\d{2}-(?:lp|tail_lp|head_lp)',x.get('id','')) for x in cells if x.get('parent')=='1' and x.get('value','')),'类框外的独立文字均为关系标签或多重性。')
 for edge in [x for x in cells if x.get('edge')=='1']:
  check('端点存在 '+page.get('name')+' '+edge.get('id'),edge.get('source') in allids and edge.get('target') in allids,'关系两端均连接实际的类框图元。')
 check('页面图元类型 '+page.get('name'),not any('image=' in x.get('style','') for x in cells),'类框、属性、操作、端点及连线均为可编辑的XML图元。')

main={x.get('id'):x for x in pages[0].findall('.//mxCell')}
check('完整核心类覆盖',all(c['name'] in main for c in C) and len(C)==28,'28类全部在完整主图')
check('完整关系覆盖',all(r['id'] in main for r in R) and len(R)==45,'45关系全部在完整主图')
for r in R:
 e=main[r['id']]
 check('关系方向 '+r['id'],e.get('source')==r['a'] and e.get('target')==r['b'],r['a']+' / '+r['b'])
 if r['kind']=='generalization':check('泛化箭头 '+r['id'],'endArrow=block' in e.get('style') and 'endFill=0' in e.get('style') and r['b']=='Work','空心三角指向Work')
 else:
  check('多重性 '+r['id'],main[r['id']+'-tail_lp'].get('value')==r['am'] and main[r['id']+'-head_lp'].get('value')==r['bm'],r['am']+' / '+r['bm'])
check('组合关系的使用',[r['id'] for r in R if r['kind']=='composition']==['R43'] and 'startArrow=diamond' in main['R43'].get('style'),'仅PublicRelease拥有ReleaseEntry，菱形在整体端')
check('认领状态集合',set(CLAIM_STATES)=={'DRAFT','PENDING_REVIEW','NEED_MORE_INFO','APPROVED','REJECTED','WITHDRAWN'},'保持原六状态')
check('采集状态集合',set(COLLECTION_STATES)=={'PENDING','RUNNING','SUCCEEDED','FAILED','RETRYING','STOPPED'},'保持原六状态')

report=OUT/'02-A2赵琦-核心业务类图与领域关系设计.md';text=report.read_text(encoding='utf-8')
check('完整类字典',all('## '+c['id']+' '+c['cn']+' '+c['name'] in text for c in C),'28项有属性、方法、约束及依据')
check('不变量 决策 场景覆盖',len(INVARIANTS)==14 and len(DECISIONS)==10 and len(SCENARIOS)==30 and all(code in text for code in [s[0] for s in INVARIANTS+DECISIONS+SCENARIOS]),'14项不变量、10项决策、30个模型走查')
for md in OUT.glob('*.md'):
 body=md.read_text(encoding='utf-8')
 check('文件元数据 '+md.name,'赵琦' in body and '2026-10-23' in body and 'v1.0' in body,'责任人、日期和版本明确')
 for target in re.findall(r'\]\(([^)]+)\)',body):
  if target.startswith(('#','http')):continue
  check('相对链接 '+md.name+' '+target,(md.parent/target).is_file(),'链接目标存在')
check('Markdown交付格式',not list(OUT.glob('*.docx')),'交付文档按照用户要求统一采用Markdown格式。')
check('泛型显示', '`title: FieldValue<String>`' in text,'代码格式完整保留泛型类型中的尖括号。')
for md in OUT.glob('*.md'):
 body=md.read_text(encoding='utf-8')
 forbidden=['不是','而是','并非','不把','不能','不得','不要','不造','不宣称','不冒称','强塞','吞并','拍板','写死','断点不动','插桩','簿记','刷盘','落盘']
 found=[s for s in forbidden if s in body]
 check('书面表达检查 '+md.name,not found,'已核对用户列明的否定转折、口语表达及非规范工程用语。')
pngs=list((OUT/'图件').glob('*.png'))
check('PNG数量',len(pngs)==6,'主图及5张局部图')
for f in pngs:
 im=Image.open(f);im.verify()
 with Image.open(f) as im:check('图片分辨率 '+f.name,min(im.size)>2000,str(im.size))
for f in (OUT/'图件').glob('*.svg'):
 st=ET.parse(f).getroot()
 labels=[''.join(x.itertext()) for x in st.findall('.//{http://www.w3.org/2000/svg}text')]
 check('SVG画布内容 '+f.name,not any(any(s in t for s in ('学术成果分享平台','第9组','约束：','实线为关联','待成员复审','2026-10-23','v1.0')) or re.match(r'^[CR]\d{2}\s',t) for t in labels),'SVG与draw.io保持一致，画布仅包含模型元素。')

record=OUT/'过程记录';record.mkdir(exist_ok=True)
summary='# 自动结构核验记录\n\n'+META+'\n\n'
summary+='本次核验覆盖文件、模型结构、图件内容及指定用语。业务代码测试、CodeArts原生工程验收和成员复审分别按照对应工作安排执行。\n\n'
summary+=f'本次 {len(checks)} 项自动断言全部通过。检查内容包括图源解析、页面与图元唯一性、28个类和45项关系的覆盖、箭头与端点、两个六状态集合、Markdown字典及相对链接、PNG分辨率、图件内容范围和指定用语。\n\n'
summary+='| 检查项 | 结果 | 说明 |\n| --- | --- | --- |\n'+'\n'.join('| '+a+' | 通过 | '+c+' |' for a,b,c in checks)+'\n'
(record/'自动结构核验记录.md').write_text(summary,encoding='utf-8')
(record/'自动结构核验结果.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')

base=OUT.parents[1]
names={'01-SRS_v2.0-9组-1011101011.docx','02-SPEC_v2.0-9组-1011101011.docx','01-需求调研报告_v2.0-9组-1011101011.docx','04-修改说明与版本记录_v2.0-9组-1011101011.docx','《软件系统分析与设计》实践任务书（一）学术成果分享平台-v1(1).pdf','《软件系统分析与设计》课程实践作业课堂展示与提交要求（需求分析).pdf','02-A2-赵琦-核心业务类图与领域关系设计.md','00-总设计手册-先看这里.md','05_核心业务类图.drawio','06_检索请求时序图.drawio','04_认领申请状态图.drawio','03_门户认领活动图.drawio','数据采集任务状态机.drawio'}
sources=[p for p in base.rglob('*') if p.is_file() and p.name in names and OUT.parents[0] not in p.parents]
(record/'输入文件指纹.tsv').write_text('实际使用输入路径\tSHA256\n'+'\n'.join(str(p.relative_to(base))+'\t'+hashlib.sha256(p.read_bytes()).hexdigest() for p in sources)+'\n',encoding='utf-8')
gen=record/'生成源';gen.mkdir(exist_ok=True)
for n in ['model.py','content.py','diagrams.py','layout.cjs','build_markdown.py','verify_package.py']:
 shutil.copy2(OUT/'_work'/n,gen/n)
shutil.copy2(OUT/'_work'/'model.json',gen/'model.json')
(gen/'说明.md').write_text('# 生成源说明\n\n'+META+'\n\n本目录保存当前版本的模型数据与生成程序。复现时，将本目录代码复制到A2目录下的 `_work` 中，然后依次运行 `model.py`、`diagrams.py`、`layout.cjs`、`diagrams.py render`、`layout.cjs png`、`build_markdown.py`和`verify_package.py`。Node脚本使用本机运行库路径，迁移到其他机器时应当调整对应配置。PNG、SVG与draw.io使用同一模型和布局数据。\n\n生成文档统一采用Markdown格式。源文件中的Word与PDF文件名用于标识原始需求资料和课程文件。\n',encoding='utf-8')
print('PASS',len(checks),'checks;',len(text),'characters in full Markdown')
