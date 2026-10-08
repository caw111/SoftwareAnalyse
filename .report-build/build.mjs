import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';

const root=process.cwd(), tmp=path.join(root,'.report-build'), out=path.join(root,'汇报成果');
const skill='C:/Users/27872/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const python='C:/Users/27872/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/27872/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#243E38',muted:'#526760',accent:'#9C572D',paper:'#FAF9F5',pale:'#E9EEE9',white:'#FFFFFF',line:'#C0CDC5'};
const FONT='Microsoft YaHei';
const meta=[],tables=[];
const durations=[20,35,40,40,45,55,35,45,60,45,60,50,55,40,55,55,50,40,45,30];
function txt(s,text,x,y,w,h,size=28,color=C.ink,bold=false,align='left'){
 const a=s.shapes.add({geometry:'textbox',name:text.slice(0,45),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=text;a.text.style={typeface:FONT,fontSize:size,color,bold,alignment:align,autoFit:'none'};return a;
}
function page(title,note,source,subtitle='',dark=false){
 const s=p.slides.add();s.background.fill=dark?C.ink:C.paper;
 txt(s,title,64,42,1152,74,42,dark?C.white:C.ink,true);
 if(subtitle)txt(s,subtitle,64,123,1152,45,23,dark?'#D5E3DA':C.muted);
 const idx=meta.length+1;
 txt(s,String(idx).padStart(2,'0'),1160,666,56,28,17,dark?'#D5E3DA':C.muted,false,'right');
 const timed=idx<=20?`建议讲述 ${durations[idx-1]} 秒。`:'答疑附录，不计入15分钟主讲。';
 s.speakerNotes.textFrame.setText(timed+'\n\n'+note+'\n\n来源：'+source);
 meta.push({title,note,source,duration:idx<=20?durations[idx-1]:0});return s;
}
function table(s,values,widths,y=195,h=380,font=25){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:64,top:y,width:1152,height:h,columnWidths:widths,values});
 t.borders.assign({style:'solid',fill:C.line,width:0.75});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const a=t.getCell(r,c);a.fill=r===0?C.ink:(r%2?C.white:C.pale);
  a.text.style={typeface:FONT,fontSize:font,color:r===0?C.white:C.ink,bold:r===0};
 }
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({margins:{left:15,right:15,top:13,bottom:10}});
 tables.push(meta.length);return t;
}
function lines(s,items,x=64,y=200,w=1152,gap=108){
 for(let i=0;i<items.length;i++){
  txt(s,items[i][0],x,y+i*gap,w,44,31,C.ink,true);
  txt(s,items[i][1],x,y+i*gap+48,w,66,25,C.muted);
 }
}
function node(s,text,x,y,w=210,h=66,geometry='roundRect',fill=C.pale){
 const a=s.shapes.add({geometry,name:text,position:{left:x,top:y,width:w,height:h},fill,line:{fill:C.ink,width:1.3}});
 a.text=text;a.text.style={typeface:FONT,fontSize:geometry==='ellipse'||text.includes('actor')?21:25,color:C.ink,alignment:'center',verticalAlignment:'middle',insets:{top:3,bottom:3,left:7,right:7},bold:false};return a;
}
function link(s,a,b,from='right',to='left',arrow=true){
 return s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:C.muted,width:1.5},...(arrow?{tail:{type:'triangle',width:'sm',length:'sm'}}:{})});
}
function route(s,points,label='',x=0,y=0,w=170,arrow=true,hollow=false){
 const xs=points.map(a=>a[0]),ys=points.map(a=>a[1]),l=Math.min(...xs),t=Math.min(...ys);
 const width=Math.max(1,Math.max(...xs)-l),height=Math.max(1,Math.max(...ys)-t);
 s.shapes.add({geometry:'custom',name:label+'状态迁移',position:{left:l,top:t,width,height},fill:'none',line:{fill:C.muted,width:1.7},customPaths:[{width,height,commands:points.map((a,i)=>({[i?'lineTo':'moveTo']:{x:a[0]-l,y:a[1]-t}}))}]});
 const end=points.at(-1),prev=points.at(-2),angle=end[0]>prev[0]?90:end[0]<prev[0]?270:end[1]>prev[1]?180:0;
 if(arrow)s.shapes.add({geometry:'triangle',position:{left:end[0]-5,top:end[1]-5,width:10,height:10,rotation:angle},fill:hollow?C.paper:C.muted,line:{fill:C.muted,width:hollow?1.4:0}});
 if(label)txt(s,label,x,y,w,32,20,C.ink);
}
const src='scripts/';
let s;
s=page('学术成果分享平台','各位老师、同学好，本次汇报聚焦需求调研与需求建模。我们把普通用户、科研人员和管理员的资料统一起来，围绕四类成果说明平台要解决的问题、核心业务规则和模型，并明确已有证据与待验证内容。','课程任务书；M01—M06；G01—G08','需求调研与需求建模总体方案',true);
txt(s,'可信数据 · 公开检索 · 学者门户',64,282,1130,70,49,C.white,true);
txt(s,'论文  /  授权专利  /  科研项目  /  获奖',64,382,1120,65,32,'#D5E3DA');
txt(s,'《软件系统分析与设计》课程实践（一）',64,553,1100,44,24,'#D5E3DA');
txt(s,'15分钟主讲  ·  2026年10月7日',64,608,1100,40,23,'#D5E3DA');

