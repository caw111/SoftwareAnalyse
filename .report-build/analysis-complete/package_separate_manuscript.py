from pathlib import Path
import re,json,shutil,hashlib,zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'需求分析/PPT设计稿-两组分别汇报版-v3.0'
BASE=ROOT/'需求分析/A组-需求分析整合版-v1.1'
main=OUT/'PPT逐页内容.md'
text=main.read_text(encoding='utf-8')
assert len(re.findall(r'^## 第\d+页 ',text,re.M))==10
assert all(f'第{i}页 1组' in text for i in range(2,6))
assert all(f'第{i}页 2组' in text for i in range(6,10))
assert not re.search(r'时长|累计|排练|分钟|\d+秒|画面安排|讲解稿|指图顺序|不同基线|基准不同|Group1|Group2|本组',text)
assert '相同的需求基准' in text
records=[]
def copy(src,target):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    assert digest==hashlib.sha256(target.read_bytes()).hexdigest()
    records.append({'source':str(src),'path':target.relative_to(OUT).as_posix(),'sha256':digest,'bytes':target.stat().st_size})
for src in (BASE/'图件').iterdir():
    if src.suffix in ['.png','.svg']:copy(src,OUT/'图件/1组'/src.name)
for src in (BASE/'模型源文件').iterdir():
    if src.suffix=='.drawio' or src.name=='03-CodeArts正式模型工程.zip':copy(src,OUT/'可编辑源/1组'/src.name)
group=BASE/'支撑材料/外部对照/Group2-b93110b/需求分析/image'
for src in group.iterdir():
    if src.suffix in ['.png','.svg','.drawio']:copy(src,OUT/'图件/2组'/src.name if src.suffix!='.drawio' else OUT/'可编辑源/2组'/src.name)
assert len(list((OUT/'图件/1组').glob('*.png')))==13
assert len(list((OUT/'图件/2组').glob('*.png')))==4
links=re.findall(r'!?\[.*?\]\((.*?)\)',text)
assert links and all((OUT/link).is_file() for link in links)
index=['# 配图索引','## 1组','| 图片 | 逐页内容中的位置 |','| --- | --- |']
for src in sorted((OUT/'图件/1组').glob('*.png')):
    pages=[]
    for i,part in enumerate(re.split(r'^## 第\d+页 .*\n',text,flags=re.M)[1:],1):
        if src.name in part:pages.append(str(i))
    index.append(f'| [{src.stem}]({src.relative_to(OUT).as_posix()}) | '+('第'+ '、'.join(pages)+'页' if pages else '完整材料备查')+' |')
index+=['','## 2组','| 图片 | 逐页内容中的位置 |','| --- | --- |']
for page,filename in [(6,'01_核心业务类图'),(7,'02_数据采集入库时序图'),(8,'03_门户认领审核时序图'),(9,'04_检索请求处理时序图')]:
    index.append(f'| [{filename}](图件/2组/{filename}.png) | 第{page}页 |')
index+=['','图件目录同时提供已有SVG，可编辑源目录保留Draw.io与原CodeArts工程。图中原始标识与署名保持原样。']
(OUT/'配图索引.md').write_text('\n\n'.join(index)+'\n',encoding='utf-8')
(OUT/'README.md').write_text('''# 两组分别汇报版

[PPT逐页内容](PPT逐页内容.md)只包含10页的标题、正文和配图，不包含汇报时长、累计计时、排练、版式指导或演讲备注。

第1页说明共同需求，第2至5页分别讲1组的类图和三条流程，第6至9页对应介绍2组，第10页归纳差异。两组以相同需求基准开展分析，当前模型中的状态和终态分歧列为需要统一的问题。

[配图索引](配图索引.md)列出1组13张图与2组4张图。图件和可编辑源随稿提供。
''',encoding='utf-8')
provenance={'group_names':{'1组':'当前工作区A组整合v1.1所展示的模型','2组':'GitHub Group2固定提交b93110b所展示的模型'},'comparison_basis':'按用户明确要求：两组起始需求基准相同，不以原交付文字中的版本标签差异解释任务基准不同。现有六/九状态和耗尽终态差异作为模型结果待复核。','group1_search':'当前整合检索已参考用户补充的B5个人包，非原始独立稿；未把该个人包作为2组整组报告。','files':records}
(OUT/'图件来源记录.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
qa={'pages':10,'group1_pages':[2,3,4,5],'group2_pages':[6,7,8,9],'comparison_page':10,'basis':'共同需求基准','primary_content':'仅页标题、正文、配图；无汇报计时或制作备注','images':{'1组':13,'2组':4},'image_copies':'字节一致','local_links':'全部有效','format':'Markdown逐页内容，未生成PPTX'}
(OUT/'检查记录.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=[{'path':p.relative_to(OUT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in OUT.rglob('*') if p.is_file() and p.name!='交付文件清单.json']
(OUT/'交付文件清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
zip_path=ROOT/'Submit/作业3_需求分析/PPT设计稿-两组分别汇报版-v3.0.zip'
assert not zip_path.exists()
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,Path(OUT.name)/p.relative_to(OUT))
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert all(z.read(OUT.name+'/'+x['path'])==(OUT/x['path']).read_bytes() for x in manifest)
digest=hashlib.sha256(zip_path.read_bytes()).hexdigest()
zip_path.with_suffix('.zip.sha256').write_text(digest+'  '+zip_path.name+'\n',encoding='utf-8')
print(json.dumps({**qa,'zip_bytes':zip_path.stat().st_size,'sha256':digest},ensure_ascii=False))
