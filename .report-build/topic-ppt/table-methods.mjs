import {PresentationFile,FileBlob} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('F:/homework/软分/SoftwareAnalyse/需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-需求分析汇报-差异集中版-含演讲稿.pptx'));
console.log('collection',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides.items[0].tables)));
console.log('table',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides.items[0].tables.items[0])));
