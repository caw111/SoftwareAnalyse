from pathlib import Path
import json,re,shutil
from authoring import author
BUILD=Path(__file__).resolve().parent
ROOT=BUILD.parents[1]
OUT=ROOT/'Submit'
manifest=json.loads((BUILD/'manifest.json').read_text(encoding='utf-8'))
A,B=map(Path,manifest['packages'])
ARCH=OUT/'归档_历史材料_不放入提交压缩包/参考仓库格式重构前_v1.2'
old=(ARCH/'docs/系统需求规格说明书_SRS.md').read_text(encoding='utf-8')
nf=re.search(r'^## 8\..*?(?=^## 9\.)',old,re.M|re.S).group(0)
nf=re.sub(r'^## 8\.[^\n]*\n','',nf)
nf=re.sub(r'^(#{3,5}) 8([. ]?)',r'\1 6\2',nf,flags=re.M)
nf=nf.replace('依甲方任务书采用 CodeArts 支撑需求、代码、检查、构建、测试及部署；','原任务书记载后续工程过程采用 CodeArts 支撑需求、代码、检查、构建、测试及部署；本次需求建模源文件采用 Draw.io，不转换或新建 CodeArts 工程。')
for src in map(Path,manifest['formal_sources']):
    t=src.read_text(encoding='utf-8')
    if src.name=='系统需求规格说明书_SRS.md':
        t=t.replace('SUCCEEDED 为图中的成功状态；本文不再另用 SUCCEEDED 表示同一结果。','SUCCEEDED 为图中的成功状态。')
        t=t.replace('| 可观测性 | OBS-01 |','| 性能 | PER-03 | 基础预聚合统计和推荐分别设定目标 | 10000 条成果、20 并发预热运行 5 分钟，基础统计 P95 不超过 3 秒；推荐设置 1 秒级超时并降级，不阻塞主详情 |\n| 可扩展性 | SCA-01 | 支持数据规模与来源扩充 | 10 万级论文无需改变基础架构运行；四类成果和来源适配独立扩展，扩充后的性能单独实测 |\n| 数据质量 | DQ-04 | ROR 精确映射需要来源依据 | 固定分层样本抽查，正确率目标至少 99%，记录样本量、标注依据与实际结果 |\n| 可观测性 | OBS-01 |')
    elif src.name=='核心模块开发规范_SPEC.md':
        t=t.replace('按SRS §6.4两论文样例','按《需求条目与验收场景》§4.4两论文样例')
    elif src.name=='需求条目与验收场景.md':
        t=t.replace('## 6. 图中局部用例编号映射','## 6. 详细非功能与工程交付要求\n\n'+nf+'\n\n## 7. 图中局部用例编号映射')
        t=t.replace('原基线 §','原基线 §')
        t=t.replace('## 2. 功能需求详细条目','旧版章节引用按下列对应查阅本附件：原基线 §4.x → 本附件 §2.x；§5.x → §3.x；§6.x → §4.x；§8.x → §6.x；§10.x → §5.x。原基线 §13 模型解释已融入主 SRS 第 3 章相应图与用例；原基线 §14 的模块对应由本版 FR 映射与 SPEC 共同承接。\n\n## 2. 功能需求详细条目')
    elif src.name=='数据源与竞品调研记录.md':
        t=t.replace('| C2 |','| U1 | [普通用户需求调研报告](../../scripts/学术成果分享平台_普通用户需求调研报告.md) | 公开查询、人物确认与统计场景的原始输入 |\n| U2 | [科研人员需求分析与建模](../../scripts/科研人员需求分析与需求建模.md) | 科研人员门户与研究资料利用的原始输入 |\n| C2 |')
    src.write_text(t,encoding='utf-8')