s=page('阶段任务与现有交付','任务书将需求调研和需求建模列为两个评审阶段。目录中已有三份Markdown调研材料、数据源Word报告以及SRS、SPEC和八张图。我们发现分角色用例图较完整，但总用例和采集状态图没有独立成图。因此本汇报增加总用例和两类状态模型，类图与时序图作为下一阶段预研材料，不代替状态图。','任务书物理第5—6、10页；M01—M06；G01—G08','已有调研与规范；本次补齐模型并统一需求口径');
table(s,[['阶段','任务书要求','当前材料与本次补充'],['需求调研','方案、来源、分类、诉求、边界','3份角色／总体报告＋数据源报告'],['需求建模','用例、认领活动、两类状态、SRS／SPEC','已有分角色用例与活动；补总图和状态图'],['后续预研','业务类图、关键交互模型','已有类图与检索时序；归入需求分析']], [185,407,560],195,325,25);
txt(s,'尚需真实访谈／样例验证及评审记录；文档存在不等于评审通过',64,565,1140,64,26,C.accent,true);

s=page('调研方法与证据边界','现有研究主要采用公开资料研读、数据源分析和同类平台对比。普通用户材料强调核实信息，科研人员材料强调归属与管理，数据源材料强调追踪与质量。我们把这些证据映射到需求、用例、规范和验收。目录中没有本小组实际问卷回收和访谈原始记录，所以画像只用于说明场景，后续要通过三角色访谈和接入样例验证。','M01第1、8章；M02引言；M03第1—3、8节','公开资料结果用于提出需求，实地验证用于修订需求');
lines(s,[['任务书与公开资料','提取必做功能、来源限制、分类与业务规则'],['同类平台与角色场景','10个平台对比；三类角色的目标、权限和异常路径'],['需求追踪与后续验证','证据 → 需求 → 用例／SPEC → 验收；补访谈、样例和评审记录']],64,200,1152,136);

s=page('同类平台的借鉴方向','总体报告已比较十个平台，我们不逐一复述产品介绍，而是提炼四类机制。学者档案给出门户和身份关联的参考；书目与元数据平台支持开放接入；国内成果服务体现机构和多类型成果场景；科研整理工具提示收藏和来源核查的增强价值。平台坚持四类成果和可信归属，暂不把讨论社区、推荐或笔记全部列为必做，也不依赖原报告待核实的商业数字。','M01第2章；M02第4章；M03第2—3节','以需求机制为依据；规模、营收与价格不作为本次论据');
table(s,[['借鉴方向','现有调研对象','落到本平台的需求'],['身份与门户','ORCID、学者档案\nResearchGate','账号／学者分离，认领审核与纠错'],['开放书目与元数据','OpenAlex、DBLP、Crossref','多源接入、稳定标识、来源追踪'],['多类型与机构视角','知网、万方等成果服务','四类成果、机构排名、分类过滤'],['检索与科研整理','Google Scholar\nSemantic Scholar等','同名核查、可解释检索；收藏导出作增强']], [230,420,502],193,425,25);

