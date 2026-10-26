import fs from 'node:fs/promises';
import path from 'node:path';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
const file=path.resolve('汇报成果/学术成果分享平台_需求调研与建模_总体汇报.pptx');
const p=await PresentationFile.importPptx(await FileBlob.load(file));
await fs.mkdir('.report-build/final-renders',{recursive:true});
if(p.slides.items.length!==28)throw new Error('Unexpected slide count');
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.export({slide:p.slides.items[i],format:'png',scale:1.5});
 await fs.writeFile(`.report-build/final-renders/slide-${String(i+1).padStart(2,'0')}.png`,new Uint8Array(await png.arrayBuffer()));
}
console.log('Final PPTX: 28 slides rendered');