destinations={Path(s).resolve():Path(d).with_suffix('.md') for s,d in zip(manifest['formal_sources'],[pair[1] for pair in manifest['word_sources'][:6]])}
current={p.name:p for p in (ROOT/'images').iterdir() if p.suffix in ['.png','.drawio']}
for source,dest in destinations.items():
    pkg=A if dest.is_relative_to(A) else B
    text=source.read_text(encoding='utf-8')
    def fix(m):
        target=m.group(2)
        if re.match(r'^(https?://|mailto:|#)',target):return m.group(0)
        resolved=(source.parent/target).resolve()
        if resolved.name in current:target_file=pkg/'images'/resolved.name
        elif resolved in destinations:
            target_file=destinations[resolved]
            if not target_file.is_relative_to(pkg):
                target_file=pkg/'参考文本'/resolved.name;target_file.parent.mkdir(exist_ok=True)
                target_file.write_text(resolved.read_text(encoding='utf-8'),encoding='utf-8')
        elif resolved.is_file():
            target_file=pkg/'参考附件'/resolved.name;target_file.parent.mkdir(exist_ok=True);shutil.copyfile(resolved,target_file)
        else:return m.group(1).strip('![]')+'（原文件待补）'
        return m.group(1)+'('+Path(__import__('os').path.relpath(target_file,dest.parent)).as_posix()+')'
    dest.write_text(re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',fix,text),encoding='utf-8')

# Historical text is supplied as research input, with diagram links normalized to current assets.
for pkg in [A,B]:
    for folder in ['参考附件','参考文本']:
        for p in (pkg/folder).glob('*.md'):
            t=p.read_text(encoding='utf-8')
            def clean(m):
                target=m.group(2)
                if re.match(r'^(https?://|mailto:|#)',target):return m.group(0)
                base=Path(target).name
                if base in current:return m.group(1)+'(../images/'+base+')'
                return m.group(1).strip('![]')+'（历史引用，详见本包正式正文与缺图清单）'
            t=re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',clean,t)
            # Historical Mermaid drafts are input notes, not accepted diagrams in the formal package.
            t=re.sub(r'```mermaid.*?```','历史 Mermaid 草图不作为本版模型；正式图以本包 images 与 SRS 为准。',t,flags=re.S)
            p.write_text(t,encoding='utf-8')

missing=(OUT/'图文核对与缺图清单.md').read_text(encoding='utf-8')
missing=missing.replace('SRS §13.1','v2.0 SRS 用例包 4；原 v1.2 §13.1')
for pkg in [OUT,A,B]:(pkg/'图文核对与缺图清单.md').write_text(missing,encoding='utf-8')

for s,d in manifest['word_sources']:
    if Path(d).name.startswith(('01-SRS','02-SPEC','01-需求条目','02-数据源')):author(Path(s),Path(d))

(ROOT/'README.md').write_text('''# SoftwareAnalyse

《软件系统分析与设计》课程项目：学术成果检索与分享平台。组号 9组，团队名 1011101011。

当前正式稿为 2026-10-12 的 v2.0，按用户指定仓库的需求调研与需求建模写法重构，Word 封面、版本历史、自动目录和表格格式参照其 PDF。

- [需求调研及支撑材料](docs/01.需求调研/需求调研报告.md)
- [系统需求规格说明书 SRS](docs/02.需求建模/系统需求规格说明书_SRS.md)
- [核心模块开发规范 SPEC](docs/02.需求建模/核心模块开发规范_SPEC.md)
- [完整 FR、业务规则、质量目标与 AC 附录](docs/02.需求建模/需求条目与验收场景.md)
- [Submit 提交目录与两份压缩包说明](Submit/README.md)
- [缺图与可编辑文件缺失清单](Submit/图文核对与缺图清单.md)
- [重构说明与参考来源](docs/重构说明.md)

源稿按需求调研与需求建模两个阶段组织；Submit 保存对应 Word、Markdown、Draw.io 与 PNG、现有 PPT 和修订等附件，原输入和旧提交材料保留在历史归档中。本轮未向外部提交。

调研问卷、访谈、原型测试、来源实验和系统指标按已有证据区分已执行与待验证。团队成员、签核及缺失原件仍待按实际情况补齐。所有正式插图取自当前 images；模型采用 Draw.io。
''',encoding='utf-8')
print('REFRESHED four Word documents and current source links')