s=page('三类角色与权限边界','普通用户需要找得到并核实成果，科研人员需要维护本人门户，管理员需要让采集、审核和质量问题可控。角色按当前操作权限区分，一个人可以同时是查询者和科研人员。账号不是学者实体，门户认领通过后才建立管理绑定。管理员可以审核证明材料和公共数据，但并不因此自动获得私人笔记读取权限。','M01第6章；M02第1章；M03第4、7节','公开查询、本人管理、后台治理分别校验权限');
table(s,[['角色','用户目标','功能与边界'],['普通用户／访客','检索并核实信息','四类成果、学者门户、来源、统计；公开只读'],['科研人员','管理本人可信门户','认领、反馈、本人维护；公共修订需审核'],['管理员','保障身份与数据可信','来源和任务管理、认领审核、质量复核、审计']], [250,330,572],200,330,26);
txt(s,'账号 ≠ 学者实体；只有“审核通过＋绑定成功”才能授予门户管理权',64,574,1148,65,28,C.accent,true);

s=page('四类成果的数据来源方案','论文优先用OpenAlex，DBLP补充计算机领域，Crossref校验出版标识。专利优先核查官方公开服务，奖励按授奖机构公告接入。科研项目在总体报告里有来源讨论，但数据源专项报告及SPEC缺少完整链路，本次补充资助机构加项目编号的识别规则。先用论文支撑规模，另外三类仍需小样本可演示路径。没有可用批量访问的类型可采用任务书允许的模拟样本，并明确标识来源。','M01第3章；M04第2、11章；任务书正文第1—2、8页；OpenAlex、DBLP与NSFC官方说明','论文先支撑规模；四类成果均保留本期可用路径');
table(s,[['类型','一期候选来源','关键标识／接入证据'],['论文','OpenAlex＋DBLP；Crossref校验','DOI／来源ID；API或快照样例'],['授权专利','国家知识产权局；EPO OPS候选','公开号、申请号、文献种类、授权依据'],['科研项目','NSFC公开查询／公告、科技部公示','资助机构＋项目编号；补样例和字段映射'],['获奖','国家科技奖励、CCF／电子学会等','授奖机构＋年度＋类别等级＋项目复合键']], [180,472,500],188,400,24);
txt(s,'候选来源不等于已完成接入；许可、凭证、访问方式与样例须登记',64,621,1120,42,23,C.accent);

s=page('领域分类与来源追踪','分类采用本地稳定领域、学科和方向层级，并保存外部标签和版本。各分类体系不完全等价，所以不能直接把NSFC、国家学科目录和OpenAlex逐级拼接。跨学科成果允许多个领域，未分类单列。每项成果保存至少一个来源，主字段保留来源选择依据；自动更新遇到人工修订冲突时进入复核，不悄悄覆盖。','M01第4、5章；M03第6.1、7节；M04第3、7、9章','本地分类稳定，外部分类可映射；每项成果都能回溯来源');
lines(s,[['领域—学科—方向','保留原分类ID、标签和版本；跨学科多标签，未分类单列'],['来源记录与字段证据','来源ID／URL、采集与更新时间、内容校验值、解析版本、字段来源'],['增量更新与人工修订','按来源更新时间和公告变化更新；重复接入幂等，冲突进入复核']],64,190,1152,137);

s=page('需求范围与统一优先级','当前资料使用P0、P1、P2和M、S、C两套表达。我们统一为基础必做、增强和后续可选。SRS把成果维护和基础统计列为P1、创新列为P2，容易导致遗漏任务书必做内容，需要回写修订。至少一项创新必须交付，建议在基础合作网络之上做筛选、共同成果回溯和最短共著路径；是否满足创新要求由评审确认。交易、付费和支付放在后期。','任务书正文第1、3、8页；M01第7章；M03第4—6节；M05 FR-13/14/16','优先顺序可以调整，课程必做范围不能被优先级删减');
table(s,[['等级','本期范围'],['P0／M 基础必做','四类成果、采集清洗、检索门户、认领审核、维护纠错、基础统计、后台治理'],['至少一项创新','合作网络筛选与证据回溯＋最短共著路径（评审确认）'],['P1／S 增强','收藏、导出、专题库／笔记、引用与资源链接，按能力选取'],['P2／C 与后期','推荐、讨论、订阅、高级预测；交易、付费全文、支付后期考虑']], [275,877],185,435,25);

