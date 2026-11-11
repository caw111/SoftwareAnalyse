from pathlib import Path
from PIL import Image
import hashlib, json, re, zipfile, subprocess, sys, tempfile

root = Path(__file__).resolve().parent.parent
support = root/'支撑材料'
excluded = {'plantuml.jar','build_deliverables.py','finalize_package.py','主图局部检查.png','压缩包校验结果.json'}
hashof = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
for source in sorted((root/'07-建模源文件').glob('*.puml')):
    text = source.read_text(encoding='utf-8')
    prefix = 'D' if source.name.startswith('05a') else 'M'
    expected = 20 if prefix == 'D' else 34
    messages = re.findall(r': ('+prefix+r'\d\d)\b',text)
    assert messages == [f'{prefix}{i:02d}' for i in range(1,expected+1)], messages
    png = root/(source.stem+'.png')
    with Image.open(png) as im:
        im.verify()
    with Image.open(png) as im:
        dimensions = list(im.size)
    checks.append({'source':str(source.relative_to(root)),'png':png.name,'message_ids':len(messages),'dimensions':dimensions,'source_rendered':True,'png_decodable':True})

for p in root.glob('*.md'):
    body=p.read_text(encoding='utf-8')
    assert '角色：B5' in body and '审核状态' in body
scenario=(root/'05-典型场景走查.md').read_text(encoding='utf-8')
counts={x:len(re.findall(r'^\| '+x+r'\d\d \|',scenario,re.M)) for x in 'SCP'}
assert counts == {'S':18,'C':8,'P':9},counts
baseline=json.loads((support/'基线文件清单.json').read_text(encoding='utf-8'))
assert all(hashof(Path(item['path']))==item['sha256'] for item in baseline['sources'])

tool_output=subprocess.run(['java','-jar',str(support/'plantuml.jar'),'-version'],capture_output=True).stdout.decode('utf-8',errors='replace')
validation={
 'date':'2026-10-26',
 'tool':{'name':'PlantUML','version':'1.2025.2','source':'https://github.com/plantuml/plantuml/releases/download/v1.2025.2/plantuml-1.2025.2.jar','sha256':hashof(support/'plantuml.jar'),'version_output':tool_output},
 'models':checks,'scenario_counts':counts,
 'baseline_originals_unchanged':True,
 'visual_check':{'by':'AI图像检查，非成员人工签署','observed':'主图与详情图整体已查看，修订else标签后检查主图局部；文字可辨，无可见裁切。'},
 'scope':'仅源图语法渲染、PNG解码/可读性、编号/文件结构、原文件哈希和ZIP完整性；不是软件运行或性能验收。',
 'pending':['CodeArts工程打开与正式工具规范确认','B1～B4新成果与全组跨模型验收','author_scope、分组分页、当前范围变化策略评审','责任作者及另一成员真实人工复审'],
 'status':'个人分析草稿v0.9，不是全组验收通过'
}
(support/'验证记录.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')

def files():
    return sorted(p for p in root.rglob('*') if p.is_file() and p.name not in excluded and '__pycache__' not in p.parts and p.name!='冻结清单.json')

entries=[{'path':p.relative_to(root).as_posix(),'sha256':hashof(p),'bytes':p.stat().st_size} for p in files()]
(support/'冻结清单.json').write_text(json.dumps({'date':'2026-10-26','version':'v0.9','scope':'B5个人交接快照；不等于B组或A/B独立冻结签署','exclusions':'运行工具jar、生成/打包中间脚本及检查用裁图不入交接ZIP；冻结清单不自我哈希','files':entries},ensure_ascii=False,indent=2),encoding='utf-8')

archive=root.parent/'B组-B5-吴星宇-检索与一致性验收-v0.9.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files()+[support/'冻结清单.json']:
        z.write(p,root.name+'/'+p.relative_to(root).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for item in entries:
        assert hashlib.sha256(z.read(root.name+'/'+item['path'])).hexdigest()==item['sha256']
    for name in z.namelist():
        if name.endswith('.json'):
            json.loads(z.read(name))
    member_count=len(z.namelist())
summary={'archive':str(archive),'sha256':hashof(archive),'bytes':archive.stat().st_size,'members':member_count,'zip_crc_and_manifest_verified':True,'model_checks':checks,'scenario_counts':counts}
(support/'压缩包校验结果.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
# Keep this post-archive receipt outside the ZIP, since it hashes the ZIP itself.
print(json.dumps(summary,ensure_ascii=False,indent=2))
