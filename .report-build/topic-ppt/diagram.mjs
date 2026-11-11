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

const input=path.join(SOURCE,'演示文稿/学术成果分享平台.pptx');
const p=await PresentationFile.importPptx(await FileBlob.load(input));
const used=[];
const blobs=new Map();
for(const [i,s] of p.slides.items.entries()){
 for(const t of [...s.tables.items])s.tables.deleteById(t.id);
 for(const sh of [...s.shapes.items])if(sh.name!=='主题标题'&&!(String(sh.text)===String(i+1).padStart(2,'0')&&sh.position.top>=840))sh.delete();
}
async function fig(s,group,name,roi,frame,desc){
 const file=path.join(SOURCE,'图件',group,name+'.png');
 if(!blobs.has(file))blobs.set(file,await fs.readFile(file));
 const blob=blobs.get(file),sw=blob.readUInt32BE(16),sh=blob.readUInt32BE(20);
 const [x,y,w,h]=roi;
 if(x<0||y<0||x+w>sw||y+h>sh)throw Error('Invalid figure crop '+name+': '+roi);
 const scale=Math.min(frame[2]/w,frame[3]/h),dw=w*scale,dh=h*scale;
 const left=frame[0]+(frame[2]-dw)/2,top=frame[1];
 s.images.add({blob,contentType:'image/png',alt:desc+'；'+group+'原图局部：'+name,fit:'cover',crop:{left:x/sw,top:y/sh,right:(sw-x-w)/sw,bottom:(sh-y-h)/sh},position:{left,top,width:dw,height:dh}});
 used.push({slide:p.slides.items.indexOf(s)+1,group,name,file,roi,sourceSize:[sw,sh],frame:[left,top,dw,dh],sha256:createHash('sha256').update(blob).digest('hex')});
}
async function vectorFocus(s,name,view,clips,frame,desc){
 const file=path.join(SOURCE,'图件/1组',name+'.svg');
 const originalSvg=await fs.readFile(file,'utf8');
 const inside=originalSvg.replace(/^[\s\S]*?<svg\b[^>]*>/,'').replace(/<\/svg>\s*$/,'');
 const [x,y,w,h]=view;
 const clip=clips.map(v=>`<rect x="${v[0]}" y="${v[1]}" width="${v[2]}" height="${v[3]}"/>`).join('');
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${w}" height="${h}" viewBox="${view.join(' ')}"><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="white"/><defs><clipPath id="focus">${clip}</clipPath></defs><g clip-path="url(#focus)">${inside}</g></svg>`;
 const factor=Math.min(frame[2]/w,frame[3]/h),dw=w*factor,dh=h*factor;
 s.images.add({svg,alt:desc+'；原SVG中保留相关类框和既有连线的局部',fit:'contain',position:{left:frame[0]+(frame[2]-dw)/2,top:frame[1],width:dw,height:dh}});
 used.push({slide:p.slides.items.indexOf(s)+1,group:'1组',name,file,roi:view,clipRegions:clips,kind:'original-svg-focus',sha256:createHash('sha256').update(originalSvg).digest('hex')});
}
function heading(s,t,y=150){text(s,t,60,y,1480,62,29,{color:C.ink});}
function caption(s,t,x,y,w=1480,size=28){text(s,t,x,y,w,65,size,{color:C.ink});}
function emphasis(s,t,y=785){text(s,t,60,y,1480,60,29,{color:C.teal,bold:true});}
const S=p.slides.items;
// Scope has no table. The following pages use original UML crops.
{
 const s=S[0];heading(s,'统一组织论文、专利、项目与获奖，明确数据处理、门户管理与公开查询的边界。');
 const items=[['采集入库','外部响应如何变成\n有来源依据的规范成果'],['门户认领审核','证明如何核验\n管理授权如何正确生效'],['检索请求处理','条件如何匹配\n列表、总数与详情如何一致']];
 items.forEach((v,i)=>{text(s,v[0],60+i*510,310,460,70,38,{bold:true,color:C.teal});text(s,v[1],60+i*510,420,460,145,32);});
 caption(s,'公众读取允许公开的内容；科研人员确认门户与贡献；管理员按对象权限采集、治理和审核。',60,675,1480,29);
 emphasis(s,'门户管理权与成果贡献分别确认',785);
}
{
 const s=S[1];heading(s,'直接看类图中的属性与操作：账号、现实学者和规范成果分别具有稳定身份。');
 await fig(s,'1组','02-局部01-账号学者与门户授权',[574,73,652,434],[60,240,460,375],'平台账号Account原始类框');
 await fig(s,'1组','02-局部01-账号学者与门户授权',[1852,1610,652,434],[570,240,460,375],'来源学者Scholar原始类框');
 await fig(s,'1组','02-局部03-贡献机构与领域关系',[73,1267,652,514],[1080,240,460,375],'规范成果Work原始类框');
 caption(s,'身份状态、科研资格\n决定能否申请和操作',60,660,460,29);
 caption(s,'标识、别名与身份证据\n用于区分同名人物',570,660,460,29);
 caption(s,'规范身份、版本与证据\n支持归并和可靠更新',1080,660,460,29);
 emphasis(s,'学者可以先于账号存在；同一成果可由多位贡献者分别确认',785);
}
{
 const s=S[2];heading(s,'四类成果共享公共身份，类型专属信息单独保留。这里放大专利申请与文献的关系。');
 await vectorFocus(s,'02-局部02-四类成果与专利身份',[500,730,860,290],[[508,813,333,202],[1016,737,334,222],[839,845,179,80]],[60,235,1480,490],'Patent与PatentDocument完整类框、原始关联和多重性');
 emphasis(s,'一件专利申请可以对应多份文献，申请级成果仍计为一件',775);
}
{
 const s=S[3];heading(s,'清洗子交互的三个结果分支：规范入库、待复核、隔离。');
 await fig(s,'1组','03a-清洗去重子交互',[620,100,1545,95],[60,225,1480,95],'清洗匹配、业务数据和复核隔离参与者');
 await fig(s,'1组','03a-清洗去重子交互',[620,1380,1545,145],[60,330,1480,140],'N07规范成果与来源原子写入');
 await fig(s,'1组','03a-清洗去重子交互',[620,1590,1545,145],[60,490,1480,140],'N08弱证据或冲突进入待复核');
 await fig(s,'1组','03a-清洗去重子交互',[620,1790,1545,145],[60,650,1480,140],'N09不合法记录隔离并保留原因');
 text(s,'同一合法DOI且无冲突时归并；相似题名只进入候选复核',60,815,1480,35,25,{color:C.teal,bold:true});
}
{
 const s=S[4];heading(s,'固定窗口三页：第一页已提交，第二页失败，恢复后从第二页继续。');
 await fig(s,'1组','03b-停止重试子交互',[600,100,1565,95],[60,225,1480,90],'任务控制器、执行器和业务数据单元参与者');
 caption(s,'X06　失败保留断点，不推进整窗成功水位',60,340,1480,28);
 await fig(s,'1组','03b-停止重试子交互',[600,1000,1565,135],[60,390,1480,130],'X06失败记录与成功水位约束');
 caption(s,'X07—X08　预算内重试，取得新的有效执行尝试后恢复',60,550,1480,28);
 await fig(s,'1组','03b-停止重试子交互',[600,1200,1565,245],[60,595,1480,235],'X07重试登记与X08从断点恢复');
}
{
 const s=S[5];heading(s,'已提交的认领申请进入审核，原图明确区分补充、驳回和拟批准分支。');
 await fig(s,'1组','05-门户认领审核时序图',[0,140,1560,105],[125,220,1350,100],'认领主图审核参与者');
 await fig(s,'1组','05-门户认领审核时序图',[0,1965,1560,480],[125,350,1350,420],'CL14补充、CL15驳回及批准调用原子授权子交互');
 emphasis(s,'证明材料默认私有；补交更新材料版本；门户批准不自动确认成果',790);
}
{
 const s=S[6];heading(s,'原子授权子交互：状态、管理绑定、审核决定和审计必须共同提交。');
 await fig(s,'1组','05a-认领原子授权与撤回子交互',[520,140,1040,105],[60,230,1030,110],'批准事务相关参与者');
 caption(s,'CX04 状态改为APPROVED，再创建授权并共同提交',60,365,1030,27);
 await fig(s,'1组','05a-认领原子授权与撤回子交互',[520,780,1040,290],[60,420,1030,325],'CX04申请批准、CX05授权、CX06决定审计及共同提交');
 text(s,'同读版本7',1150,255,390,50,31,{bold:true,color:C.teal});
 caption(s,'撤回先提交\n旧批准冲突失败',1150,355,390,30);
 caption(s,'批准先提交\n旧撤回冲突失败\n解绑另走授权撤销',1150,535,390,30);
 emphasis(s,'任一步失败整体回滚或拒绝，不能留下部分生效的管理授权',790);
}
{
 const s=S[7];
 await vectorFocus(s,'02-局部03-贡献机构与领域关系',[520,135,840,495],[[527,380,334,244],[1016,141,334,223],[860,330,158,108]],[60,170,1100,660],'Contribution与ContributionAffiliation完整类框及当时署名关系');
 text(s,'同一贡献\n匹配人物和机构',1220,175,320,100,29,{bold:true,color:C.teal});
 text(s,'查询A01与I01\nR06中：\nA01署名I03\nA03署名I01',1220,330,320,200,29);
 text(s,'R06不命中',1220,595,320,65,34,{bold:true,color:C.warn});
 text(s,'正确命中：\nR01、R04、R07',1220,710,320,100,27);
}
{
 const s=S[8];heading(s,'同一公开版本下，先按权限得到允许集合，再统一计算列表、总数和分面。');
 await fig(s,'1组','06a-检索权限计数与分页子交互',[0,140,1560,105],[60,220,1480,100],'检索控制、权限、索引与公开条目参与者');
 await fig(s,'1组','06a-检索权限计数与分页子交互',[0,690,1560,280],[60,345,1480,270],'QX04共同允许集合与同版读视图');
 caption(s,'返回前权限变化：作废结果和计数，明确要求重试',60,660,1480,28);
 await fig(s,'1组','06a-检索权限计数与分页子交互',[0,1940,1560,130],[60,710,1480,125],'权限变化后不返回旧total或部分列表');
}
{
 const s=S[9];heading(s,'把预期行为直接落到消息与分支上，再用固定场景核对。');
 caption(s,'重复采集：清洗匹配器（左）调用业务数据单元（中）',60,250,1480,29);
 await fig(s,'1组','03a-清洗去重子交互',[640,715,1525,115],[60,300,1480,110],'N04重复采集仅记录观测并复用结果');
 caption(s,'失败恢复：执行器（中）向任务控制器（左）报告失败',60,455,1480,29);
 await fig(s,'1组','03b-停止重试子交互',[600,1000,1565,135],[60,505,1480,128],'X06失败不推进水位');
 caption(s,'检索控制复验权限：变化时作废结果和旧计数，保留条件再重试',60,650,1480,29);
 await fig(s,'1组','06a-检索权限计数与分页子交互',[0,1940,1560,130],[60,700,1480,125],'QX权限变化分支');
}
{
 const s=S[10];heading(s,'起始需求相同。1组28类、2组15类，主要差别是职责与历史是否独立成类。');
 text(s,'1组：独立的门户管理授权',60,250,700,60,31,{bold:true,color:C.teal});
 text(s,'2组：门户资料归入学者对象',835,250,700,60,31,{bold:true,color:C.purple});
 await fig(s,'1组','02-局部01-账号学者与门户授权',[77,1614,644,426],[60,335,700,390],'1组PortalAuthorization含有效期、撤销原因与操作');
 await fig(s,'2组','01_核心业务类图',[1500,195,524,390],[835,335,700,390],'2组Scholar及有效管理关联多重性，门户资料归入学者');
 emphasis(s,'整合保留独立授权历史，并显式关联贡献机构、采集观测与公开版本',790);
}
{
 const s=S[11];heading(s,'当前整合沿用六个认领业务状态，验证结果与审核占用使用内部字段记录。');
 text(s,'1组：六态，校验通过后待审核',60,250,700,60,30,{bold:true,color:C.teal});
 text(s,'2组：九态，验证步骤进入业务状态',835,250,700,60,30,{bold:true,color:C.purple});
 caption(s,'认领控制（左）向申请存储（右）提交',60,310,700,24);
 caption(s,'控制（左）／验证（中）／申请存储（右）',835,305,700,24);
 await fig(s,'1组','05-门户认领审核时序图',[880,920,670,115],[60,365,700,160],'1组CL06直接提交至PENDING_REVIEW');
 await fig(s,'2组','03_门户认领审核时序图',[1280,635,1100,220],[835,350,700,160],'2组步骤4PENDING_VERIFICATION与步骤5VERIFYING');
 await fig(s,'2组','03_门户认领审核时序图',[1280,1030,1100,95],[835,515,700,90],'2组步骤7PENDING_REVIEW');
 caption(s,'成功名称统一为SUCCEEDED，整窗完成并校验后才进入成功。',60,680,1480,29);
 emphasis(s,'预算耗尽进入STOPPED并留因；不可重试故障保留FAILED供人工处理',790);
}
{
 const s=S[12];heading(s,'采集的事务边界不同，整合时以可靠登记和失败后可恢复为共同约束。');
 text(s,'1组：来源、观测、处理登记与页断点先可靠提交',60,240,1480,60,30,{bold:true,color:C.teal});
 caption(s,'生命线从左到右：执行器、外部数据源、原文存储、业务数据单元',60,295,1480,24);
 await fig(s,'1组','03-采集入库时序图',[1350,1420,1410,200],[60,335,1480,200],'1组M11页事务及M12提交后推进');
 text(s,'2组：规范成果、后续登记与断点同事务提交',60,570,1480,55,30,{bold:true,color:C.purple});
 caption(s,'清洗归并服务（左）写入业务存储（右）',60,625,700,24);
 await fig(s,'2组','02_数据采集入库时序图',[1800,1290,590,230],[60,665,700,155],'2组步骤9与10规范成果及断点同事务');
 caption(s,'整合采用分阶段可靠登记。\n检索保留同版契约，补齐QX异常分支。',835,640,700,29);
}
const speechFile=path.join(B,'speeches-diagram.json');
const speeches=JSON.parse(await fs.readFile(speechFile,'utf8'));
for(const item of speeches){
 const s=S[item.page-1],figures=used.filter(v=>v.slide===item.page);
 const notes='演讲稿\n\n'+item.speech+'\n\n图件来源（不朗读）\n'+figures.map(v=>v.group+'：'+v.file+'；原图裁剪区域 '+JSON.stringify(v.roi)).join('\n')+'\n图中类名、消息编号和箭头均来自已有PNG或SVG原图。类关系局部在原SVG中仅保留有关类框和既有连线，没有重写文字、关系或多重性。完整原图保存在备查图册与本地源文件中。\n两组起始需求相同。整合采用结论不表示改写了2组原件，也不表示真实系统已运行通过。QX细化另参考B5个人材料，不等同于2组整组交付。';
 s.speakerNotes.text=notes;
}
await fs.mkdir(PREVIEW,{recursive:true});
for(const [i,s] of S.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(PREVIEW,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 await fs.writeFile(path.join(PREVIEW,`slide-${String(i+1).padStart(2,'0')}.layout.json`),await (await s.export({format:'layout'})).text());
}
const candidate=path.join(B,`main-${REV}.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:path.join(VALIDATED,'main.pptx'),pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-heading-fit'],explicitTotalSlideCount:13,requiredNativeTableOwnerSlides:[],fontPolicy:{basis:'reference',families:[FONT],referencePath:input,referenceSha256:createHash('sha256').update(await fs.readFile(input)).digest('hex')},verifyArtifactToolImport:true,receiptPath:path.join(B,`receipt-main-${REV}.json`)});
await fs.writeFile(path.join(B,`figures-${REV}.json`),JSON.stringify(used,null,2));
const count=speeches.reduce((a,v)=>a+(v.speech.match(/[\p{Script=Han}\p{L}\p{N}]/gu)||[]).length,0);
await fs.writeFile(path.join(B,`speech-${REV}.md`),'# 学术成果分享平台需求分析：图解版逐页演讲稿\n\n对应13页图解版。正文约'+count+'字，按每分钟220字讲述约'+(count/220).toFixed(1)+'分钟，另留约1分钟换页与指图，整体按12分钟内安排。\n\n'+speeches.map(v=>'## 第'+v.page+'页 '+v.title+'\n\n'+v.speech).join('\n\n')+'\n');
console.log(JSON.stringify({revision:REV,slides:S.length,figurePlacements:used.length,spokenCharacters:count}));
