import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
const B=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(B,'../..');
const source=path.join(root,'需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-图解汇报版.pptx');
const scripts=JSON.parse(await fs.readFile(path.join(B,'speeches-diagram.json'),'utf8'));
const p=await PresentationFile.importPptx(await FileBlob.load(source));
if(p.slides.items.length!==13||scripts.length!==13)throw Error('Slide/script count mismatch');
for(const item of scripts){
 const s=p.slides.items[item.page-1];
 const title=s.shapes.items.find(x=>x.name==='主题标题');
 if(String(title.text)!==item.title)throw Error('Title mismatch on slide '+item.page);
 const original=String(s.speakerNotes.text);
 const provenance=original.includes('图件来源（不朗读）')?original.split('图件来源（不朗读）')[1].trim():'';
 s.speakerNotes.text='第'+item.page+'页　'+item.title+'\n\n【演讲稿】\n\n'+item.speech+'\n\n【图件来源与资料说明，不朗读】\n'+provenance;
}
await (await PresentationFile.exportPptx(p)).save(path.join(B,'notes-authored-r12.pptx'));
const count=scripts.reduce((a,v)=>a+(v.speech.match(/[\p{Script=Han}\p{L}\p{N}]/gu)||[]).length,0);
const manuscript='# 学术成果分享平台图解版：逐页演讲稿\n\n对应13页图解汇报PPT，可直接按页讲述。正文约'+count+'字，按每分钟220字约10.3分钟，另留约1分钟换页和指图，整体预计约11.3分钟。\n\nPPT中的讲稿位于每页备注区，可在PowerPoint的“备注”或“演示者视图”中查看。只朗读“演讲稿”部分，后面的图件来源用于备查。\n\n'+scripts.map(v=>'## 第'+v.page+'页 '+v.title+'\n\n'+v.speech).join('\n\n')+'\n';
await fs.writeFile(path.join(B,'speech-r12.md'),manuscript);
console.log(JSON.stringify({slides:scripts.length,spokenCharacters:count}));
