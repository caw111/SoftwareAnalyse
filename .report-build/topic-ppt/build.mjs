import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
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

const p=Presentation.create({slideSize:{width:1600,height:900}});

// 1. Scope: the first page already carries content, rather than adding a cover.
{
 const s=base(p,'学术成果分享平台需求分析',1);
 text(s,'系统管理什么，谁使用系统',60,144,1480,50,34,{bold:true});
 text(s,'论文、专利、项目与获奖统一组织。1组与2组依据相同需求建立业务对象和交互模型。',60,213,1480,76,30);
 table(s,[['使用者','业务需求','权限与职责边界'],['公众用户','检索成果、筛选人物机构、查看详情','只读取当前允许公开的内容'],['科研人员','申请本人门户、确认贡献、维护个人信息','门户管理权与成果贡献分别确认'],['管理员／审核员','采集数据、治理冲突、审核申请','按对象权限操作，保留来源与决定依据']],60,325,1480,[300,580,600],[58,88,88,88],30);
 text(s,'采集入库　　门户认领审核　　检索请求处理',60,715,1480,55,36,{bold:true,color:C.teal});
 text(s,'每条业务链明确输入、处理结果，以及失败或并发时的行为。',60,784,1420,48,29);
 note(s,1);
}
// 2. Native table and a small editable domain-concept diagram.
{
 const s=base(p,'从业务事实识别核心对象',2);
 text(s,'学者可以先于账号存在，同一原文可以多次采集，一项成果可以有多位贡献者。',60,145,1480,76,29);
 table(s,[['业务对象','需要保存的数据','主要行为'],['账号与学者','稳定ID、身份依据、\n角色或来源','校验资格，区分同名人物'],['规范成果','成果ID、类型、题名\n版本与来源证据','校验后更新，解析\n合并后的规范身份'],['成果贡献','主体、角色、署名机构\n确认状态','确认贡献，撤销对应关系'],['认领申请','申请人、目标、材料版本\n状态和理由','提交、补充、审核、撤回'],['来源与任务','原文版本、固定范围\n处理结果、断点','记录观测、恢复处理\n追踪更新']],60,249,990,[200,400,390],[52,77,77,77,77,77],26);
 text(s,'分别具有稳定身份',1110,251,420,48,29,{bold:true,color:C.teal});
 node(s,'登录账号\nAccount / User',1110,322,420,92);
 node(s,'现实人物\nScholar',1110,452,420,92);
 node(s,'规范成果\nWork / AcademicOutcome',1110,582,420,92,{size:27});
 footer(s,'1组：Account、Work、Contribution、ClaimApplication、CollectionTask。\n2组：User、AcademicOutcome、OutcomeContributor、PortalClaim、CrawlTask。',738,100,25);
 note(s,2);
}
// 3. Common constraints with an editable patent/document example.
{
 const s=base(p,'类关系决定权限、贡献和统计口径',3);
 table(s,[['关键关系','业务约束','直接影响'],['四类成果继承\n统一父类','共享公共身份，保留\n类型专属字段','统一展示，按类型校验\n标识和日期'],['成果关联贡献','每条贡献属于一个成果，\n成果可有多条贡献','保留多作者、多角色\n及单位贡献'],['账号管理门户','当前有效绑定两端\n均至多一条','防止重复授予管理权'],['任务观测原文','同一原文可被\n多个任务再次观测','保留来源证据，\n不重复建规范成果']],60,180,980,[240,380,360],[54,88,88,88,88],27);
 text(s,'一件申请，两份文献',1090,181,440,50,30,{bold:true,color:C.teal});
 const patent=node(s,'专利申请\nPatent：1件',1120,267,380,103,{size:30});
 const pub=node(s,'公开文献',1085,455,205,87,{size:28});
 const grant=node(s,'授权文献',1320,455,205,87,{size:28});
 connect(s,patent,pub,{from:'bottom',to:'top',arrow:false});connect(s,patent,grant,{from:'bottom',to:'top',arrow:false});
 text(s,'PatentDocument：2份\n申请级成果数仍为1',1090,585,440,90,28,{align:'center'});
 footer(s,'1组：授权、贡献机构、观测独立建模，公开版本组合条目。\n2组：部分信息由关联和属性承载，成果组合贡献明细。组合不直接等同于物理级联删除。',730,107,25);
 note(s,3,'专利数量为已确认稿中的机制示例，不是平台实测统计。');
}
// 4. The operational steps remain native table evidence.
{
 const s=base(p,'采集入库怎样形成可信成果',4);
 text(s,'固定来源、窗口与规则配置，取得有效执行尝试后，再获取、清洗和规范入库。',60,143,1480,75,29);
 table(s,[['处理步骤','必须完成的业务动作'],['验证响应','区分有效数据、合法空页、访问受限和非数据网页'],['保留原文','保存来源键、checksum、原文引用及规则版本'],['清洗校验','规范展示值与比较键，保留未知值和字段证据'],['身份匹配','可信强标识一致且无冲突时关联；弱证据进入复核'],['规范入库','成果、贡献、来源映射、更新记录和后续工作可靠提交']],60,247,1000,[210,790],[52,73,73,73,73,73],28);
 const labels=['来源响应','原文版本','清洗与匹配','规范成果','后续更新登记'];let prev;
 labels.forEach((v,i)=>{const a=node(s,v,1150,246+i*85,350,60,{size:28});if(prev)connect(s,prev,a,{from:'bottom',to:'top'});prev=a;});
 footer(s,'同一合法DOI且无冲突：一个规范成果，保留两份来源。只有相似题名：保留候选，不自动合并。',706,70,28);
 sources(s,'1组：M主交互引用N清洗子图，GovernanceReview负责治理复核。\n2组：主图读取、清洗与入库消息承载流程；两组均要求隔离有原因、错误不丢失。',791);
 note(s,4);
}
// 5. Recovery: the table is the central visual, not a block of state definitions.
{
 const s=base(p,'采集失败以后，怎样恢复且不重复',5);
 text(s,'案例：三页窗口，第一页已提交，第二页解析失败。',60,151,1480,56,34,{bold:true});
 table(s,[['事件','分页断点 cursor','整窗成功水位'],['第一页可靠提交','指向第二页','保持原值'],['第二页解析失败','保持第二页','保持原值'],['恢复后处理全部输入并完成校验','本窗结束','才可推进']],60,245,1480,[660,410,410],[60,82,82,82],30);
 text(s,'原文可以复用，未完成处理仍须继续。旧attempt不能通过迟到回调推进水位。',60,585,1480,80,30,{color:C.teal,bold:true});
 footer(s,'1组：页断点与来源引用、观测及处理登记共同提交，规范入库另设事务。\n2组：页断点与规范成果及后续登记共同提交。断点之前的数据或待处理工作必须可靠存在。',691,97,25);
 text(s,'待统一：重试耗尽后，1组进入STOPPED；2组保留FAILED，人工放弃后才STOPPED。',60,810,1420,42,24,{color:C.warn});
 note(s,5);
}
// 6. Main claim flow with the private-evidence contract.
{
 const s=base(p,'门户认领从材料提交到审核决定',6);
 text(s,'前提：已登录、科研身份审核通过、目标门户存在。材料默认私有，手填ORCID仅提供核验线索。',60,147,1480,77,29);
 table(s,[['业务步骤','处理结果'],['提交申请','检查身份、目标、证明、本人重复申请和版本'],['读取审核材料','校验审核权限，读取当前材料及对象版本'],['要求补充','说明缺项，补交递增材料版本并重新检查'],['作出决定','批准建立绑定；驳回保留理由；合法撤回留存历史']],60,260,1000,[250,750],[55,78,78,78,92],28);
 let prev;
 ['提交申请','材料校验','授权审核','决定与留痕'].forEach((v,i)=>{const a=node(s,v,1160,267+i*100,340,69,{size:30});if(prev)connect(s,prev,a,{from:'bottom',to:'top'});prev=a;});
 footer(s,'技术验证超时保持可恢复状态。材料更新后，旧版本审核不能终审。门户批准不自动确认候选成果。',678,74,28);
 sources(s,'状态表达待统一：1组采用六状态，验证和审核占用为内部过程。\n2组将待验证、验证中、审核中纳入业务状态，共九状态。',785);
 note(s,6);
}
// 7. The enclosing rectangle is a native transaction diagram.
{
 const s=base(p,'批准与撤回竞争时，如何避免错误授权',7);
 text(s,'提交时复验资格、权限、材料和对象版本，保证账号与门户双向有效唯一。',60,146,1480,60,29);
 s.shapes.add({geometry:'rect',name:'批准事务边界',position:{left:60,top:230,width:1480,height:105},fill:'none',line:{fill:C.teal,width:2}});
 const tx=['申请通过','有效管理绑定','审核决定','审计与版本'];
 tx.forEach((v,i)=>text(s,v,90+i*365,262,335,50,32,{bold:true,color:C.teal,align:'center'}));
 text(s,'共同提交',60,345,1480,35,24,{color:C.muted,align:'center'});
 text(s,'双方都读到待审核，version=7。',60,402,1480,48,31,{bold:true});
 table(s,[['谁先提交','已提交事实','另一请求的结果'],['本人撤回','WITHDRAWN，version=8\n无新授权','旧批准失败，不能创建授权'],['管理员批准','APPROVED，version=8\n绑定共同生效','旧撤回失败，解绑另走授权撤销']],60,475,1480,[300,560,620],[56,93,93],29);
 footer(s,'冲突方读取当前真实状态，不能覆盖终审历史。通知在提交后发送，失败可以补发。',750,60,28);
 sources(s,'1组：ClaimControl协调批准事务。2组：共同提交PortalClaim、管理绑定和更新记录。',815);
 note(s,7,'事务图为源模型交互的可编辑简化表达；version=7/8是并发机制示例。');
}
// 8. A required native domain relationship example: R06 is excluded.
{
 const s=base(p,'检索条件怎样得到正确的结果集合',8);
 text(s,'查询：作者A01在机构I01的成果。人物与机构必须属于同一条贡献关系。',60,146,1480,66,31,{bold:true});
 const work=node(s,'成果 R06',60,271,245,150,{size:34,bold:true});
 const a=node(s,'A01的贡献',445,226,335,83,{size:31});
 const b=node(s,'A03的贡献',445,388,335,83,{size:31});
 const i3=node(s,'机构 I03',950,226,300,83,{size:31});
 const i1=node(s,'机构 I01',950,388,300,83,{size:31});
 connect(s,work,a,{arrow:false});connect(s,work,b,{arrow:false});connect(s,a,i3,{arrow:false});connect(s,b,i1,{arrow:false});
 text(s,'R06\n不命中',1310,282,230,125,40,{bold:true,color:C.warn,align:'center'});
 table(s,[['固定样例','贡献事实','是否命中'],['R01、R04、R07','A01的贡献关联I01','命中，共3条'],['R06','A01关联I03，A03关联I01','不命中']],60,534,1480,[400,700,380],[53,70,70],29);
 footer(s,'1组：ContributionAffiliation关联类。2组：OutcomeContributor中的署名机构与证据，查询契约约束同贡献。',755,66,25);
 text(s,'日期按成果类型解释；项目默认资助年度。项目编号需结合资助机构消歧。',60,831,1420,32,23,{color:C.muted});
 note(s,8,'R01等编号来自现有固定验收样例。条件组合：跨维度AND，同维度通常OR，多人物明确all/any。');
}
// 9. The numbers are a labeled mechanism example, not measured statistics.
{
 const s=base(p,'检索列表、总数与详情怎样保持一致',9);
 text(s,'固定同一公开release，同时校验当前权限。下列数字为权限过滤示例。',60,145,1480,55,30,{bold:true});
 text(s,'候选 10 条',60,218,430,55,38,{color:C.ink,bold:true});
 text(s,'受限 3 条',580,218,430,55,38,{color:C.warn,bold:true});
 text(s,'允许 7 条',1110,218,430,55,38,{color:C.teal,bold:true});
 table(s,[['一致性问题','具体处理'],['R2发布，列表仍绑定R1','续页和详情继续读R1；R1失效明确提示刷新'],['候选中有不可见记录','先取得允许集合，再统一计算列表、total和分面'],['实际total=3，每页2条','取得真实总数后判断页码，第3页越界'],['查询或读取失败','明确返回错误，不当作空集，也不拼接最新数据']],60,306,1480,[600,880],[54,72,72,72,72],28);
 footer(s,'1组QX细化返回前权限复验：权限修订变化，作废结果并要求重试。\n2组主图通过固定release、实时权限和同版规范ID读取表达一致性契约。',682,92,26);
 text(s,'公开索引与统计同快照构建，校验READY后切换。构建失败保留旧版，采集完成不等于新数据已可检索。',60,794,1420,62,25,{color:C.muted});
 note(s,9,'10/3/7为机制示例。1组当前QX细化参考另行提供的B5吴星宇个人包v0.9 M20至M30，不能等同于2组整组交付。');
}
// 10. Conclude with verifiable behavior, not a differences summary.
{
 const s=base(p,'用具体场景核对需求是否落实到模型',10);
 table(s,[['需求规则','检查场景','模型应得到的结果'],['幂等与来源保留','同一合法DOI来自两个来源，\n然后重复采集','一个规范成果，来源和观测可追溯'],['失败恢复','第一页已提交，\n第二页解析失败','保留有效断点，整窗水位不提前推进'],['并发授权','管理员批准与\n本人撤回同时发生','最多一个合法提交，状态与绑定一致'],['同贡献检索','查询A01与I01，\n另有R06交叉关系','正确返回3条，R06不混入'],['版本与权限','旧版失效，或返回前\n权限发生变化','明确刷新或重试，不返回混版内容及旧计数']],60,185,1480,[290,570,620],[56,87,87,87,87,87],28);
 text(s,'两组模型按同一组业务预期核对，问题回写类图、时序和需求记录。',60,745,1480,66,31,{bold:true,color:C.teal});
 text(s,'当前是需求分析模型与设计走查，真实系统行为在实现后验证。',60,824,1420,36,25,{color:C.muted});
 note(s,10);
}

