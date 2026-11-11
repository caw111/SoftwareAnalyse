from pathlib import Path
import re,shutil,json,hashlib,zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'需求分析/PPT设计稿-需求分析正文版-v4.0'
OLD=ROOT/'需求分析/PPT设计稿-两组分别汇报版-v3.0'
main=OUT/'PPT逐页内容.md';body=main.read_text(encoding='utf-8')
headers=re.findall(r'^## (第\d+页 .*)',body,re.M)
assert len(headers)==10
assert all(f'第{i}页 1组' in body for i in range(2,6))
assert all(f'第{i}页 2组' in body for i in range(6,10))
assert not re.search(r'时长|累计|排练|分钟|\d+秒|画面安排|讲解稿|指图顺序|不同基线|基准不同|Group1|Group2|本组',body)
assert '相同需求基准' in body
parts=re.split(r'^## 第\d+页 .*\n',body,flags=re.M)[1:]
assert all('差异' not in p and '对照项' not in p for p in parts[:9])
assert parts[-1].count('两组的主要差异')==1
for folder in ['图件','可编辑源']:shutil.copytree(OLD/folder,OUT/folder,dirs_exist_ok=True)
shutil.copy2(OLD/'图件来源记录.json',OUT/'图件来源记录.json')
for path in (OUT/'图件').rglob('*'):
    if path.is_file():assert path.read_bytes()==(OLD/path.relative_to(OUT)).read_bytes()
assert len(list((OUT/'图件/1组').glob('*.png')))==13
assert len(list((OUT/'图件/2组').glob('*.png')))==4
for link in re.findall(r'!?\[.*?\]\((.*?)\)',body):assert (OUT/link).is_file(),link
index=['# 图件索引','1组与2组按各自业务模型分别介绍，完整原图与可编辑源一并提供。']
for group in ['1组','2组']:
    index+=['## '+group,'| 图件 | 正文位置 |','| --- | --- |']
    for path in sorted((OUT/'图件'/group).glob('*.png')):
        used=[str(i) for i,p in enumerate(parts,1) if path.name in p]
        index.append(f'| [{path.stem}]({path.relative_to(OUT).as_posix()}) | '+('第'+'、'.join(used)+'页' if used else '完整材料备查')+' |')
(OUT/'图件索引.md').write_text('\n\n'.join(index)+'\n',encoding='utf-8')
(OUT/'README.md').write_text('''# 需求分析正文版

[PPT逐页内容](PPT逐页内容.md)共10页，只包含页标题、业务正文和配图。

第1页说明需求范围，第2至5页分别介绍1组的对象模型、采集、认领和检索，第6至9页介绍2组对应内容。第10页归纳需要保证的业务结果，差异仅占最后一段简要对照。

正文重点是对象的属性和行为、关联约束、交互步骤、事务提交、异常恢复与并发处理。两组从相同需求基准出发。

[图件索引](图件索引.md)包含1组13张原图、2组4张原图及正文使用位置。已有SVG与原生可编辑源一并保留。
''',encoding='utf-8')
qa={'pages':10,'detailed_analysis_pages':list(range(2,10)),'difference':'仅第10页一段简要对照','requirements':'相同需求基准','group1_pages':list(range(2,6)),'group2_pages':list(range(6,10)),'slide_content':'对象数据与行为、关系约束、输入处理输出、事务、异常、并发；无计时或制作备注','images':{'1组':13,'2组':4},'local_links':'pass','image_bytes':'identical to source','artifact':'Markdown逐页内容；未生成PPTX'}
(OUT/'内容检查记录.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.rglob('*') if p.is_file() and p.name!='交付文件清单.json']
(OUT/'交付文件清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
zpath=ROOT/'Submit/作业3_需求分析/PPT设计稿-需求分析正文版-v4.0.zip'
assert not zpath.exists()
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in OUT.rglob('*'):
        if path.is_file():z.write(path,Path(OUT.name)/path.relative_to(OUT))
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    assert all(z.read(OUT.name+'/'+x['path'])==(OUT/x['path']).read_bytes() for x in manifest)
zpath.with_suffix('.zip.sha256').write_text(hashlib.sha256(zpath.read_bytes()).hexdigest()+'  '+zpath.name+'\n',encoding='utf-8')
print(json.dumps({**qa,'files':len(manifest)+1,'package_bytes':zpath.stat().st_size},ensure_ascii=False))
