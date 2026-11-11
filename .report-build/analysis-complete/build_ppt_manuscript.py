from pathlib import Path
import re,json,hashlib,shutil,zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'需求分析/PPT设计稿-两组对比与需求分析-v1.0'
BASE=ROOT/'需求分析/A组-需求分析整合版-v1.1'
draft=OUT/'PPT逐页设计文稿.md'
text=draft.read_text(encoding='utf-8')
parts=re.split(r'^## (第\d{2}页 .*|附录A\d{2} .*)\n',text,flags=re.M)
assert len(parts)==57
pages=[]
for i in range(1,len(parts),2):
    title,body=parts[i],parts[i+1].split('\n## 图件对应总表')[0]
    screen=re.search(r'### 上屏正文\n(.*?)\n### 版式与图件',body,re.S).group(1).strip()
    layout=re.search(r'### 版式与图件\n(.*?)\n### 讲解词',body,re.S).group(1).strip()
    notes=re.search(r'### 讲解词\n(.*?)\n### 页脚来源',body,re.S).group(1).strip()
    sources=re.search(r'### 页脚来源\n(.*)',body,re.S).group(1).strip()
    seconds=int(re.search(r'时长：(\d+)秒',body).group(1)) if title.startswith('第') else 0
    assert screen and layout and notes and sources
    assert not re.search(r'【.*?】|填写汇报人|按最终实际情况填写',screen)
    pages.append(dict(page=title.split(' ')[0],title=title,seconds=seconds,screen=screen,layout=layout,notes=notes,sources=sources))
assert len(pages)==28 and sum(p['seconds'] for p in pages)==900
assert len([p for p in pages if p['seconds']])==20
for p in pages:print(p['page'],p['seconds'],'screen chars',len(p['screen']))

