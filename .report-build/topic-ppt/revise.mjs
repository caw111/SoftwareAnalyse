import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
import {GlobalFonts} from '@napi-rs/canvas';

const B=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(B,'../..');
const SOURCE=path.join(ROOT,'需求分析/PPT主题汇报稿');
const SKILL='C:/Users/27872/.codex/plugins/cache/openai-primary-runtime/presentations/26.1025.11240/skills/presentations';
const PYTHON='C:/Users/27872/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/27872/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const REV=process.env.DECK_REVISION||'r01';
const PREVIEW=path.join(B,REV);await fs.mkdir(PREVIEW,{recursive:true});
const VALIDATED=path.join(B,`validated-${REV}`);await fs.mkdir(VALIDATED,{recursive:true});
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc');
const FONT='Microsoft YaHei';
const C={ink:'#24383B',teal:'#175D61',light:'#E5EFED',purple:'#705782',muted:'#657575',line:'#CBD7D5',paper:'#FFFFFF',wash:'#F7F9F8',warn:'#A65C28'};
const original=await fs.readFile(path.join(SOURCE,'PPT逐页内容.md'),'utf8');
const split=original.split(/^## 第\d+页 /m).slice(1);
const originalPages=split.map(x=>({title:x.split('\n')[0],body:x.slice(x.indexOf('\n')).trim()}));
const trace=[];

function text(s,value,x,y,w,h,size=28,opt={}){
 const sh=s.shapes.add({geometry:'textbox',name:opt.name||String(value).slice(0,28),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=value;sh.text.style={typeface:FONT,fontSize:size,color:opt.color||C.ink,bold:!!opt.bold,alignment:opt.align||'left',verticalAlignment:opt.valign||'top',autoFit:'none',wrap:'square'};sh.text.insets=0;return sh;
}
function node(s,label,x,y,w,h,opt={}){
 const sh=s.shapes.add({geometry:'rect',name:label,position:{left:x,top:y,width:w,height:h},fill:opt.fill||C.wash,line:{fill:opt.color||C.teal,width:1.5}});
 sh.text=label;sh.text.style={typeface:FONT,fontSize:opt.size||28,color:opt.color||C.ink,bold:!!opt.bold,alignment:'center',verticalAlignment:'middle',autoFit:'none'};sh.text.insets=10;return sh;
}
function connect(s,a,b,opt={}){return s.shapes.connect(a,b,{kind:opt.kind||'elbow',fromSide:opt.from||'right',toSide:opt.to||'left',line:{fill:opt.color||C.teal,width:2},tail:{type:opt.arrow===false?'none':'arrow',width:'med',length:'med'}});}
function table(s,values,x,y,width,cols,heights,size=28){
 const height=heights.reduce((a,b)=>a+b,0);
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width,height,columnWidths:cols,values});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:C.paper,textStyle:{typeface:FONT,fontSize:size,color:C.ink},margins:{left:16,right:16,top:10,bottom:10},anchor:'center'});
 t.borders.assign({fill:C.line,width:0.8});
 for(let i=0;i<values.length;i++){
   t.rows[i].height=heights[i];
   t.cells.block({row:i,column:0,rowCount:1,columnCount:values[0].length}).assign({fill:i===0?C.teal:(i%2?C.paper:C.wash),textStyle:{typeface:FONT,fontSize:size,color:i===0?'#FFFFFF':C.ink,bold:i===0}});
 }
 return t;
}
function base(p,title,num){
 const s=p.slides.add();s.background.fill=C.paper;
 text(s,title,60,48,1480,76,48,{bold:true,color:C.teal,name:'主题标题'});
 text(s,String(num).padStart(2,'0'),1480,850,60,28,19,{align:'right',color:C.muted});
 return s;
}
function footer(s,t,y=752,h=85,size=25){text(s,t,60,y,1480,h,size,{color:C.ink});}
function note(s,i,extra=''){
 s.speakerNotes.text=originalPages[i-1].body+'\n\n来源：1组为当前整合模型，2组为GitHub固定提交 b93110b8964e9061469bcfab8d0ced701f3d4526 的需求分析交付。两组依据共同需求开展分析。\n'+
 '本地原文：'+path.join(SOURCE,'PPT逐页内容.md')+'\n'+
 '2组原文：https://github.com/caw111/SoftwareAnalyse/tree/b93110b8964e9061469bcfab8d0ced701f3d4526/前期成果/需求分析\n'+extra;
}
function sources(s,t,y=810){text(s,t,60,y,1420,60,23,{color:C.muted});}

