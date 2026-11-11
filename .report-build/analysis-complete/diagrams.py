"""Generate editable Draw.io, SVG and PNG from one sequence specification."""
from pathlib import Path
import json, math, html, textwrap
import xml.etree.ElementTree as E
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'需求分析/A组-需求分析整合版-v1.0'
FIG=OUT/'图件'; SRC=OUT/'模型源文件'
FONT='C:/Windows/Fonts/msyh.ttc'
INK='#26384B'; BLUE='#E9F0F7'; LINE='#748497'

def msg(id,a,b,text,ret=False): return dict(kind='msg',id=id,a=a,b=b,text=text,ret=ret)
def band(text): return dict(kind='band',text=text)
def frame(op,guard,rows): return dict(kind='frame',op=op,guard=guard,rows=rows)
def otherwise(guard): return dict(kind='else',guard=guard)
def ref(text): return dict(kind='ref',text=text)

SPECS=[
dict(file='05-门户认领审核时序图',title='门户认领审核 主交互',sub='图5-1  已审核科研身份是申请前提；审核材料仅向本人和有权审核人开放',
lanes=['申请人／审核人\n«actor»','认领与审核页面\n«boundary»','ClaimControl\n«control»','Account／\nScholarPortal\n«entity group»','ClaimApplication／\nReviewRecord\n«entity group»'],
rows=[
msg('CL01',0,1,'申请人提交目标门户与证明材料'),msg('CL02',1,2,'submitClaim(门户、材料版本、预期版本)'),
msg('CL03',2,3,'canApplyForPortal()；核对目标与有效绑定'),msg('CL04',3,2,'返回资格、目标及占用检查结果',True),
frame('break','未登录／身份未通过／材料不合法／已有冲突绑定',[msg('CL05',2,1,'返回具体原因；首次仍为 DRAFT，补交仍待补充')]),
msg('CL06',2,4,'submit(expectedVersion)；有效提交至 PENDING_REVIEW'),msg('CL07',4,2,'提交成功：申请编号、材料版本、对象版本',True),msg('CL08',2,1,'显示待审核回执；未产生门户管理权',True),
band('审核阶段  与首次提交分属不同用户请求'),
msg('CL09',0,1,'审核人打开申请并提交审核动作与理由'),msg('CL10',1,2,'reviewClaim(申请、动作、理由、预期版本)'),
msg('CL11',2,3,'checkObjectPermission(申请)；核对审核范围'),
msg('CL12',2,4,'读取当前状态和有权访问的材料版本'),
frame('break','无审核权限或材料／对象版本已变化',[msg('CL13',2,1,'拒绝本次操作并提示刷新；保留已提交状态')]),
frame('alt','证据不足且状态为 PENDING_REVIEW',[
msg('CL14',2,4,'requestMore(reason, version)＋appendDecision()'),
otherwise('证据不成立且状态为 PENDING_REVIEW'),
msg('CL15',2,4,'reject(reason, version)＋appendDecision()'),
otherwise('拟批准且状态为 PENDING_REVIEW'),ref('图5-2 CX01—CX06  事务内重验并原子创建授权')]),
msg('CL16',2,1,'仅提交成功后返回实际结果；失败不通知通过',True),
frame('opt','申请人对 NEED_MORE_INFO 补交材料',[
msg('CL17',0,1,'补交形成新材料版本；沿用原申请编号'),
ref('重入 CL02—CL08  校验通过后 submit() 回 PENDING_REVIEW')]),
ref('本人撤回与终审竞争见图5-2 CX07—CX10；终态再申请使用新编号')]),
dict(file='05a-认领原子授权与撤回子交互',title='认领原子授权与撤回竞争',sub='图5-2  调用自图5-1批准分支；两条路径是独立并发请求，非先批准再撤回',
lanes=['审核人／申请人\n«actor»','ClaimControl\n«control»','ClaimApplication\n«entity»','PortalAuthorization\n«entity»','ReviewRecord／\nAuditEntry\n«entity / value»'],
rows=[band('路径A  管理员批准请求'),msg('CX01',0,1,'approveClaim(申请、材料版本、expectedVersion)'),
frame('critical','批准事务  账号资格、审核权限、目标版本与双方有效唯一性重验',[
msg('CX02',1,2,'重读申请；仅 PENDING_REVIEW 且版本匹配可继续'),
msg('CX03',1,3,'复核有效授权：账号最多一个；门户最多一个'),
frame('alt','全部条件成立',[
msg('CX04',1,2,'approve(expectedVersion) → APPROVED'),
msg('CX05',1,3,'创建指定账号与门户的有效授权'),
msg('CX06',1,4,'appendDecision(批准, 理由)；追加审计；共同提交'),
otherwise('状态／权限／唯一性冲突或任一步持久化失败'),
band('整笔回滚或拒绝；读取实际已提交状态，不重置并发胜出的撤回')])]),
band('路径B  本人撤回请求  可与路径A竞争同一申请版本'),
msg('CX07',0,1,'withdrawClaim(申请、expectedVersion)'),
frame('critical','撤回事务  校验本人身份、当前状态和预期版本',[
frame('alt','PENDING_REVIEW 或 NEED_MORE_INFO 且版本匹配',[
msg('CX08',1,2,'withdraw(expectedVersion) → WITHDRAWN'),
msg('CX09',1,4,'追加撤回审计；共同提交，不创建授权'),
otherwise('审批已提交／版本过期／其他不允许状态'),
band('拒绝撤回，返回实际终态；不能撤销已经生效的授权')])]),
msg('CX10',1,0,'返回提交结果／版本冲突；同一版本最多一条路径成功',True),
ref('通过后解除授权使用 PortalAuthorization.revoke()；保留 APPROVED 和历史')]),
dict(file='06-检索请求处理时序图',title='检索请求处理 主交互',sub='图6-1  匿名用户可查询公开成果；列表、分页、详情固定同一公开版本',
lanes=['公众用户\n«actor»','搜索与详情页面\n«boundary»','SearchControl\n«control»','PublicRelease／\nReleaseEntry\n«entity group»','查询引擎／权限服务\n«control»'],
rows=[msg('Q01',0,1,'输入关键词、类型、人物、机构、时间与排序'),
frame('opt','输入同名人物且要求精确人物筛选',[ref('先显示人物候选及机构证据；用户确认 ScholarId 后继续')]),
msg('Q02',1,2,'search(条件、page_size、releaseId?、continuation?)'),
frame('break','参数非法／字段不适用／人物尚未确认',[
msg('Q03',2,1,'返回字段级原因并保留输入；不执行查询')]),
msg('Q04',2,3,'首次固定可用 release；续页验证原 release 与查询令牌'),
frame('break','公开版本已失效或无可用公开版本',[
msg('Q05',2,1,'说明版本失效或服务不可用；不混入最新数据')]),
msg('Q06',3,2,'返回 releaseId、分类版本、规则版本、数据范围',True),
ref('图6-2 QX01—QX08  同版检索＋实时权限过滤＋统一计数分页'),
msg('Q07',2,1,'返回可见列表、总量、分面、版本与查询令牌',True),
frame('alt','有效查询无命中',[
msg('Q08',1,0,'显示0条与当前条件；提供修改筛选入口',True),
otherwise('有效查询有命中'),msg('Q09',1,0,'按类型分组展示；保留来源、缺失值和状态',True)]),
band('同版详情  后续独立请求'),
msg('Q10',0,1,'打开结果详情'),msg('Q11',1,2,'detail(规范成果ID、原 releaseId、查询上下文)'),
msg('Q12',2,4,'核对当前权限与指定公开版本可用性'),
frame('break','无权限／版本失效／读取失败',[
msg('Q13',2,1,'分别提示无权访问、重新检索或稍后重试')]),
msg('Q14',2,3,'resolveEntry(workId)；readPublicView(permissionContext)'),
msg('Q15',3,2,'同版题录、贡献、来源、类型日期；不含私有证明',True),
msg('Q16',2,1,'返回详情与原查询上下文；返回列表恢复条件',True)]),
dict(file='06a-检索权限计数与分页子交互',title='检索权限计数与分页一致性',sub='图6-2  统一允许集合约束列表、总数与分面；权限变化不能通过旧快照恢复',
lanes=['SearchControl\n«control»','PermissionPolicy\n«control»','SearchIndex\n«read model»','PublicRelease／\nReleaseEntry\n«entity group»'],
rows=[msg('QX01',0,1,'获取当前公开可见约束与 permissionRevision'),
msg('QX02',1,0,'返回同一可见范围表达式与权限修订号',True),
msg('QX03',0,2,'查询固定 release；同贡献筛选＋可见约束'),
frame('critical','一次逻辑查询使用同一候选集合与同版读视图',[
band('先身份／类型／条件匹配 → 解析规范ID → 按实时可见范围过滤'),
band('再计算总数与分面 → 稳定排序 → 分页；不可先分页再剔除'),
msg('QX04',2,0,'返回规范ID页、total、facets与读视图标记',True)]),
msg('QX05',0,3,'按同一 release 批量读条目和来源快照'),
msg('QX06',0,1,'返回前重验 permissionRevision 与页内对象权限'),
frame('alt','权限修订未变化且所有数据同版',[
msg('QX07',0,0,'生成绑定条件、release、权限修订与排序位置的查询令牌'),
otherwise('权限已变化／原查询令牌权限修订过期'),
band('本次结果作废；同一release下重算一次，仍变化则提示刷新'),
otherwise('查询超时／索引或条目缺失／同版不可满足'),
band('明确失败并保留条件；不将故障计为0条，不降级拼接最新数据')]),
msg('QX08',0,0,'成功回主图Q07；失败直接返回可恢复原因'),
ref('内部一致性策略为本次设计决策；目标是列表 total facets 使用同一可见集合')])]