async function renderAll(deck,dir){
 await fs.mkdir(dir,{recursive:true});
 for(const [i,s] of deck.slides.items.entries()){
   const png=await deck.export({slide:s,format:'png',scale:1});
   await fs.writeFile(path.join(dir,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
   const layout=await s.export({format:'layout'});await fs.writeFile(path.join(dir,`slide-${String(i+1).padStart(2,'0')}.layout.json`),await layout.text());
 }
}
const mainCandidate=path.join(B,`main-${REV}.pptx`);
await (await PresentationFile.exportPptx(p)).save(mainCandidate);
await renderAll(p,path.join(PREVIEW,'main'));
console.log('Main rendered: 10 slides');

// Separate original-model atlas preserves every supplied drawing unchanged.
const atlas=Presentation.create({slideSize:{width:1200,height:1600}});
const order1=['02-核心业务类图','02-局部01-账号学者与门户授权','02-局部02-四类成果与专利身份','02-局部03-贡献机构与领域关系','02-局部04-来源采集与规范映射','02-局部05-治理更新与公开版本','03-采集入库时序图','03a-清洗去重子交互','03b-停止重试子交互','05-门户认领审核时序图','05a-认领原子授权与撤回子交互','06-检索请求处理时序图','06a-检索权限计数与分页子交互'];
const order2=['01_核心业务类图','02_数据采集入库时序图','03_门户认领审核时序图','04_检索请求处理时序图'];
for(const [group,files] of [['1组',order1],['2组',order2]]){
 for(const name of files){
  const s=atlas.slides.add();s.background.fill='#FFFFFF';
  text(s,group+'　'+name.replace(/^\d+[a-z]?[-_]/,''),46,36,1108,77,36,{bold:true,color:group==='1组'?C.teal:C.purple});
  const file=path.join(SOURCE,'图件',group,name+'.png');const blob=await fs.readFile(file);
  s.images.add({blob,contentType:'image/png',alt:group+' '+name,fit:'contain',position:{left:40,top:131,width:1120,height:1385}});
  text(s,'原始模型全图',46,1542,1030,36,24,{color:C.muted});
  text(s,String(atlas.slides.items.length).padStart(2,'0'),1090,1542,65,36,24,{color:C.muted,align:'right'});
  s.speakerNotes.text=group+'原始PNG模型，内容与原图字节一致。\n来源：'+file+'\n'+(group==='2组'?'GitHub固定提交 b93110b8964e9061469bcfab8d0ced701f3d4526。':'当前整合交付，A2类图、A3采集图及补建认领检索图。');
  trace.push({group,name,file,sha256:createHash('sha256').update(blob).digest('hex')});
 }
}
const atlasCandidate=path.join(B,`atlas-${REV}.pptx`);
await (await PresentationFile.exportPptx(atlas)).save(atlasCandidate);
await renderAll(atlas,path.join(PREVIEW,'atlas'));
console.log('Atlas rendered: 17 slides');

const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const fontPolicy={basis:'design',families:[FONT]};
for(const kind of ['main','atlas']){
 const native=kind==='main'?[1,2,3,4,5,6,7,8,9,10]:[];
 const dims=kind==='main'?'15240000,8572500':'11430000,15240000';
 const result=await finalizePresentation({
   workspaceDir:ROOT,candidatePath:kind==='main'?mainCandidate:atlasCandidate,
   finalPath:path.join(VALIDATED,`${kind}.pptx`),pythonExecutable:PYTHON,
   integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
   layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
   layoutArgs:['--expected-slide-size-emu',dims,'--validate-bullet-geometry','--validate-heading-fit',...native.flatMap(n=>['--require-native-table-slide',String(n)])],
   explicitTotalSlideCount:kind==='main'?10:17,requiredNativeTableOwnerSlides:native,fontPolicy,
   verifyArtifactToolImport:true,receiptPath:path.join(B,`receipt-${kind}-${REV}.json`)
 });
 console.log(JSON.stringify({kind,finalPath:result.finalPath}));
}
await fs.writeFile(path.join(B,`build-trace-${REV}.json`),JSON.stringify({revision:REV,mainSlides:10,atlasSlides:17,source:path.join(SOURCE,'PPT逐页内容.md'),figures:trace},null,2));