const sourceDeck=path.join(SOURCE,'演示文稿/学术成果分享平台-需求分析汇报.pptx');
const p=await PresentationFile.importPptx(await FileBlob.load(sourceDeck));
const changes=[];
// Delete the comparison text from the existing ten slides, retaining native
// tables, diagrams and the original positions of all business content.
for(const [i,s] of p.slides.items.entries()){
  for(const sh of [...s.shapes.items]){
    const content=String(sh.text);
    if(/1组|2组|两组/.test(content)){
      changes.push({slide:i+1,removed:content});
      sh.delete();
    }
  }
  const body=originalPages[i].body.split(/\n\s*\n/).filter(x=>!/1组|2组|两组|Group2|B5/.test(x)).join('\n\n');
  s.speakerNotes.text=body+'\n\n资料来源：共同任务需求及现有整合分析模型。源稿：'+path.join(SOURCE,'PPT逐页内容.md')+'。模型对照集中在第11至13页。';
}
text(p.slides.items[0],'论文、专利、项目与获奖统一组织，围绕成果数据、门户管理和公开查询建立业务模型。',60,213,1480,76,30);
// Business concepts use one set of labels in the requirements section.
for(const [oldValue,newValue] of [['登录账号\nAccount / User','登录账号\n独立身份与权限'],['现实人物\nScholar','现实人物\n学者身份与来源'],['规范成果\nWork / AcademicOutcome','规范成果\n统一成果身份']]){
 const sh=p.slides.items[1].shapes.items.find(x=>String(x.text)===oldValue);
 if(!sh)throw Error('Missing original concept: '+oldValue);
 sh.text=newValue;
}
footer(p.slides.items[1],'账号、现实人物与规范成果分别标识。门户认领建立管理授权，成果贡献按具体关系确认。',746,82,27);
footer(p.slides.items[2],'授权需要保存生效、撤销和版本历史。组合表达业务归属，物理删除仍须遵守历史与审计保留规则。',740,86,27);
sources(p.slides.items[3],'隔离和待复核必须保留原因、来源及处理计数。技术错误要进入恢复或人工处理，不能静默丢弃。',792);
footer(p.slides.items[4],'推进分页断点前，必须可靠保存对应数据或待处理工作。整窗完成与后续公开发布分别记录。',700,90,28);
sources(p.slides.items[5],'补交材料后，重新核验资格与材料版本。批准只授予门户管理权，候选成果仍须逐项确认。',791);
sources(p.slides.items[6],'批准必须整体生效或整体回滚。发生唯一性或版本冲突时，保留已提交决定并返回冲突原因。',818);
text(p.slides.items[9],'按同一组业务预期核对模型，发现的问题回写类图、时序和需求记录。',60,745,1480,66,31,{bold:true,color:C.teal});
footer(p.slides.items[8],'返回前复验权限修订。权限发生变化时作废本次结果及计数，保留查询条件并提示重试。',692,88,28);