def wrap(s,width,size):
    f=ImageFont.truetype(FONT,size)
    out=[]
    for para in s.split('\n'):
        line=''
        for ch in para:
            if f.getlength(line+ch)>width and line:out.append(line);line=ch
            else:line+=ch
        out.append(line)
    return out

class Diagram:
    def __init__(self,spec):
        self.s=spec;self.W=1560;self.x=[130+i*(1300/(len(spec['lanes'])-1)) for i in range(len(spec['lanes']))]
        self.items=[];self.counter=0;self.messages=[]
    def text(self,t,x,y,w,size=23,bold=False,align='left'):
        lines=wrap(t,w,size);self.items.append(('text',t,x,y,w,(size+8)*len(lines),size,bold,align));return (size+8)*len(lines)
    def box(self,x,y,w,h,fill='white',stroke=LINE):self.items.append(('box',x,y,w,h,fill,stroke))
    def line(self,x,y,x2,y2,dashed=False,arrow=False):self.items.append(('line',x,y,x2,y2,dashed,arrow))
    def rows(self,rows,y,depth=0):
        for r in rows:
            kind=r['kind']
            if kind=='msg':
                self.messages.append(r)
                a,b=self.x[r['a']],self.x[r['b']]
                width=abs(a-b)-28 if a!=b else min(600,self.W-a-35)
                # Minimum one column for self messages, otherwise wrap at arrow width.
                tx=min(a,b)+14;h=self.text(r['id']+'  '+r['text'],tx,y+8,width,23)
                yy=y+h+20
                if a==b:
                    self.line(a,yy,a+60,yy);self.line(a+60,yy,a+60,yy+20);self.line(a+60,yy+20,a,yy+20,False,True);yy+=20
                else:self.line(a,yy,b,yy,r['ret'],True)
                y=yy+23
            elif kind=='band':
                h=(len(wrap(r['text'],self.W-120,23)))*31+20
                self.box(50+depth*8,y,self.W-100-depth*16,h,'#F5F7FA','#D9DDE3')
                self.text(r['text'],65+depth*8,y+10,self.W-140-depth*16,23);y+=h+18
            elif kind=='ref':
                h=len(wrap(r['text'],self.W-200,23))*31+30
                self.box(45+depth*8,y,self.W-90-depth*16,h,'#EDF3F8',LINE)
                self.text('ref',57+depth*8,y+12,55,22,True)
                self.text(r['text'],125+depth*8,y+12,self.W-185-depth*16,23);y+=h+22
            elif kind=='else':
                self.line(28+depth*8,y,self.W-28-depth*8,y,True)
                h=self.text('else ['+r['guard']+']',42+depth*8,y+10,self.W-100-depth*16,22,True);y+=h+24
            elif kind=='frame':
                idx=len(self.items);start=y
                h=self.text(r['op']+' ['+r['guard']+']',38+depth*8,y+10,self.W-95-depth*16,22,True)
                y=self.rows(r['rows'],y+h+24,depth+1)
                self.items.insert(idx,('box',22+depth*8,start,self.W-44-depth*16,y-start,'none',LINE));y+=20
        return y
    def build(self):
        self.text(self.s['title'],35,22,self.W-70,34,True)
        self.text(self.s['sub'],35,76,self.W-70,23)
        start=len(self.items)
        for i,l in enumerate(self.s['lanes']):
            self.box(self.x[i]-115,142,230,100,BLUE,LINE)
            self.text(l,self.x[i]-106,151,212,22,True,'center')
        y=self.rows(self.s['rows'],270);self.H=y+40
        for x in reversed(self.x):self.items.insert(start,('line',x,242,x,self.H-20,True,False))
        return self
    def save(self):
        im=Image.new('RGB',(self.W,self.H),'white');d=ImageDraw.Draw(im)
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.W}" height="{self.H}" viewBox="0 0 {self.W} {self.H}"><rect width="100%" height="100%" fill="white"/>']
        mx=E.Element('mxfile',host='app.diagrams.net');di=E.SubElement(mx,'diagram',name=self.s['title']);model=E.SubElement(di,'mxGraphModel',page='1',pageWidth=str(self.W),pageHeight=str(self.H));root=E.SubElement(model,'root');E.SubElement(root,'mxCell',id='0');E.SubElement(root,'mxCell',id='1',parent='0')
        for n,item in enumerate(self.items):
            kind,*v=item;id='e'+str(n)
            if kind=='box':
                x,y,w,h,fill,stroke=v
                d.rectangle((x,y,x+w,y+h),fill=None if fill=='none' else fill,outline=stroke,width=2)
                svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
                c=E.SubElement(root,'mxCell',id=id,parent='1',vertex='1',value='',style=f'rounded=0;fillColor={fill};strokeColor={stroke};strokeWidth=2;');E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
            elif kind=='text':
                t,x,y,w,h,size,bold,align=v;f=ImageFont.truetype(FONT,size,index=1 if bold else 0)
                lines=wrap(t,w,size)
                for j,l in enumerate(lines):
                    xx=x if align=='left' else x+w/2-f.getlength(l)/2;yy=y+j*(size+8)
                    d.text((xx,yy),l,font=f,fill=INK,anchor='lt')
                    svg.append(f'<text x="{xx}" y="{yy+size}" font-family="Microsoft YaHei, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{INK}">{html.escape(l)}</text>')
                c=E.SubElement(root,'mxCell',id=id,parent='1',vertex='1',value='\n'.join(lines),style=f'text;html=0;align={align};verticalAlign=top;whiteSpace=wrap;overflow=visible;spacing=0;fontFamily=Microsoft YaHei;fontSize={size};fontColor={INK};fontStyle={1 if bold else 0};');E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
            elif kind=='line':
                x,y,x2,y2,dash,arr=v
                length=math.hypot(x2-x,y2-y);segments=max(1,int(length/10))
                if dash:
                    for k in range(0,segments,2):
                        a=k/segments;b=min(1,(k+1)/segments);d.line((x+(x2-x)*a,y+(y2-y)*a,x+(x2-x)*b,y+(y2-y)*b),fill=LINE,width=2)
                else:d.line((x,y,x2,y2),fill=LINE,width=2)
                svg.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="{LINE}" stroke-width="2"'+(' stroke-dasharray="6 5"' if dash else '')+'/>')
                if arr:
                    sign=1 if x2>x else -1;pts=[(x2-sign*12,y2-6),(x2,y2),(x2-sign*12,y2+6)]
                    d.line(pts,fill=INK,width=3);svg.append('<polyline points="'+' '.join(f'{a},{b}' for a,b in pts)+f'" fill="none" stroke="{INK}" stroke-width="2"/>')
                c=E.SubElement(root,'mxCell',id=id,parent='1',edge='1',value='',style=f'edgeStyle=none;rounded=0;endArrow={"open" if arr else "none"};strokeColor={LINE};strokeWidth=2;dashed={1 if dash else 0};');g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});E.SubElement(g,'mxPoint',x=str(x),y=str(y),attrib={'as':'sourcePoint'});E.SubElement(g,'mxPoint',x=str(x2),y=str(y2),attrib={'as':'targetPoint'})
        svg.append('</svg>');FIG.mkdir(parents=True,exist_ok=True);SRC.mkdir(parents=True,exist_ok=True)
        (FIG/(self.s['file']+'.svg')).write_text('\n'.join(svg),encoding='utf-8');im.save(FIG/(self.s['file']+'.png'))
        E.indent(mx);E.ElementTree(mx).write(SRC/(self.s['file']+'.drawio'),encoding='utf-8',xml_declaration=True)
        return {'file':self.s['file'],'width':self.W,'height':self.H,'messages':self.messages}

