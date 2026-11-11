from pathlib import Path
import shutil,zipfile
root=Path.cwd(); folder=root/'汇报成果'/'需求实践与分析成果研讨'; dest=folder/'图件'/'整合版全量图件'; dest.mkdir(parents=True,exist_ok=True)
src=root/'需求分析'/'A组-需求分析整合版-v1.1'/'图件'
for f in src.iterdir():
 if f.is_file() and f.suffix.lower() in ('.png','.svg'):
  shutil.copy2(f,dest/f.name)
model_src=root/'需求分析'/'A组-需求分析整合版-v1.1'/'模型源文件'
editable=dest/'可编辑模型源'; editable.mkdir(exist_ok=True)
for f in model_src.glob('*.drawio'): shutil.copy2(f,editable/f.name)
readme=folder/'README.md'; s=readme.read_text(encoding='utf-8')
s=s.replace('核心业务类图，以及SRS引用的用例/活动/状态图和Draw.io源文件。','核心业务类图、整合版全量PNG/SVG图件，以及SRS引用的用例/活动/状态图和Draw.io源文件。')
s=s.replace('`图件/需求建模模型/`保存SRS引用图的PNG和Draw.io源文件','`图件/需求建模模型/`保存SRS引用图的PNG和Draw.io源文件；`图件/整合版全量图件/`保留整合版全套PNG/SVG及相关可编辑Draw.io')
readme.write_text(s,encoding='utf-8')
zip_path=root/'Submit'/'第9组-需求实践与分析成果研讨.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(folder.rglob('*')):
  if f.is_file(): z.write(f,f.relative_to(folder.parent))
with zipfile.ZipFile(zip_path) as z: assert z.testzip() is None
print('graphics copied',sum(1 for p in dest.rglob('*') if p.is_file()),'zip',zip_path.stat().st_size,'entries',len(z.namelist()))
