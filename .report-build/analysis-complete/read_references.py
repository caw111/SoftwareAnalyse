from pathlib import Path
import zipfile, hashlib, json

ROOT=Path(__file__).resolve().parents[2]
BUILD=Path(__file__).parent
REF=BUILD/'references';REF.mkdir(exist_ok=True)
baseline=ROOT/'需求分析/A组-需求分析整合版-v1.0'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[{'path':p.relative_to(baseline).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size} for p in baseline.rglob('*') if p.is_file()]
manifest=BUILD/'v1.0-before-revision.json'
if not manifest.exists():manifest.write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf-8')
inputs=[('Group2-b93110b',BUILD/'group2-b93110b.zip'),('B5',Path('E:/weichat/xwechat_files/wxid_quoop5hprm8122_9298/msg/file/2026-10/B组-B5-吴星宇-检索与一致性验收.zip'))]
info=[]
for name,zpath in inputs:
    target=(REF/name).resolve();target.mkdir(exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        for f in z.infolist():
            dest=(target/f.filename).resolve()
            assert dest==target or target in dest.parents, f.filename
            if f.is_dir():dest.mkdir(parents=True,exist_ok=True)
            else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(f))
        info.append({'name':name,'source':str(zpath),'sha256':digest(zpath),'entries':len(z.infolist()),'crc':'pass'})
(REF/'输入来源.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
for p in (REF/'Group2-b93110b').rglob('学术成果分享平台_需求分析报告_v1.0.md'):
    print(p.read_text(encoding='utf-8-sig'))