const reference='对照来源：本地整合模型与GitHub固定提交 b93110b8964e9061469bcfab8d0ced701f3d4526。共同起始需求相同，文档版本编号不用于解释任务基准差异。';
const comparisonPages=[];
function comparisonNote(s,body){
  s.speakerNotes.text=body+'\n\n'+reference+'\n详细对照：'+path.join(ROOT,'需求分析/A组-需求分析整合版-v1.1/支撑材料/Group2与B5对照及修订.md')+'。该对照文档早期基线说法与用户后续澄清不一致，本PPT遵循用户明确说明：两组起始需求相同。\n2组原文：https://github.com/caw111/SoftwareAnalyse/tree/b93110b8964e9061469bcfab8d0ced701f3d4526/前期成果/需求分析\n处理结论说明当前整合稿的采用方式，不代表已改写2组原件或通过团队复审。';
}
// 11. Object/relationship differences, with a concrete integration decision.
{
 const s=base(p,'两组差异：对象与关系如何整合',11);
 text(s,'起始需求相同。1组展开28个类，2组使用15个类，主要区别是职责和历史是否独立成类。',60,145,1480,67,28);
 const rows=[
  ['对照项','1组表达','2组表达','整合处理与目的'],
  ['门户授权','独立门户与授权对象\n记录绑定历史','在Scholar及管理关联中\n承载门户与绑定','保留独立授权记录\n明确生效、撤销和双向有效唯一'],
  ['贡献与机构','ContributionAffiliation\n单列贡献机构与证据','OutcomeContributor\n保存署名机构与证据','统一按同一条贡献匹配人物与机构\n防止借用其他作者的机构'],
  ['来源与观测','独立记录采集观测\n与归并映射','来源记录与任务之间\n通过观测关系表达','保留不可变原文与每次采集结果\n重复观测可以追溯，成果不重复建立'],
  ['公开版本','PublicRelease与\nReleaseEntry独立建模','通过公开版本与同版\n读取的交互职责表达','以明确的公开版本标识关联\n索引、统计和条目读取']
 ];
 table(s,rows,60,233,1480,[190,350,350,590],[56,112,112,112,112],25);
 footer(s,'类名按职责建立映射，例如Account对应User、Work对应AcademicOutcome。类的数量不作为优劣标准。',774,74,27);
 const body='## 第11页 两组差异：对象与关系如何整合\n\n'+rows.map(r=>'| '+r.map(v=>v.replaceAll('\n','；')).join(' | ')+' |').join('\n')+'\n\n两组起始需求相同。1组28类、2组15类，数量反映展开粒度。当前整合保留明确的授权历史、贡献机构证据、采集观测和公开版本对象，以便核对唯一性、可追溯和同版读取。Account对应User，Work对应AcademicOutcome。';
 comparisonNote(s,body);comparisonPages.push(body);
}
// 12. State names and transient steps are resolved explicitly.
{
 const s=base(p,'两组差异：状态名称与迁移如何统一',12);
 text(s,'以下给出当前整合稿采用的状态规则。业务终态、技术执行过程和审核占用分别记录。',60,145,1480,68,28);
 const rows=[
  ['对照项','1组表达','2组表达','当前整合采用的规则'],
  ['认领状态','六个业务状态\n验证和审核占用为内部过程','九状态，额外包含\nPENDING_VERIFICATION\nVERIFYING\nUNDER_REVIEW','沿用六个业务状态\n验证结果和审核占用用内部字段记录\n材料变化必须重新验证，终审检查版本'],
  ['采集成功','SUCCEEDED','SUCCESS','成功状态统一命名为SUCCEEDED\n只在整窗完成并校验后进入'],
  ['重试耗尽','进入STOPPED','保持FAILED\n人工放弃后才STOPPED','预算耗尽进入STOPPED并保留原因\n不可重试故障保留FAILED供人工处理\n人工停止在安全退出后生效']
 ];
 table(s,rows,60,233,1480,[190,350,350,590],[56,146,100,146],25);
 text(s,'统一后的认领状态',60,715,1480,42,29,{bold:true,color:C.teal});
 text(s,'DRAFT、PENDING_REVIEW、NEED_MORE_INFO、APPROVED、REJECTED、WITHDRAWN',60,775,1480,52,25);
 const body='## 第12页 两组差异：状态名称与迁移如何统一\n\n'+rows.map(r=>'| '+r.map(v=>v.replaceAll('\n','；')).join(' | ')+' |').join('\n')+'\n\n认领六状态为DRAFT、PENDING_REVIEW、NEED_MORE_INFO、APPROVED、REJECTED、WITHDRAWN。保留2组验证和占用的必要业务检查，将其表达为内部执行信息。验证超时返回可恢复原因，不能直接变成业务驳回。整窗失败不推进成功水位。统一状态需要同步维护枚举、状态迁移表、时序图和验收场景，2组原件按来源保留。';
 comparisonNote(s,body);comparisonPages.push(body);
}
// 13. Commit boundaries and search detail are integrated by their guarantees.
{
 const s=base(p,'两组差异：事务与检索如何统一处理',13);
 text(s,'整合时保留各自原图，明确共同业务约束，并将缺少的提交边界和失败分支写入模型。',60,145,1480,68,28);
 const rows=[
  ['对照项','1组表达','2组表达','整合处理与检查方式'],
  ['采集提交','来源、观测、处理登记\n与页断点一起提交\n规范入库另设事务','规范成果、后续登记\n与页断点一起提交','沿用分阶段提交，可靠登记待处理工作\n规范入库失败后继续处理\n用“第一页成功、第二页失败”检查恢复'],
  ['检索交互','主图与QX子交互展开\n总数、越界和返回前\n权限复验','主图表达固定公开版本\n实时权限和同版ID读取','保留同版读取契约，补全QX细节\n先按权限计数，再分页\n权限变化作废结果，旧版失效提示刷新'],
  ['检查材料','当前整合记录\n32项设计场景','整组交付提供\n15项检查场景','按需求去重并补齐预期结果\n同贡献、并发、恢复和版本分别核对\n设计走查不计作真实运行通过']
 ];
 table(s,rows,60,233,1480,[190,350,350,590],[56,145,145,145],25);
 footer(s,'当前整合已采用上述设计处理。2组原件保留，状态和交互仍须同步复审，真实行为在实现后验证。',780,67,27);
 const body='## 第13页 两组差异：事务与检索如何统一处理\n\n'+rows.map(r=>'| '+r.map(v=>v.replaceAll('\n','；')).join(' | ')+' |').join('\n')+'\n\n采集采用1组分阶段事务，断点前可靠保存来源和处理登记，规范入库及后续工作可靠提交。两种事务设计均以可靠恢复为目标，不声称必须使用同一种物理事务划分。授权保持批准、绑定、决定与审计原子生效。检索保留2组固定release与同版读取职责，使用当前整合稿Q/QX补齐分页和返回前权限校验。当前QX细化参考另外提供的B5吴星宇个人包v0.9，不将B5个人交付等同于2组整组作业。32项与15项为不同来源的设计检查记录，不能直接相加作为运行通过证据。';
 comparisonNote(s,body);comparisonPages.push(body);
}

