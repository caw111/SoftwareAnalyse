from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[2]
out=root/'Submit'
paths=list((root/'docs').glob('*.md'))+list((root/'汇报成果').glob('*.md'))
for pkg in ['作业1_需求调研成果','作业2_需求建模成果']:paths+=list((out/pkg).rglob('*.md'))
replacements={
'重试耗尽或不可恢复时保持 FAILED 并保存失败原因，不再自动调度；管理员明确放弃后才 STOPPED，失败和主动取消分别统计。':'重试耗尽时转为 STOPPED 并保存失败历史与停止原因；不可恢复错误先记 FAILED，由管理员终止后转 STOPPED，失败和主动取消分别统计。',
'| AC-U08 | 重试耗尽及管理员后来放弃 | 耗尽保持 FAILED 且不调度；管理员放弃才 STOPPED，历史保留 |':'| AC-U08 | 重试耗尽或管理员人工终止 | 转为 STOPPED 并停止调度，保留失败历史、重试次数与停止原因 |',
'统计分析和成果管理现有 PNG 可展示，但对应可编辑源文件未在 images 中找到，不能声明源文件已经齐全。':'成果管理模块 PNG 存在；统计分析模块 PNG 及两个模块对应的可编辑源文件未在当前 images 中找到，缺失项在相应小节标明。',
'统计分析和成果管理的 PNG 存在，但原文提到的合并 Draw.io 工程缺失':'成果管理模块 PNG 存在，统计分析模块 PNG 和原文提到的合并 Draw.io 工程缺失',
"WHERE state IN ('PENDING', 'REVIEWING', 'NEEDS_INFO');":"WHERE state IN ('PENDING_REVIEW', 'NEED_MORE_INFO');",
'超过上限保留失败并解释原因':'重试耗尽时转为 STOPPED，保留失败和停止原因',
'APPROVE／REJECT／NEEDS_INFO':'APPROVE／REJECT／NEED_MORE_INFO',
}
for p in paths:
    text=p.read_text(encoding='utf-8')
    for old,new in replacements.items():text=text.replace(old,new)
    if p.parent==root/'docs' or p.parent.name=='文本源稿':
        if re.search(r'\| v1\.1 \| 2026-10-10',text) and '| v1.2 | 2026-10-12' not in text:
            text=re.sub(r'(^\| v1\.1 \| 2026-10-10[^\n]*$)',r'\1\n| v1.2 | 2026-10-12 | 按当前 images 同步插图、状态与模型解释，采用 Draw.io 可编辑文件并列出缺图 |',text,flags=re.M)
    if p.name=='图文核对与缺图清单.md':
        text=text.replace('| 总体技术架构图 |','| 统计分析模块用例图 | SRS §13.1 | 当前 images 缺少统计分析模块_UML用例图.png 及可编辑源文件 |\n| 总体技术架构图 |')
    p.write_text(text,encoding='utf-8')
p=out/'图文核对与缺图清单.md'
text=p.read_text(encoding='utf-8').replace('| 总体技术架构图 |','| 统计分析模块用例图 | SRS §13.1 | 当前 images 缺少统计分析模块_UML用例图.png 及可编辑源文件 |\n| 总体技术架构图 |')
p.write_text(text,encoding='utf-8')
build=root/'.report-build/submit-build'
old=json.loads((build/'superseded_word_outputs.json').read_text(encoding='utf-8'))
if old:
    notice='\n\n由于旧调研支撑 Word 正在被占用，本轮生成了“06-调研支撑材料摘编_图文更新版-9组-1011101011.docx”。文件夹内被占用的旧版暂留，两个更新压缩包只包含新版。\n'
    p=out/'README.md';p.write_text(p.read_text(encoding='utf-8')+notice,encoding='utf-8')
    (out/'作业1_需求调研成果'/'00-材料版本说明.md').write_text('# 材料版本说明\n\n调研支撑材料请使用文件名含“图文更新版”的 Word 副本。旧版因本机 Word 占用暂留，重新打包时排除旧版；其他正文采用 v1.2。具体缺图见图文核对与缺图清单。\n',encoding='utf-8')

# Make the updated excerpt's source address explicit for the next build.
files=json.loads((build/'docx_outputs.json').read_text(encoding='utf-8'))
for i,p in enumerate(files):
    if '_图文更新版' in p:
        # The exporter recognizes this suffix and continues to use the original Markdown source.
        pass
print('Resolved state and missing-image references')
