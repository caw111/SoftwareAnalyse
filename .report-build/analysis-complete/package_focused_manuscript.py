from pathlib import Path
import re,shutil,json,hashlib,zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'需求分析/PPT设计稿-15分钟重点版-v2.0'
OLD=ROOT/'需求分析/PPT设计稿-两组对比与需求分析-v1.0'
source=OUT/'15分钟重点汇报逐页设计稿.md'
text=source.read_text(encoding='utf-8')
parts=re.split(r'^## (第\d+页 .*)\n',text,flags=re.M)
assert len(parts)==21
pages=[]
for i in range(1,len(parts),2):
    title=parts[i];body=parts[i+1].split('\n## 备查图件与制作边界')[0]
    seconds=int(re.search(r'时长：(\d+)秒',body).group(1))
    screen=re.search(r'### 上屏正文\n(.*?)\n### 画面安排',body,re.S).group(1).strip()
    notes=re.search(r'### 讲解稿\n(.*?)\n### (?:讲解节奏|指图顺序|依据)',body,re.S).group(1).strip()
    assert screen and notes and '### 依据' in body
    pages.append({'title':title,'seconds':seconds,'screen':screen,'notes':notes})
assert len(pages)==10 and sum(p['seconds'] for p in pages)==900
assert max(len(p['screen']) for p in pages)<450
shutil.copytree(OLD/'素材',OUT/'素材',dirs_exist_ok=True)
assert len(list((OUT/'素材/本组').glob('*.png')))==13
for p in (OUT/'素材').rglob('*'):
    if p.is_file():assert p.read_bytes()==(OLD/p.relative_to(OUT)).read_bytes()
copymd=['# 15分钟重点版上屏文案','10页主讲，上屏只放这里的文案。案例讲法、配图区域和时间安排见15分钟重点汇报逐页设计稿.md。']
for p in pages:copymd+=['## '+p['title'],p['screen']]
(OUT/'上屏文案.md').write_text('\n\n'.join(copymd)+'\n',encoding='utf-8')
index=['# 备查图件索引','主讲不新增附录页。遇到相关提问再打开下列完整图。原图和已有SVG全部保留，未更改图中业务内容。','| 图件 | 主讲或备查用途 |','| --- | --- |']
uses={
'02-局部01-账号学者与门户授权':'第3页，说明身份与管理授权',
'02-局部03-贡献机构与领域关系':'第4页，同贡献人物机构筛选',
'02-局部05-治理更新与公开版本':'第6页，入库与公开版本分离',
'03-采集入库时序图':'第5页，页断点与整窗水位',
'05a-认领原子授权与撤回子交互':'第7页事务、第8页并发竞争',
'06a-检索权限计数与分页子交互':'第9页，权限计数与分页'}
for p in sorted((OUT/'素材/本组').glob('*.png')):
    index.append(f'| [{p.stem}]({p.relative_to(OUT).as_posix()}) | {uses.get(p.stem,"备查，按提问打开")} |')
index+=['','[Group2类图](素材/Group2/01_核心业务类图.png)保留为比较依据，不增加固定主讲页。素材/可编辑源目录保留A2及新增Draw.io，以及A3原CodeArts工程。','## 比较来源','本组整合v1.1按当前SRS/SPEC v2.0。GitHub Group2固定提交b93110b采用其v1.1基线。B5吴星宇v0.9为另行提供的个人包，不能等同于Group2整组交付。','## 重点版使用方式','第2页讲比较与取舍。第3至4页解释对象关系，第5至6页解释采集与公开，第7至8页解释认领事务，第9页解释检索一致性。第10页用四个预期结果收束。完整类表、算法参数、工具和全部场景不在主讲中展开。']
(OUT/'备查图件索引.md').write_text('\n\n'.join(index)+'\n',encoding='utf-8')
(OUT/'README.md').write_text('''# 15分钟重点汇报设计稿 v2.0

从[15分钟重点汇报逐页设计稿](15分钟重点汇报逐页设计稿.md)开始。主讲10页，时间分配共900秒，没有固定附录页。

[上屏文案](上屏文案.md)可直接复制制作PPT。[备查图件索引](备查图件索引.md)保留13张本组原图及已有SVG、可编辑源和Group2比较图。

本轮根据用户对内容过多、缺少重点的反馈重写。两组比较聚焦对象拆分、认领状态和重试耗尽，主体用联合检索、分页恢复、原子授权、并发撤回、权限变化的具体案例讲解。此交付是设计文稿，未生成PPTX，15分钟为排练分配。
''',encoding='utf-8')
for name in ['15分钟重点汇报逐页设计稿.md','备查图件索引.md','README.md']:
    raw=(OUT/name).read_text(encoding='utf-8')
    for link in re.findall(r'!?\[.*?\]\((.*?)\)',raw):assert (OUT/link).is_file(),link
qa={'pages':10,'seconds':900,'fixed_appendix_pages':0,'main_diagrams':6,'all_our_pngs':13,'screen_characters':[len(p['screen']) for p in pages],'speaker_chinese_characters':[len(re.findall(r'[\u4e00-\u9fff]',p['notes'])) for p in pages],'check':'逐页有完整文案、案例讲解、配图范围、来源；图片复制字节一致；相对链接有效','boundary':'未生成PPTX，未进行实际放映排版或计时验证'}
(OUT/'设计稿检查记录.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.rglob('*') if p.is_file() and p.name!='交付校验清单.json']
(OUT/'交付校验清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
zpath=ROOT/'Submit/作业3_需求分析/PPT设计稿-15分钟重点版-v2.0.zip'
assert not zpath.exists()
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,Path(OUT.name)/p.relative_to(OUT))
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    assert all(z.read(OUT.name+'/'+x['path'])==(OUT/x['path']).read_bytes() for x in manifest)
digest=hashlib.sha256(zpath.read_bytes()).hexdigest()
zpath.with_suffix('.zip.sha256').write_text(digest+'  '+zpath.name+'\n',encoding='utf-8')
print(json.dumps({**qa,'zip':str(zpath),'zip_bytes':zpath.stat().st_size},ensure_ascii=False))
