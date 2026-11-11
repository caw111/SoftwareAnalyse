import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
import {GlobalFonts} from '@napi-rs/canvas';
const ROOT=process.cwd(), B=path.join(ROOT,'.report-build/third-submit');
const OUT=path.join(ROOT,'Submit/第9组-第三次作业-需求分析');
const SKILL='C:/Users/27872/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
process.env.RUNTIME_NODE_MODULES='C:/Users/27872/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc');
const source=path.join(ROOT,'需求分析/PPT主题汇报稿/演示文稿/学术成果分享平台-图解汇报版-含逐页演讲稿.pptx');
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const S=p.slides.items;
function tx(s,v,x,y,w,h,z=28,b=false,color='#24383B'){
 const sh=s.shapes.add({geometry:'textbox',name:v.slice(0,24),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=v;sh.text.style={typeface:'微软雅黑',fontSize:z,color,bold:b,wrap:'square',autoFit:'none'};sh.text.insets=0;return sh;
}
function clear(i,title){const s=S[i];for(const im of [...s.images.items])im.delete();for(const sh of [...s.shapes.items])sh.delete();for(const t of [...s.tables.items])s.tables.deleteById(t.id);tx(s,title,60,48,1480,80,48,true,'#175D61');tx(s,String(i+1).padStart(2,'0'),1480,850,60,28,19,false,'#657575');return s;}
function box(s,v,x,y,w,h){let sh=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:'#F7F9F8',line:{fill:'#175D61',width:1.5}});sh.text=v;sh.text.style={typeface:'微软雅黑',fontSize:27,color:'#24383B',alignment:'center',verticalAlignment:'middle',autoFit:'none'};sh.text.insets=10;return sh;}
function link(s,a,b){s.shapes.connect(a,b,{kind:'elbow',fromSide:'top',toSide:'bottom',line:{fill:'#175D61',width:2},tail:{type:'none'}});}
const notes=JSON.parse(await fs.readFile(path.join(ROOT,'.report-build/topic-ppt/speeches-diagram.json'),'utf8'));
notes[0].speech='大家好，我们汇报第三次作业的需求分析。平台统一管理论文、专利、项目和获奖，公众可以检索公开成果，科研人员认领门户和确认贡献，管理员负责采集治理与审核。下面先说明核心对象和类关系，再按采集、认领和检索三条业务链解释交互，最后核对前期模型与SRS的一致性，并说明AI使用和实际验证情况。';
{
const s=clear(2,'四类成果怎样共享属性并保留差异');
tx(s,'Work保存共同身份和更新规则，Paper、Patent、Project、Award继承公共属性与操作。',60,150,1480,70,30);
const work=box(s,'«abstract» Work\nworkId、题名、版本、来源证据\napplyVerifiedUpdate()',470,255,660,145);
const cls=[['Paper 论文','DOI、刊物、出版日期'],['Patent 专利申请','辖区、申请号、授权证据'],['Project 科研项目','资助机构、批准号、资助年'],['Award 学术获奖','奖励体系、年度、等级']];
cls.forEach((v,i)=>{let a=box(s,v[0]+'\n'+v[1],60+i*385,510,355,135);link(s,a,work);});
s.shapes.add({geometry:'triangle',name:'UML泛化空心三角',position:{left:788,top:400,width:24,height:22},fill:'#FFFFFF',line:{fill:'#175D61',width:2}});
tx(s,'空心三角指向父类。四个子类完整且互斥，一条规范成果只属于其中一种。',60,705,1480,65,29);
tx(s,'Patent与PatentDocument采用关联，一件申请可以对应多份公布或授权文献。',60,785,1480,50,28,true,'#175D61');
notes[2].speech='四类成果共享规范标识、题名、版本和来源证据，因此用抽象类Work组织公共属性与更新操作。论文保留DOI和出版信息，专利保留申请身份和授权证据，项目保留资助机构及批准号，获奖保留奖励体系与年度。四类互斥，一条成果只属于其中一种。专利文献另外建模，同一申请可以对应公布和授权文献，不能当成两件成果。公开版本和版本条目采用组合，条目属于某个版本，公共成果本身继续独立保存。';
}
for(const sh of S[4].shapes.items){if(String(sh.text).startsWith('固定窗口三页'))sh.text='一次采集范围内有三页数据：第一页已保存，第二页失败，重试后继续处理。';}
notes[9].speech=notes[9].speech.replace('下面集中说明两组如何整合。','下面核对这些分析对象和交互与前期需求的对应关系。');
{
const s=clear(10,'业务对象从哪些需求中识别出来');
const groups=[['人物与认领','账号、学者、学者门户、门户管理授权\n认领申请、门户审核记录','调研场景二；UC1.3、UC3.1、UC3.5'],['成果与关系','成果、论文、专利申请、专利文献、专利家族\n项目、获奖、贡献、机构、任职、当时署名\n学术领域、领域标注','调研场景一、三至五；UC2.1～2.3、UC3.2～3.3'],['采集与更新','数据源、原始记录、采集任务、采集观测\n来源映射、更新记录、治理复核\n公开版本、公开版本条目','调研场景六；UC5.1、UC5.3～5.5']];
groups.forEach((g,i)=>{let y=210+i*205;tx(s,g[0],60,y,280,55,32,true,'#175D61');tx(s,g[1],365,y,1160,110,29);tx(s,g[2],365,y+120,1160,45,24,false,'#657575');});
tx(s,'共28个业务类。每个类的属性、操作和SRS依据见报告及对象对应表。',60,825,1420,40,25);
notes[10].speech='对象识别按调研中的业务事实展开。认领场景要求把账号、学者、门户、申请和授权分开。四类成果及贡献关系来自检索、补录和纠错场景，历史署名机构不能被当前任职替代。来源更新场景则要求保存任务、原文、每次观测和后续更新工作。我们共保留二十八个业务类，完整属性、操作和SRS依据都在对象字典及对应表中。类的数量不等于数据库表的数量。';
}
{
const s=clear(11,'类图和时序图怎样承接前期模型');
const rows=[['门户认领','UC3.1／UC3.5／UC5.2','申请与授权对象','CL、CX消息','六个认领状态'],['采集入库','UC5.1／UC5.3／UC5.4','来源与任务对象','M、N、X消息','六个采集状态'],['检索与详情','UC2.1～UC2.3','贡献与公开版本','Q、QX消息','同版内容和当前权限']];
rows.forEach((r,i)=>{let y=225+i*175;tx(s,r[0],60,y,300,65,34,true,'#175D61');tx(s,r[1],365,y,520,55,30);tx(s,r[2]+'　'+r[3],365,y+65,1080,55,29);tx(s,r[4],1130,y,410,65,29);});
tx(s,'用例确定目标，活动图解释分支，状态图约束迁移。类图和时序图落实对象职责。',60,790,1480,65,28,true,'#175D61');
notes[11].speech='一致性按业务逐条检查。门户认领对应SRS的认领、本人申请和后台审核用例，活动步骤由CL与CX展开，状态仍采用六态。认领对应前期门户认领审核活动图和认领申请状态图。采集对应来源管理、清洗和增量更新，M、N、X承接正常、清洗和故障路径，并与数据采集任务状态机核对。检索与详情对应UC2.1到2.3，贡献关系限定匹配语义，公开版本约束同版读取。前期图中的局部用例编号按名称映射到SRS，不直接混用。三十二项设计场景记录了核对输入与预期，但还不是运行测试。';
}
{
const s=clear(12,'AI使用与实际验证情况');
const cols=[['声明','Codex辅助识别对象、补写交互\n整理追踪关系和报告排版。\n已有图件和源文件随包保留。'],['理解','需要解释继承与组合的依据\n授权与贡献、断点与成功水位\n同版读取与实时权限的区别。'],['责任','已有用户反馈已落实。\n静态检查和版式检查有记录。\n成员交叉复审尚无新增签字。']];
cols.forEach((v,i)=>{tx(s,v[0],60+i*510,260,460,70,38,true,'#175D61');tx(s,v[1],60+i*510,380,460,250,29);});
tx(s,'本次未开展真实访谈或平台运行测试。AI辅助修订与人工复核分别记录。',60,755,1480,75,29);
notes[12].speech='最后说明AI使用。Codex参与对象整理、认领和检索交互补建、追踪关系及报告排版，原始材料与历史记录保留。用户提出过两组共同基准、减少抽象表格、使用原图及解释固定窗口等要求，我们据此修订。自动静态核对和版式检查可以确认材料结构与模型定位，不能替代成员理解和真实运行。现有记录没有新增成员交叉复审签字，因此如实保留这一状态。最终采用的规则和提交责任仍由成员承担。谢谢大家。';
}
for(let i=0;i<S.length;i++){const title=S[i].shapes.items.find(x=>x.name==='主题标题')?.text;notes[i].title=title?String(title):[,,,,,,,,,,'业务对象从哪些需求中识别出来','类图和时序图怎样承接前期模型','AI使用与实际验证情况'][i]||notes[i].title;S[i].speakerNotes.text='第'+(i+1)+'页\n【演讲稿】\n'+notes[i].speech+'\n\n【资料来源，不朗读】\n本包需求分析报告、业务对象字典、跨模型追踪表、AI历史记录。原图来源为本组A2类图、A3采集图及已有认领检索补图。第3页为按同一模型重绘的继承示意，详细关系以随附原生图源为准。';}
notes[2].title='四类成果怎样共享属性并保留差异';
await (await PresentationFile.exportPptx(p)).save(path.join(B,'deck-candidate.pptx'));
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
await finalizePresentation({workspaceDir:ROOT,candidatePath:path.join(B,'deck-candidate.pptx'),finalPath:path.join(B,'validated-r2/deck.pptx'),pythonExecutable:'C:/Users/27872/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-heading-fit'],explicitTotalSlideCount:13,requiredNativeTableOwnerSlides:[],fontPolicy:{basis:'reference',families:['微软雅黑'],referencePath:source,referenceSha256:createHash('sha256').update(await fs.readFile(source)).digest('hex')},verifyArtifactToolImport:true,receiptPath:path.join(B,'deck-validation-r2.json')});
await fs.copyFile(path.join(B,'validated-r2/deck.pptx'),path.join(OUT,'汇报材料/02-需求分析汇报.pptx'));
await fs.writeFile(path.join(OUT,'汇报材料/逐页演讲稿.md'),'# 需求分析汇报逐页演讲稿\n\n'+notes.map(v=>'## 第'+v.page+'页 '+v.title+'\n\n'+v.speech).join('\n\n'));
console.log('PPT validated. Slides: '+S.length);