names=['02-核心业务类图','02-局部01-账号学者与门户授权','02-局部02-四类成果与专利身份','02-局部03-贡献机构与领域关系','02-局部04-来源采集与规范映射','02-局部05-治理更新与公开版本','03-采集入库时序图','03a-清洗去重子交互','03b-停止重试子交互','05-门户认领审核时序图','05a-认领原子授权与撤回子交互','06-检索请求处理时序图','06a-检索权限计数与分页子交互']
roster=['03、06；附录A01','07','08','09','10','16','11；附录A02','12','13','14；附录A03','15','17；附录A04','18']
assets=[]
for i,(name,uses) in enumerate(zip(names,roster),1):
    for ext in ['.png','.svg']:
        src=BASE/'图件'/(name+ext)
        if src.exists():
            target=OUT/'素材/本组'/src.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
            assert src.read_bytes()==target.read_bytes()
            assets.append({'id':f'G{i:02}','source':str(src),'path':target.relative_to(OUT).as_posix(),'pages':uses,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
for src in (BASE/'模型源文件').glob('*'):
    if src.suffix=='.drawio' or src.name=='03-CodeArts正式模型工程.zip':
        target=OUT/'素材/可编辑源'/src.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
        assets.append({'id':'本组原生源','source':str(src),'path':target.relative_to(OUT).as_posix(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
group=BASE/'支撑材料/外部对照/Group2-b93110b/需求分析/image'
for ext in ['.png','.svg','.drawio']:
    src=group/('01_核心业务类图'+ext);target=OUT/'素材/Group2'/src.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
    assets.append({'id':'G2-01','source':str(src),'path':target.relative_to(OUT).as_posix(),'pages':'03','sha256':hashlib.sha256(target.read_bytes()).hexdigest()})

# Text-only copy for direct insertion into presentation authoring tools.
copy=['# PPT上屏正文汇总','本文件仅保留逐页设计稿的上屏正文，20页主讲共15分钟，8页答辩附录不计时。图件、版式和讲解词见PPT逐页设计文稿.md。']
for p in pages:copy+=['## '+p['title'],p['screen']]
(OUT/'PPT上屏正文汇总.md').write_text('\n\n'.join(copy)+'\n',encoding='utf-8')

index=['# 页面与素材索引','本组13张PNG原图全部随稿提供。SVG适合放大，PNG方便直接插入。主讲使用原图相关区域，完整图及可编辑源保持不变。','## 15分钟主讲安排','| 页码 | 标题 | 建议时长 | 累计时间 |','| --- | --- | --- | --- |']
elapsed=0
for p in pages[:20]:
    elapsed+=p['seconds'];index.append(f"| {p['page']} | {p['title'].split(' ',1)[1]} | {p['seconds']}秒 | {elapsed//60:02}:{elapsed%60:02} |")
index+=['','## 本组模型图','| 图号 | 图片 | 尺寸 | SVG | 使用页 |','| --- | --- | --- | --- | --- |']
for i,(name,uses) in enumerate(zip(names,roster),1):
    png=OUT/'素材/本组'/(name+'.png');svg=png.with_suffix('.svg')
    with Image.open(png) as im:size=f'{im.width}×{im.height}'
    s=f'[SVG]({svg.relative_to(OUT).as_posix()})' if svg.exists() else '原交付无SVG'
    index.append(f'| G{i:02} | [{name}]({png.relative_to(OUT).as_posix()}) | {size} | {s} | {uses} |')
index+=['','## Group2对照图','[G2-01 核心业务类图PNG](素材/Group2/01_核心业务类图.png)、[SVG](素材/Group2/01_核心业务类图.svg)、[Draw.io](素材/Group2/01_核心业务类图.drawio)。来源为固定提交b93110b，不作为本组原图重新署名。','## 来源入口']
refs=[('S1 本组详细报告',BASE/'本组-需求分析报告.md'),('S2 Group2原始报告',BASE/'支撑材料/外部对照/Group2-b93110b/需求分析/docs/学术成果分享平台_需求分析报告_v1.0.md'),('S3 B5原始说明',BASE/'支撑材料/外部对照/B5-v0.9/05-检索模型说明.md'),('S4 当前SPEC',ROOT/'docs/02.需求建模/核心模块开发规范_SPEC.md'),('S4 FR与AC附录',ROOT/'docs/02.需求建模/需求条目与验收场景.md'),('S5 完整对象关系字典',BASE/'支撑材料/业务对象与关系完整字典.md')]
for label,path in refs:
    assert path.is_file();index.append(f'- [{label}]({path.as_posix()})')
index+=['','上面的来源入口指向当前工作区。随稿图件采用相对路径，可整体移动；全部比较结论和来源版本已在设计正文中说明。','## 本组13张原图预览']
for i,name in enumerate(names,1):index+=['### '+f'G{i:02} '+name,f'![G{i:02} {name}](素材/本组/{name}.png)']
(OUT/'页面与素材索引.md').write_text('\n\n'.join(index)+'\n',encoding='utf-8')

proof=OUT/'参考材料';proof.mkdir(exist_ok=True)
shutil.copy2(BASE/'支撑材料/整合版32项设计走查.csv',proof/'整合版32项设计走查.csv')
shutil.copy2(BASE/'支撑材料/Group2与B5对照及修订.md',proof/'Group2与B5对照及修订.md')
readme='''# 两组对比与需求分析PPT设计稿

2026-10-26，v1.0。本轮交付为逐页内容设计，没有生成PPTX。

- [PPT逐页设计文稿](PPT逐页设计文稿.md)：20页主讲、8页附录，每页包含上屏正文、版式与图件、讲解词、来源。
- [上屏正文汇总](PPT上屏正文汇总.md)：可直接复制到PPT制作工具的页面文案。
- [页面与素材索引](页面与素材索引.md)：15分钟安排、13张本组图、Group2比较图、源文件和原图预览。
- 素材/本组：13张原PNG及已有SVG。素材/可编辑源：原A2、新增认领检索Draw.io，以及A3 CodeArts工程。
- 参考材料：实际对照说明和32项设计场景CSV。交付校验清单用于确认随稿文件未变动。

主讲共900秒。第2至5页讲差异，第6至18页讲具体模型，第19至20页讲追踪和结论。附录用于答辩。原图重复出现仅用于局部讲解与全图核查，保持相同图号和来源。

设计稿按当前整合v1.1及Group2固定提交比较，明确区分另行提供的B5个人材料。没有给两组贴未经交付证据支持的“需求驱动／场景驱动”标签，也没有宣称双方共用同一需求基线。
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')

# Structural content QA; this is a manuscript, not rendered PPT verification.
assert len(list((OUT/'素材/本组').glob('*.png')))==13
assert len(list((OUT/'素材/可编辑源').glob('*.drawio')))==5
assert all(re.search(r'\b'+f'G{i:02}'+r'\b','\n'.join(p['layout'] for p in pages[:20])) for i in range(1,14))
assert sum(p['seconds'] for p in pages[:20])==900
links=re.findall(r'!?\[.*?\]\((.*?)\)',(OUT/'页面与素材索引.md').read_text(encoding='utf-8'))
assert all((Path(link) if re.match(r'^[A-Za-z]:/',link) else OUT/link).exists() for link in links)
checks={'main_pages':20,'appendix_pages':8,'seconds':900,'our_pngs':13,'our_svgs':len(list((OUT/'素材/本组').glob('*.svg'))),'editable_drawio':5,'group2_reference_diagram':1,'source_copy_hashes':'pass','content':'每页均有完整上屏文案、配图与版式、讲解词、来源；所有13张本组图有主讲位置','validation':'设计稿结构及来源核对；未生成PPTX，未进行实际放映排版验证'}
(OUT/'设计稿检查记录.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'图件来源校验.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2),encoding='utf-8')
files=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.rglob('*') if p.is_file() and p.name!='交付校验清单.json']
(OUT/'交付校验清单.json').write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf-8')
zpath=ROOT/'Submit/作业3_需求分析/PPT设计稿-两组对比与需求分析-v1.0.zip'
assert not zpath.exists(), 'Use a new release name instead of replacing an existing archive.'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,Path(OUT.name)/p.relative_to(OUT))
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
digest=hashlib.sha256(zpath.read_bytes()).hexdigest()
zpath.with_suffix('.zip.sha256').write_text(digest+'  '+zpath.name+'\n',encoding='utf-8')
print(json.dumps({**checks,'output':str(OUT),'zip_bytes':zpath.stat().st_size,'sha256':digest},ensure_ascii=False))
