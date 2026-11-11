import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
const B=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(B,'../..');
const source=path.join(root,'需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-需求分析汇报-差异集中版.pptx');
const scripts=JSON.parse(await fs.readFile(path.join(B,'speeches-r06.json'),'utf8'));
const p=await PresentationFile.importPptx(await FileBlob.load(source));
if(p.slides.items.length!==scripts.length)throw Error('Slide/script count mismatch');
for(const item of scripts){
 const s=p.slides.items[item.page-1];
 const title=s.shapes.items.find(sh=>sh.name==='主题标题');
 if(String(title.text)!==item.title)throw Error('Title mismatch on slide '+item.page);
 const reference=item.page<=10
  ?'共同任务需求、现有需求分析整合模型与固定检查场景。'
  :'本地整合分析模型与2组GitHub固定提交 b93110b8964e9061469bcfab8d0ced701f3d4526。两组起始需求相同。当前整合稿的采用结论不代表已改写2组原件或通过团队复审。第13页QX细化另参考B5吴星宇个人包v0.9，该个人包不等同于2组整组交付。';
 s.speakerNotes.text='演讲稿\n\n'+item.speech+'\n\n资料来源（不朗读）\n'+reference+'\n配套材料：需求分析/PPT主题汇报稿/PPT逐页内容-差异集中版.md\n2组固定来源：https://github.com/caw111/SoftwareAnalyse/tree/b93110b8964e9061469bcfab8d0ced701f3d4526/前期成果/需求分析';
}
await (await PresentationFile.exportPptx(p)).save(path.join(B,'notes-authored-r06.pptx'));
const total=scripts.reduce((sum,v)=>sum+(v.speech.match(/[\p{Script=Han}\p{L}\p{N}]/gu)||[]).length,0);
const md='# 学术成果分享平台需求分析：逐页演讲稿\n\n对应13页差异集中版PPT。正文约'+total+'字（不含标题与标点），按每分钟220至240字讲述，正文约9.3至10.2分钟，另留约1分钟用于换页和指图，整体预计约10.3至11.2分钟。幻灯片正文不加入计时信息。\n\n'+scripts.map(v=>'## 第'+v.page+'页 '+v.title+'\n\n'+v.speech).join('\n\n')+'\n';
await fs.writeFile(path.join(B,'speech-manuscript-r06.md'),md);
console.log(JSON.stringify({slides:scripts.length,spokenCharacters:total,estimatedMinutesAt220:total/220}));
