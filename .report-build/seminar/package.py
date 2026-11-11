from pathlib import Path
import zipfile
root=Path.cwd(); folder=root/'汇报成果'/'需求实践与分析成果研讨'
notes=folder/'02-课堂发言提纲.md'; s=notes.read_text(encoding='utf-8')
s=s.replace('下一步优先验证三件事：采集在不同提交位置故障后是否能无丢失地恢复；并发批准、撤回是否只产生一个合法结果；检索能否保持同贡献、同公开版本和实时权限语义。', '会前先核对SRS引用的用例、活动和状态图与整合版类图、时序是否一致；当前材料有采集任务状态图和时序图，但没有单独的采集活动图，若课程要求每个关键交互都配活动图，再补这一张。之后验证三件事：采集在不同提交位置故障后是否能无丢失地恢复；并发批准、撤回是否只产生一个合法结果；检索能否保持同贡献、同公开版本和实时权限语义。')
notes.write_text(s,encoding='utf-8')
record=folder/'03-研讨决策记录表.md'; s=record.read_text(encoding='utf-8')
s=s.replace('| SRS待补指标 | 确认失败率阈值、恢复时长、公开更新时延及部署条件 |  |  | 更新后的SRS及评审记录 |', '| 需求模型一致性 | 对照SRS引用的用例/活动/状态图、整合类图与三条时序；确认是否需要补采集活动图 |  |  | 模型追踪表、补充图源或确认意见 |\n| SRS待补指标 | 确认失败率阈值、恢复时长、公开更新时延及部署条件 |  |  | 更新后的SRS及评审记录 |')
record.write_text(s,encoding='utf-8')
readme=folder/'README.md'
s=readme.read_text(encoding='utf-8')
s=s.replace('三张原始时序子图。','三张原始时序子图、核心业务类图，以及SRS引用的用例/活动/状态图和Draw.io源文件。')
s=s.replace('`图件/`：报告附录中引用的原始高清图','`图件/`：报告附录中的高清图；`图件/需求建模模型/`保存SRS引用图的PNG和Draw.io源文件')
readme.write_text(s,encoding='utf-8')
zip_path=root/'Submit'/'第9组-需求实践与分析成果研讨.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(folder.rglob('*')):
  if f.is_file(): z.write(f,f.relative_to(folder.parent))
print('zip bytes',zip_path.stat().st_size)
for f in sorted((folder/'图件'/'需求建模模型').glob('*')): print(f.name,f.stat().st_size)