s=page('系统总用例图：覆盖三角色与采集治理','统一总用例将公开查询、门户认领、管理采集和数据治理放在同一边界里。左侧是访客、注册科研人员和已认领学者，右侧是管理员及外部数据源。权限继承由参与者泛化表达。公开统计和网络是用户目标，管理员负责审核、任务及质量。图中关联线不表达先后顺序；详细操作顺序在活动图和状态图中说明。分角色原图在附录保留。','任务书二（二）1；M02/M03；M05第3章；新增汇总模型','新增总览；原分角色用例图在附录21—22页');
const boundary=s.shapes.add({geometry:'rect',position:{left:230,top:183,width:800,height:435},fill:'none',line:{fill:C.line,width:1}});
txt(s,'学术成果分享平台',430,184,430,30,21,C.ink,true,'center');
const visitor=node(s,'«actor»\n访客',64,230,145,68,'rect');
const registered=node(s,'«actor»\n注册科研人员',64,414,145,68,'rect');
const claimed=node(s,'«actor»\n已认领学者',64,533,145,68,'rect');
const admin=node(s,'«actor»\n管理员',1051,410,165,75,'rect');
const external=node(s,'«actor»\n外部数据源',1051,230,165,75,'rect');
const leftLabels=['检索／查看成果与学者','浏览学者门户','查看统计与合作网络','提交门户认领','维护本人门户与成果'];
const rightLabels=['配置来源／采集任务','执行采集、清洗与入库','审核认领申请','质量复核与纠错','维护领域分类'];
const lu=leftLabels.map((v,i)=>node(s,v,251,230+i*75,330,57,'ellipse'));
const ru=rightLabels.map((v,i)=>node(s,v,666,230+i*75,343,57,'ellipse'));
for(let i=0;i<3;i++)link(s,visitor,lu[i],'right','left',false);
link(s,registered,lu[3],'right','left',false);link(s,claimed,lu[4],'right','left',false);
for(const a of ru)link(s,admin,a,'left','right',false);
route(s,[[1051,267],[1042,267],[1042,333],[1009,333]],'',0,0,170,false);
route(s,[[136,414],[136,304]],'',0,0,170,true,true);route(s,[[136,533],[136,488]],'',0,0,170,true,true);
txt(s,'权限泛化',73,356,128,30,19,C.muted);txt(s,'关联线表示参与关系；维护前必须校验本人门户权限',64,630,1140,36,22,C.accent);

s=page('检索场景：找成果，也要核实学者身份','以找某位作者近五年的成果为例，用户先输入姓名、机构或领域，系统展示人物候选。用户核对机构、代表成果和标识后，按实体ID查询，而不是把同名作者的论文全部混在一起。未确认身份时允许文本检索，但说明范围。多个筛选维度同时生效，详情展示来源与缺失字段，空结果和服务失败分开提示。返回时保留条件、排序和页码。','M02第6—8、12.1、13章；M03第7.2节；G04/G05/G08','同名候选由用户核查；平台不把姓名相同当作同一人');
const flow=['输入姓名与机构','核对人物候选','组合筛选并查询','详情与来源核查'];
const ns=flow.map((v,i)=>node(s,v,64+i*294,235,260,85));for(let i=0;i<3;i++)link(s,ns[i],ns[i+1]);
lines(s,[['筛选与排序','跨维度AND／同维度OR；领域含子领域，分页排序可复现'],['异常与上下文','空结果可放宽条件；超时可重试；返回保留查询条件与页码']],64,387,1150,118);

