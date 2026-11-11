from pathlib import Path
import re,shutil,json,hashlib,zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'需求分析/PPT主题汇报稿'
OLD=ROOT/'需求分析/PPT设计稿-需求分析正文版-v4.0'
main=OUT/'PPT逐页内容.md';text=main.read_text(encoding='utf-8')
titles=re.findall(r'^## 第\d+页 (.*)',text,re.M)
assert len(titles)==10
assert all('1组' not in x and '2组' not in x and '对照' not in x and '差异' not in x for x in titles)
assert not re.search(r'时长|累计|排练|分钟|\d+秒|画面安排|讲解稿|指图顺序|不同基线|基准不同',text)
assert '相同需求' in text
for folder in ['图件','可编辑源']:
    shutil.copytree(OLD/folder,OUT/folder,dirs_exist_ok=True)
shutil.copy2(OLD/'图件来源记录.json',OUT/'图件来源记录.json')
for p in (OUT/'图件').rglob('*'):
    if p.is_file():assert p.read_bytes()==(OLD/p.relative_to(OUT)).read_bytes()
for link in re.findall(r'!?\[.*?\]\((.*?)\)',text):assert (OUT/link).is_file(),link
pages=re.split(r'^## 第\d+页 .*\n',text,flags=re.M)[1:]
assert all('1组' in p and '2组' in p for p in pages[1:9])
index=['# 模型图件索引','正文按业务主题讲解，两组模型在同一主题下标注来源。完整图件和可编辑源保留，不要求逐图讲解。']
for group in ['1组','2组']:
    index+=['## '+group,'| 图件 | 对应正文 |','| --- | --- |']
    for p in sorted((OUT/'图件'/group).glob('*.png')):
        page_nums=[str(n) for n,part in enumerate(pages,1) if p.name in part]
        index.append(f'| [{p.stem}]({p.relative_to(OUT).as_posix()}) | '+('第'+'、'.join(page_nums)+'页' if page_nums else '完整材料备查')+' |')
(OUT/'图件索引.md').write_text('\n\n'.join(index)+'\n',encoding='utf-8')
(OUT/'README.md').write_text('''# 需求分析主题汇报稿

[PPT逐页内容](PPT逐页内容.md)按业务主题组织10页正文：需求范围、业务对象、类关系、采集处理、失败恢复、认领审核、并发授权、检索条件、结果一致性、场景核对。

每个主题只讲一次，同时标明1组和2组的具体模型表达。相关区别在对应页面简要说明，没有独立分组重复介绍，也没有末页差异汇总。两组依据相同需求开展分析。

正文只保留标题、业务内容和配图，无计时和制作备注。[图件索引](图件索引.md)列出原图及正文对应位置，全部原图、已有SVG和可编辑源随稿保存。
''',encoding='utf-8')
qa={'pages':10,'structure':titles,'grouping':'按业务主题，每个主题一次讲解，结合两组模型标注','separate_group_blocks':False,'final_difference_page':False,'basis':'相同需求基准','primary_content':'页标题、业务正文、配图；无计时及制作备注','figures':{'1组':len(list((OUT/'图件/1组').glob('*.png'))),'2组':len(list((OUT/'图件/2组').glob('*.png')))},'copy_hashes':'pass','local_links':'pass','artifact':'Markdown设计文稿，未生成PPTX'}
(OUT/'内容检查记录.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=[{'path':p.relative_to(OUT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in OUT.rglob('*') if p.is_file() and p.name!='交付文件清单.json']
(OUT/'交付文件清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
zpath=ROOT/'Submit/作业3_需求分析/PPT主题汇报稿.zip'
assert not zpath.exists()
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,Path(OUT.name)/p.relative_to(OUT))
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    assert all(z.read(OUT.name+'/'+x['path'])==(OUT/x['path']).read_bytes() for x in manifest)
zpath.with_suffix('.zip.sha256').write_text(hashlib.sha256(zpath.read_bytes()).hexdigest()+'  '+zpath.name+'\n',encoding='utf-8')
print(json.dumps({**qa,'zip_bytes':zpath.stat().st_size},ensure_ascii=False))
