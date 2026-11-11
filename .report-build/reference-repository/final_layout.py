from pathlib import Path
from docx import Document
import json
from authoring import author
BUILD=Path(__file__).resolve().parent
ROOT=BUILD.parents[1]
M=json.loads((BUILD/'manifest.json').read_text(encoding='utf-8'))
A,B=map(Path,M['packages'])
specs=[ROOT/'docs/02.需求建模/核心模块开发规范_SPEC.md',next(B.glob('02-SPEC*.md')),A/'参考文本/核心模块开发规范_SPEC.md']
for p in specs:
    t=p.read_text(encoding='utf-8');t='# 核心模块开发规范\n'+'\n'.join(t.splitlines()[1:])+'\n'
    pos=t.index('| v1.2 |')
    end=t.index('\n',pos)
    t=t[:end]+'\n| v2.0 | 2026-10-12 | 按参考格式统一封面、版本历史和目录；更新 SRS 章节引用及详细需求附录链接，保留核心模块规则 |'+t[end:]
    p.write_text(t,encoding='utf-8')
sp=next(B.glob('02-SPEC*.md'));author(sp,sp.with_suffix('.docx'))
check=next(A.glob('06-提交材料自查清单*.md'))
t=check.read_text(encoding='utf-8');t=t.replace('\n\n本表沿用','\n\n## 1. 提交材料核查\n\n本表沿用',1)
t=t.replace('本轮新增格式自查：','## 2. 重构格式核查\n\n本轮新增格式自查：')
for p in [check,next(B.glob('08-提交材料自查清单*.md'))]:p.write_text(t,encoding='utf-8')
author(check,check.with_suffix('.docx'))
record=next(A.glob('04-修改说明与版本记录*.md'))
t=record.read_text(encoding='utf-8')
t=t.replace('正式稿目前由 docs 三份 v1.1 Markdown 重构为统一格式的 Word 文件。','正式稿当前由 docs 中需求调研与需求建模两个阶段的 v2.0 Markdown 生成对应 Word 文件。')
t=t.replace('正式稿目录 docs 三份 v1.1 已同步为 v1.2 图文同步稿','正式稿已在 docs/01.需求调研 与 docs/02.需求建模 重构为 v2.0，重构前 v1.2 图文同步稿保存在历史归档')
for p in [record,next(B.glob('06-修改说明与版本记录*.md'))]:p.write_text(t,encoding='utf-8')
author(record,record.with_suffix('.docx'))
srs=next(B.glob('01-SRS*.docx'));d=Document(srs)
for p in d.paragraphs:
    if p.text.startswith('优先级：'):p.paragraph_format.keep_with_next=True
d.save(srs)
print('FINAL LAYOUT: SPEC cover, check directory, revision introduction, UC heading placement')