await fs.mkdir(PREVIEW,{recursive:true});
for(const [i,s] of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(PREVIEW,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 await fs.writeFile(path.join(PREVIEW,`slide-${String(i+1).padStart(2,'0')}.layout.json`),await (await s.export({format:'layout'})).text());
}
const candidate=path.join(B,`main-${REV}.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log('Rendered and exported '+p.slides.items.length+' slides');
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:path.join(VALIDATED,'main.pptx'),pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-bullet-geometry','--validate-heading-fit',...Array.from({length:13},(_,i)=>['--require-native-table-slide',String(i+1)]).flat()],explicitTotalSlideCount:13,requiredNativeTableOwnerSlides:Array.from({length:13},(_,i)=>i+1),fontPolicy:{basis:'reference',families:[FONT],referencePath:sourceDeck,referenceSha256:createHash('sha256').update(await fs.readFile(sourceDeck)).digest('hex')},verifyArtifactToolImport:true,receiptPath:path.join(B,`receipt-main-${REV}.json`)});
const cleanPages=originalPages.map((page,i)=>'## 第'+(i+1)+'页 '+page.title+'\n\n'+page.body.split(/\n\s*\n/).filter(x=>!/1组|2组|两组|Group2|B5/.test(x)).join('\n\n'));
cleanPages[0]=cleanPages[0].replace('\n\n| 使用者','\n\n平台统一组织论文、专利、项目与获奖，围绕成果数据、门户管理和公开查询建立对象与交互模型。\n\n| 使用者');
await fs.writeFile(path.join(B,`content-${REV}.md`),'# 学术成果分享平台需求分析：差异集中说明版\n\n'+[...cleanPages,...comparisonPages].join('\n\n'));
await fs.writeFile(path.join(B,`changes-${REV}.json`),JSON.stringify({source:sourceDeck,slides:13,comparisonSlides:[11,12,13],removed:changes},null,2));
console.log('Finalized '+path.join(VALIDATED,'main.pptx'));
