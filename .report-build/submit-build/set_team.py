from pathlib import Path
from docx import Document
import json
build=Path(__file__).resolve().parent
out=build.parents[1]/'Submit'
old='组号待填-团队名待填';new='9组-1011101011'
def update(text):
    return text.replace(old,new).replace('组号：待填','组号：9组').replace('团队名：待填','团队名：1011101011').replace('团队名称：待填','团队名称：1011101011').replace('填写组号 团队名 成员分工和提交负责人，替换文件及压缩包中的待填字样。','组号为 9组，团队名为 1011101011。填写成员分工和提交负责人。').replace('当前没有组号和团队名，文件使用“组号待填-团队名待填”，不可原样作为最终命名提交。替换名称后需重新打包。团队成员、分工、历史 AI 使用及人工验证情况也需填写。','组号为 9组，团队名为 1011101011，文件与压缩包已按此命名。团队成员、分工、历史 AI 使用及人工验证情况仍需填写。')
# Remove only the two earlier generated packages, then rebuild after renaming.
for suffix in ['需求调研成果','需求建模成果']:
    target=out/f'{old}-{suffix}.zip'
    assert target.resolve().parent==out.resolve()
    if target.exists():target.unlink()
for p in sorted(out.rglob('*'),key=lambda p:len(p.parts),reverse=True):
    if old in p.name:p.rename(p.with_name(p.name.replace(old,new)))
for p in out.rglob('*.md'):
    if '归档_' in str(p):continue
    text=p.read_text(encoding='utf-8')
    # Replace this exact instruction before replacing the placeholder token.
    text=text.replace('当前没有组号和团队名，文件使用“组号待填-团队名待填”，不可原样作为最终命名提交。替换名称后需重新打包。团队成员、分工、历史 AI 使用及人工验证情况也需填写。','组号为 9组，团队名为 1011101011，文件与压缩包已按此命名。团队成员、分工、历史 AI 使用及人工验证情况仍需填写。')
    p.write_text(update(text),encoding='utf-8')
paths=json.loads((build/'docx_outputs.json').read_text(encoding='utf-8'))
paths=[p.replace(old,new) for p in paths]
for p in out.rglob('*.docx'):
    if '归档_' in str(p) or '原始调研材料' in str(p):continue
    d=Document(p)
    paragraphs=list(d.paragraphs)+[par for t in d.tables for row in t.rows for cell in row.cells for par in cell.paragraphs]
    for par in paragraphs:
        for run in par.runs:
            revised=update(run.text)
            if revised!=run.text:run.text=revised
    for rel in d.part.rels.values():
        if rel.is_external:rel._target=rel.target_ref.replace(old,new)
    d.save(p)
(build/'docx_outputs.json').write_text(json.dumps(paths,ensure_ascii=False,indent=2),encoding='utf-8')
# Update only the private validation helper so its next packaging pass uses the supplied tag.
p=build/'verify_submit.py';p.write_text(p.read_text(encoding='utf-8').replace(old,new),encoding='utf-8')
print('Updated filenames, team fields, Markdown links, Word links and package names')