s=page('门户认领：提交、核验、审核与绑定','原认领活动图已有科研人员、平台和管理员三条泳道。这里提炼其核心：申请人提供身份与成果证据，平台校验材料、重复申请和绑定状态，管理员核验。证据不足走补材料，不是直接驳回。通过后仍要原子检查唯一绑定，再授予权限和写审计。邮箱验证只证明邮箱控制，ORCID格式正确不证明本人；可交互绑定应使用认证流程。并发冲突时回到复核并保留原权限。','M03第7、10节；G03；M05 FR-11/12；https://info.orcid.org/documentation/collecting-and-sharing-orcid-ids/','与原活动图一致；审核通过还必须保证唯一绑定成功');
const cf=['选择本人门户','提交证据','平台校验','管理员核验','绑定、授权\n审计'];
const cn=cf.map((v,i)=>node(s,v,64+i*234,226,214,80));for(let i=0;i<4;i++)link(s,cn[i],cn[i+1]);
table(s,[['分支','处理结果'],['证据不足','退回待补充；提交后重新校验'],['身份不成立','驳回并说明理由；重新申请建新记录'],['绑定竞争','不授予权限；保留原权限并转待审核复核']], [280,872],362,239,24);
txt(s,'一个账号最多一个本人门户；一个门户最多一个管理账号',64,623,1140,34,24,C.accent,true);

s=page('采集任务状态机','采集状态统一为待执行、运行中、成功、失败、重试和已停止。管理员启动或计划触发进入运行，失败保存错误与检查点，再按退避和次数上限重试。停止是终态，再执行建立新任务并关联旧任务。原SRS提到暂停但没有暂停及恢复状态，因此当前统一为停止。采集成功只指约定采集和解析完成，不代表数据质量、索引和整个系统都验收成功。完整事件与日志规则见配套方案。','任务书二（二）3；M05第8.1节；M06 SPEC-INGEST-01；本次补充模型','新增六状态模型；停止后再执行创建新任务');
const wait=node(s,'待执行',64,219,210,70),run=node(s,'运行中',447,219,210,70),success=node(s,'成功',1006,219,210,70);
const retry=node(s,'重试',64,420,210,70),failed=node(s,'失败',447,420,210,70),stop=node(s,'已停止',1006,420,210,70);
route(s,[[274,254],[447,254]],'启动／计划触发',280,214,168);
route(s,[[657,254],[1006,254]],'采集解析完成',719,213,235);
route(s,[[552,289],[552,420]],'无法继续',663,382);
route(s,[[447,455],[274,455]],'重试获准',305,415);
route(s,[[169,420],[169,337],[489,337],[489,289]],'退避到期',268,297);
route(s,[[657,455],[1006,455]],'放弃任务',767,415);
route(s,[[618,289],[618,377],[1111,377],[1111,420]],'停止',843,337);
route(s,[[64,254],[42,254],[42,536],[1062,536],[1062,490]],'取消',47,337,100);
route(s,[[169,490],[169,553],[1160,553],[1160,490]],'停止重试',607,550,180);
txt(s,'取消、停止与放弃均进入已停止；每次迁移保留日志、进度和原因',64,576,1152,67,25,C.accent,true);

s=page('认领申请状态机','认领模型补入SRS缺少的待补充状态，与已有活动图一致。申请从草稿提交为待审核，再由管理员开始审核，审核可退回补充、驳回或绑定通过。待补充重新提交回到待审核；绑定竞争也回到待审核。草稿、待审核和待补充可撤回；终态历史不改写。已驳回后需要再次申请时建立新记录，避免重用旧申请破坏审核证据。','M03第7、10、13节；G03；M05第8.2节；本次统一模型','补入“待补充”，保留终态历史；驳回后重新申请建新记录');
const draft=node(s,'草稿',64,222,200,70),pending=node(s,'待审核',385,222,200,70),review=node(s,'审核中',707,222,200,70),approved=node(s,'已通过',1016,222,200,70);
const withdraw=node(s,'已撤回',64,447,200,70),supp=node(s,'待补充',385,447,200,70),reject=node(s,'已驳回',1016,447,200,70);
route(s,[[264,257],[385,257]],'提交',292,223,89);
route(s,[[585,257],[707,257]],'受理',617,224,87);
route(s,[[907,257],[1016,257]],'绑定通过',915,220,120);
route(s,[[777,292],[777,391],[520,391],[520,447]],'证据不足',596,402);
route(s,[[440,447],[440,292]],'补充提交',450,340,125);
route(s,[[846,292],[846,348],[1116,348],[1116,447]],'驳回',944,353,95);
route(s,[[806,222],[806,201],[485,201],[485,222]],'绑定冲突／复核',536,172,247);
route(s,[[164,292],[164,447]],'放弃',179,355,90);
route(s,[[385,280],[302,280],[302,482],[264,482]],'撤回',310,352,87);
route(s,[[385,482],[264,482]],'撤回',295,485,86);
txt(s,'未通过或发生冲突时不授予权限；申请状态变更必须记录操作者和理由',64,580,1152,68,25,C.accent,true);