def expand_actors(spec):
    # Different human roles must have independent UML lifelines.
    import copy
    s=copy.deepcopy(spec)
    if s['file'].startswith('05-'):
        s['lanes']=['申请人\n«actor»','有权审核人\n«actor»']+s['lanes'][1:]
        def remap(rows):
            for r in rows:
                if r['kind']=='msg':
                    for k in ['a','b']:
                        r[k]=(1 if r['id']=='CL09' else 0) if r[k]==0 else r[k]+1
                if r['kind']=='frame':remap(r['rows'])
        remap(s['rows'])
    elif s['file'].startswith('05a-'):
        s['lanes']=['有权审核人\n«actor»','申请人\n«actor»']+s['lanes'][1:]
        def remap(rows):
            for r in rows:
                if r['kind']=='msg':
                    for k in ['a','b']:
                        r[k]=(1 if r['id'] in ['CX07','CX10'] else 0) if r[k]==0 else r[k]+1
                if r['kind']=='frame':remap(r['rows'])
        remap(s['rows'])
    return s

def main():
    specs=[expand_actors(s) for s in SPECS]
    data=[Diagram(s).build().save() for s in specs]
    (SRC/'新增交互模型.json').write_text(json.dumps(specs,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'模型消息索引.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    ids=[m['id'] for d in data for m in d['messages']];assert len(ids)==len(set(ids))
    assert len(data)==4 and all(d['height']<4200 for d in data)
    print(json.dumps([{'file':d['file'],'size':[d['width'],d['height']],'messages':len(d['messages'])} for d in data],ensure_ascii=False))
if __name__=='__main__':main()
