import fs from 'node:fs/promises';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
const source='F:/homework/软分/SoftwareAnalyse/需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-需求分析汇报.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
console.log(await p.inspect({kind:'slide,textbox,shape,table',maxChars:4500}));
console.log('shapes',p.slides.items[1].shapes.items.map(sh=>({id:sh.id,name:sh.name,content:String(sh.text),p:sh.position})));
console.log('shape methods',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides.items[1].shapes.items[0])));
console.log('collection methods',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides.items[1].shapes)));