s=page('SRS与SPEC：把业务规则写成可实现约束','已有SRS给出了十六项功能需求，SPEC提供采集、清洗、去重、消歧、检索和质量六项规范。我们建议在原规范中补齐科研项目，而不是另造一套体系；认领与统计已有散落的规则，需要整理为独立模块规范。每份规范要明确做什么、输入输出、规则边界、异常、接口和验收，并与需求编号对应。后续代码履约从已评审规范开始。','M05第3—9章；M06第1—8章；M03第7节','6项已有核心规范；项目、认领与统计仍需回写正式文件');
table(s,[['已有模块规范','规则重点','建议补齐'],['INGEST／DATA-01','采集、清洗与字段标准化','四类来源、项目字段、六状态与检查点'],['DATA-02／DATA-03','成果去重、作者机构消歧','项目键、强标识冲突、缺失证据与样本'],['SEARCH／QUALITY','排序、过滤、来源与复核','项目检索、评分归一化、指标分母'],['CLAIM／STAT（新增建议）','认领权限、统计与合作网络','原子绑定、终态历史、计数与证据明细']], [355,400,397],187,426,24);

s=page('去重与消歧：标识优先，证据不足人工复核','清洗保留原值和比较值，规范DOI、日期精度及作者顺序。论文先用DOI去重，无DOI再做候选评分；专利区分公开文献、申请和家族；奖励用复合键。项目补充资助机构和项目编号，编号缺失只召回候选并人工确认。作者同名不能直接合并，身份和机构历史需要多项证据。表中阈值来自现有SPEC，是待标注样本验证的参数，不是已经达到的效果。','M04第4—6章；M06 SPEC-DATA-01/02/03；项目为本次补充','阈值沿用现有SPEC；必须定义有效证据、缺失处理和版本');
table(s,[['对象','优先依据','自动／人工复核区间'],['论文','合法DOI；无DOI按题名等评分','≥0.92自动；[0.82,0.92)复核'],['专利公开文献','主管机构＋公开号＋文献种类','不同阶段／国家记录保留关联'],['科研项目（补）','资助机构＋项目编号','编号缺失仅召回候选、人工确认'],['获奖','授奖机构、年度、类别等级、项目','≥0.93自动；[0.84,0.93)复核'],['作者／机构','可靠ORCID关联／ROR、机构历史','作者≥0.95自动；[0.85,0.95)复核']], [245,455,452],178,448,23);
txt(s,'不同强标识不能被高相似分数覆盖；缺失证据不默认满分',64,637,1115,29,22,C.accent,true);

s=page('检索、统计与创新的统一规则','检索首先保证精确标识命中和标题优先，并列结果采用年份和成果ID形成稳定顺序。现有复合分包含文本、引用、时效和质量，实施前需要统一归一化与缺失值处理。统计使用与列表一致的数据版本，机构采用全计数，故机构数量合计可能大于总成果数。合作网络边必须能追踪共同论文，最短路径仅代表共著连接。基础统计和网络是必做，高级筛选及路径分析是拟选创新增量。','M03第7.2/7.3节；M02第9章；M06 SPEC-SEARCH-01；G01','列表与统计使用同一范围与版本，结果可解释、可回溯');
lines(s,[['检索：精确命中与稳定顺序','标题优先；并列按年份↓、成果ID↑；跨类型分值须校准'],['统计：类型口径与明细一致','机构全计数、多领域可重叠；未分类与缺失年份单列'],['创新：最短共著路径与证据','在基础网络上筛选、查共同论文；路径不代表合作意愿']],64,185,1152,140);

s=page('可验收的质量目标','任务书要求最终入库至少一万条成果，我们将它转化为可测试环境，建议在二十并发、预热五分钟下检索P95不超过两秒，统计五秒以内。数据质量目标沿用已有规范：核心完整率至少百分之九十五，来源追踪百分之百，清洗和自动合并通过抽样验证。认领并发、幂等采集和非本人修改也要有失败场景。当前没有实测报告，这些数字均是目标，评审应确认测试设备、分母和抽样方法。','任务书四（二）；M03第8节；M05第7/9章；M06第3/5/6/7章','以下是验收目标，当前资料未提供实测达标证据');
table(s,[['维度','建议验收条件','验证方式'],['规模与性能','≥1万条；20并发；检索P95≤2秒','记录设备，预热后5分钟；冷启动单列'],['数据质量','完整率≥95%；来源追踪100%','按成果类型定义核心字段与分母'],['清洗／自动合并','清洗≥99%；去重≥98%；作者≥97%','分类型标注样本；清洗抽查500条'],['权限与恢复','唯一绑定、幂等采集、失败可恢复','双账号、并发、重复提交和失败场景']], [270,440,442],192,413,24);

s=page('需求追踪：每项要求都有模型与验收','这张矩阵让评审能从任务书找到需求，再找到模型和SPEC，最后找到可执行的验收场景。例如门户认领对应提交与审核用例、活动图和认领状态图，验收要覆盖补材料、驳回、重复申请和并发绑定。采集对应六状态图和INGEST规范，统计对应统一口径及合作网络证据。原各角色报告局部编号要加前缀，统一以SRS的FR编号维护，防止同号异义。','M05 FR-01—16；M06第1、8章；配套方案第12节','完整追踪矩阵见配套方案；局部需求编号加角色前缀');
table(s,[['统一需求','模型／用例','规范','代表验收场景'],['FR-01—07 采集治理','UC-07/08/09＋采集状态','INGEST、DATA、QUALITY','失败重试、重复导入、强ID冲突'],['FR-08—10 检索门户','UC-01/02＋检索活动','SEARCH','同名候选、组合筛选、四类详情'],['FR-11—13 认领维护','UC-04/05/06＋活动／状态','CLAIM（补）','补充／驳回、唯一绑定、越权拒绝'],['FR-14/16 统计创新','UC-03＋合作网络路径','STAT（补）','计数明细一致、路径边对应论文']], [335,300,220,297],188,414,22);

s=page('评审前的重点修订与验证','评审前优先做四件事：修订SRS，把四类、维护、基础统计和一个创新的范围写清；同步模型，把待补充和停止语义写入正式状态表；补齐项目采集、编号、去重和检索的样例规范；保存真实访谈、接入实验和评审记录。这不是重新扩建系统，而是消除已有文件之间的冲突，使团队在后续分析、设计和实现时遵循同一份需求。','M01—M06差异核对；任务书需求调研／建模评审要求','本次已提供补充模型与方案；正式SRS／SPEC修订及评审尚待完成');
table(s,[['工作','应形成的证据','建议责任方向'],['统一范围与编号','修订SRS、优先级、追踪矩阵','总体／普通用户负责人'],['认领与任务状态同步','活动／状态一致，操作与日志规约','科研人员＋管理员负责人'],['项目及数据规则验证','样例、字段映射、去重与查询集','数据源／数据治理负责人'],['验证与需求评审','访谈记录、样例实验、问题关闭单','整合负责人组织全组评审']], [337,476,339],192,415,24);

s=page('总体方案与后续交付','我们的总体方案是以可追踪的数据为底座，以公开检索和学者门户为入口，以审核和数据治理保证可信，以可解释统计支持共享。现有材料已经提供较多调研和规则，但需要统一范围、补足项目与状态模型，并完成真实验证和评审。本阶段交付应包括调研报告、SRS、SPEC、模型、汇报和证据，再由已评审需求进入系统分析、架构和构件设计。附录完整保留八张原图，供老师提问时展开。','任务书第二部分与里程碑；本次整合方案','四类成果共享闭环；三角色分工；统一规范与验收',true);
txt(s,'可追踪的数据\n可信的门户\n可解释的检索与统计',64,230,1152,236,52,C.white,true);
txt(s,'调研报告 ＋ SRS／SPEC ＋ 业务模型 ＋ 汇报与验证证据',64,532,1120,90,31,'#D5E3DA');

const originals=[
 ['普通用户用例图.png','普通用户用例图','公开检索与统计；注册账户扩展个人功能','M02；G01'],
 ['科研人员用例图.png','科研人员用例图','认领前后权限分离；审核管理员参与','M03第9节；G02'],
 ['普通用户活动图.png','普通用户活动图','成果、学者和统计三条查询路径','M02；G04'],
 ['作者检索活动图.png','作者检索活动图','同名候选、条件校验、空结果与返回上下文','M02 UC-01；G05'],
 ['门户认领活动图.png','门户认领活动图','三泳道：核验、补充、绑定竞争与审计','M03第10节；G03'],
 ['现状调研活动图.png','科研现状调研活动图','资料核查、资源条件、笔记与统计辅助','M03；G06'],
 ['核心任务类图.png','核心业务类图（预研）','四类成果与贡献关系；采集任务等对象需后续补齐','M03；G07'],
 ['检索请求时序图.png','检索请求时序图（预研）','参数校验、索引查询、权限过滤与结果返回','M03；G08'],
];
for(const [file,title,caption,source] of originals){
 s=page('附录 · '+title,'此页完整保留小组原图。'+caption+'。原图用于对应现有资料，主讲中的统一模型及优先级以配套方案为准。类图和时序图属于后续需求分析的预研材料。',source,'原图保留，答疑时放大查看');
 s.background.fill=C.white;
 s.images.add({blob:await fs.readFile(path.join(root,src,file)),contentType:'image/png',alt:title,fit:'contain',position:{left:64,top:175,width:1148,height:465}});
 txt(s,caption,64,647,1070,40,21,C.muted);
}

if(meta.length!==28||durations.reduce((a,b)=>a+b,0)!==900)throw new Error('Deck count/timing mismatch');
await fs.mkdir(path.join(tmp,'renders'),{recursive:true});
await fs.writeFile(path.join(tmp,'meta.json'),JSON.stringify(meta,null,2));
await fs.writeFile(path.join(tmp,'presentation.json'),JSON.stringify(p.toProto()));
let speech='# 学术成果分享平台：15分钟逐页讲稿\n\n主讲第1—20页，共900秒；第21—28页为原模型图答疑附录。每页讲稿也已写入PPT备注。\n\n';
for(let i=0;i<20;i++)speech+=`## 第${i+1}页 ${meta[i].title}（${meta[i].duration}秒）\n\n${meta[i].note}\n\n`;
speech+='## 答疑提示\n\n- 四类是否都做？论文优先支撑规模，其他三类仍有可演示数据路径；受限访问时用明确标识的模拟样本。\n- 指标是否已达到？都是SRS/SPEC建议目标，当前目录无实测报告。\n- 访谈多少人？未发现本小组原始访谈数据，第三方样本不当作本组样本。\n- ORCID格式正确是否可直接认领？不能；账号控制证据与实体标识是两件事，结合认证流程和人工证据核验。\n- 为什么机构总数大于成果总数？采用机构全计数，同一成果可关联多个机构；展示时注明。\n- 创新是什么？基础网络之外的筛选、最短共著路径及边的成果证据，评审确认。\n- 原Word是否已统一？原文件保留；补充方案和PPT给出修订建议，仍需回写SRS/SPEC并完成评审。\n';
await fs.writeFile(path.join(out,'15分钟逐页讲稿.md'),speech);
await (await PresentationFile.exportPptx(p)).save(path.join(tmp,'candidate.pptx'));
console.log('draft exported; rendering');
for(let i=0;i<meta.length;i++){
 const slide=p.slides.items[i];
 const blob=await p.export({slide,format:'png',scale:1.5});
 await fs.writeFile(path.join(tmp,'renders',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
 console.log('render',i+1);
}
await finalizePresentation({workspaceDir:root,candidatePath:path.join(tmp,'candidate.pptx'),finalPath:path.join(out,'学术成果分享平台_需求调研与建模_总体汇报.pptx'),pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:28,requiredNativeTableOwnerSlides:tables,fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath:path.join(tmp,'validation.json')});
console.log('finalized',meta.length,'slides');
