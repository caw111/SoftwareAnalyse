from model import *
import html, xml.etree.ElementTree as ET, re, math

PAGES=[('00','核心业务类图',list(range(1,46))),('01','账号学者与门户授权',list(range(1,10))),('02','四类成果与专利身份',list(range(10,14))+list(range(22,26))),('03','贡献机构与领域关系',list(range(14,22))+list(range(26,30))),('04','来源采集与规范映射',list(range(30,38))),('05','治理更新与公开版本',list(range(38,46)))]
COLORS={'A':'#E5EFFA','B':'#E5F3EC','C':'#FFF0DA','D':'#EEE9F8'}
CM={c['name']:c for c in C}
WORK=OUT/'_work'; IMG=OUT/'图件'; IMG.mkdir(exist_ok=True)

def lines(c,main):
 attrs=c['attrs'][:3] if main else c['attrs']
 ops=c['ops'][:2] if main else c['ops']
 # Short forms in diagram, full contracts remain in dictionary.
 ops=[re.sub(r'\([^)]*\)', '()',x) for x in ops]
 return attrs,ops

def make_dot():
 for pid,title,ids in PAGES:
  rs=[r for r in R if int(r['id'][1:]) in ids]
  names=[c['name'] for c in C if pid=='00' or any(c['name'] in (r['a'],r['b']) for r in rs)]
  main=pid=='00'
  direction='TB' if pid in ('01','05') else 'LR'
  d=['digraph G {',f'graph [rankdir={direction}, splines=polyline, nodesep=0.75, ranksep=1.65, pad=0.35, outputorder=edgesfirst, bgcolor="white"];','node [shape=box, label="", fixedsize=true];','edge [fontname="Microsoft YaHei", fontsize=13, color="#53657C", arrowsize=1.5, labeldistance=1.5];']
  for n in names:
   a,o=lines(CM[n],main); w=300 if main else 330; h=52+len(a)*20+len(o)*21+24
   d.append(f'{n} [width={w/72:.4f},height={h/72:.4f}];')
  for r in rs:
   options={'id':r['id'],'label':r['label'].replace(' XOR',''),'taillabel':r['am'],'headlabel':r['bm'],'dir':'none'}
   if r['kind']=='generalization': options.update(dir='forward',arrowhead='empty',label='')
   if r['kind']=='composition': options.update(dir='back',arrowtail='diamond')
   if r['a']==r['b']: options['minlen']='1'
   d.append(r['a']+' -> '+r['b']+' ['+', '.join(k+'='+json.dumps(v,ensure_ascii=False) for k,v in options.items())+'];')
  d.append('}')
  (WORK/f'diagram-{pid}.dot').write_text('\n'.join(d),encoding='utf-8')

def cell(root,id,value,style,x,y,w,h,parent='1'):
 c=ET.SubElement(root,'mxCell',id=id,value=value,style=style,vertex='1',parent=parent)
 ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
 return c

def render():
 mx=ET.Element('mxfile',host='app.diagrams.net',modified='2026-10-23T00:00:00.000Z',agent='Codex XML authoring',version='24.7.17',type='device')
 sizes={}
 for pid,title,ids in PAGES:
  j=json.loads((WORK/f'layout-{pid}.json').read_text(encoding='utf-8')); main=pid=='00'
  bb=[float(v) for v in j['bb'].split(',')]; W=bb[2]+80; H=bb[3]+80
  sizes[pid]=[W,H]
  dia=ET.SubElement(mx,'diagram',id='A2-'+pid,name=title)
  model=ET.SubElement(dia,'mxGraphModel',grid='1',gridSize='10',page='1',pageScale='1',pageWidth=str(math.ceil(W)),pageHeight=str(math.ceil(H)),background='#FFFFFF')
  root=ET.SubElement(model,'root'); ET.SubElement(root,'mxCell',id='0'); ET.SubElement(root,'mxCell',id='1',parent='0')
  svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="white"/>','<g font-family="Microsoft YaHei,SimHei,Arial" fill="#172B4D">']
  def tx(id,text,x,y,w=400,h=24,size=15,bold=False,align='left',parent='1',color='#172B4D'):
   st=f'text;html=0;whiteSpace=wrap;overflow=hidden;align={align};verticalAlign=middle;fontFamily=Microsoft YaHei;fontSize={size};fontColor={color};strokeColor=none;fillColor=none;'
   if bold: st+='fontStyle=1;'
   cell(root,id,text,st,x,y,w,h,parent)
   # all text is one line here
   anchor='middle' if align=='center' else 'start'; xx=x+w/2 if align=='center' else x+3
   svg.append(f'<text x="{xx}" y="{y+h/2+size*.35}" text-anchor="{anchor}" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{html.escape(text)}</text>')
  def xy(p): return float(p[0])+40,bb[3]-float(p[1])+40
  objs={o['_gvid']:o for o in j['objects'] if 'pos' in o}
  occupied=[]
  for o in objs.values():
   x,y=xy(o['pos'].split(','));w=float(o['width'])*72;h=float(o['height'])*72
   occupied.append((x-w/2-3,y-h/2-3,x+w/2+3,y+h/2+3))
  def place_label(x,y,w,h,positions=None):
   def hits(box):return any(box[0]<z[2] and box[2]>z[0] and box[1]<z[3] and box[3]>z[1] for z in occupied)
   choices=[(0,0)]
   for delta in (14,28,42,56,70,90,120):choices.extend([(0,-delta),(0,delta),(-delta,0),(delta,0)])
   if positions:choices=[(xx-x,yy-y) for xx,yy in positions]
   for dx,dy in choices:
    box=(x+dx-w/2-2,y+dy-h/2-2,x+dx+w/2+2,y+dy+h/2+2)
    if not hits(box):occupied.append(box);return x+dx,y+dy
   occupied.append((x-w/2,y-h/2,x+w/2,y+h/2));return x,y
  def endpoint_positions(pts,head=False):
   ps=list(reversed(pts)) if head else pts
   ans=[]
   for distance in (28,40,55,70,90):
    left=distance
    for aa,bbp in zip(ps,ps[1:]):
     length=math.dist(aa,bbp)
     if length<.1:continue
     if left>length:left-=length;continue
     ux=(bbp[0]-aa[0])/length;uy=(bbp[1]-aa[1])/length
     for normal in (14,-14,24,-24,0):ans.append((aa[0]+ux*left-uy*normal,aa[1]+uy*left+ux*normal))
     break
   return ans
  rs=[r for r in R if int(r['id'][1:]) in ids]; rmap={r['id']:r for r in rs}
  for k,e in enumerate(j.get('edges',[])):
   r=rmap[e['id']]; pts=[]
   # xdot supplies untrimmed Bezier polyline points; straight segments retain graph layout.
   for op in e.get('_draw_',[]):
    if op['op'] in ('b','B'): pts=[xy(v) for v in op['points']]
   if not pts: continue
   ded=[]
   for p in pts:
    if not ded or math.dist(p,ded[-1])>0.01: ded.append(p)
   pts=ded
   # use visible stroke from graphviz including clipping, markers rendered from xdot polygons
   svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+'" fill="none" stroke="#53657C" stroke-width="1.5"/>')
   for section in ['_hdraw_','_tdraw_']:
    for op in e.get(section,[]):
     if op['op'] in ('p','P'):
      pol=[xy(v) for v in op['points']]
      fill='#53657C' if r['kind']=='composition' else 'white'
      svg.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in pol)+f'" fill="{fill}" stroke="#53657C" stroke-width="1.5"/>')
   a=objs[e['tail']]; b=objs[e['head']]
   style='edgeStyle=none;html=0;rounded=0;endArrow=none;startArrow=none;strokeColor=#53657C;strokeWidth=1.5;'
   if r['kind']=='generalization': style+='endArrow=block;endFill=0;endSize=16;'
   if r['kind']=='composition': style+='startArrow=diamond;startFill=1;startSize=14;'
   # pin observed boundary coordinates so the editable source uses the same route
   for side,obj,point in [('exit',a,pts[0]),('entry',b,pts[-1])]:
    cx,cy=xy(obj['pos'].split(',')); nw=float(obj['width'])*72; nh=float(obj['height'])*72
    rx=max(0,min(1,(point[0]-(cx-nw/2))/nw)); ry=max(0,min(1,(point[1]-(cy-nh/2))/nh))
    style+=f'{side}X={rx:.5f};{side}Y={ry:.5f};{side}Dx=0;{side}Dy=0;{side}Perimeter=1;'
   ec=ET.SubElement(root,'mxCell',id=r['id'],edge='1',parent='1',source=a['name'],target=b['name'],style=style,value='')
   geo=ET.SubElement(ec,'mxGeometry',relative='1',attrib={'as':'geometry'}); arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
   for x,y in pts[1:-1]: ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
   for typ,label in [('lp',e.get('label','')),('tail_lp',r['am']),('head_lp',r['bm'])]:
    if not label or typ not in e: continue
    x,y=xy(e[typ].split(',')); size=13; width=max(27,sum(13 if ord(ch)>255 else 7 for ch in label)+8); h=20
    x,y=place_label(x,y,width,h,endpoint_positions(pts,typ=='head_lp') if typ!='lp' else None)
    svg.append(f'<rect x="{x-width/2}" y="{y-h/2}" width="{width}" height="{h}" fill="white" opacity="0.94"/>')
    tx(r['id']+'-'+typ,label,x-width/2,y-h/2,width,h,size,False,'center')
  # node groups drawn after edge labels, matching graphviz layering
  for o in objs.values():
   n=o['name']; c=CM[n]; x,y=xy(o['pos'].split(',')); w=float(o['width'])*72; h=float(o['height'])*72; x-=w/2;y-=h/2
   attrs,ops=lines(c,main); color=COLORS[c['group']]
   cell(root,n,'','group;container=1;collapsible=0;recursiveResize=0;',x,y,w,h)
   cell(root,n+'-box','','rounded=0;fillColor=#FFFFFF;strokeColor=#53657C;strokeWidth=1.5;',0,0,w,h,n)
   cell(root,n+'-head','','rounded=0;fillColor='+color+';strokeColor=#53657C;strokeWidth=1.5;',0,0,w,48,n)
   svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white" stroke="#53657C" stroke-width="1.5"/>')
   svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="48" fill="{color}" stroke="#53657C" stroke-width="1.5"/>')
   # separate function preserves same node-relative positions in drawio
   def nt(id,txt,yy,sz=14,bold=False,center=False):
    tx(n+'-'+id,txt,x+7,y+yy,w-14,20,sz,bold,'center' if center else 'left')
    el=root[-1];el.set('parent',n); gg=el.find('mxGeometry');gg.set('x','7');gg.set('y',str(yy))
   nt('cn',c['cn']+(' «abstract»' if n=='Work' else ''),3,16,True,True)
   nt('en',n,25,14,True,True)
   for i,t in enumerate(attrs):nt('a'+str(i),'- '+t,55+i*20,13)
   yy=55+len(attrs)*20+2
   cell(root,n+'-separator','','shape=line;strokeColor=#53657C;strokeWidth=1;',0,yy,w,1,n)
   svg.append(f'<line x1="{x}" y1="{y+yy}" x2="{x+w}" y2="{y+yy}" stroke="#53657C"/>')
   for i,t in enumerate(ops):nt('o'+str(i),'+ '+t,yy+7+i*21,13)
  svg.append('</g></svg>')
  fname='02-核心业务类图' if main else f'02-局部{pid}-{title}'
  (IMG/(fname+'.svg')).write_text('\n'.join(svg),encoding='utf-8')
 ET.indent(mx); ET.ElementTree(mx).write(OUT/'02-核心业务类图.drawio',encoding='utf-8',xml_declaration=True)
 (WORK/'diagram-sizes.json').write_text(json.dumps(sizes),encoding='utf-8')
 print(sizes)

if __name__=='__main__':
 import sys
 make_dot() if len(sys.argv)<2 else render()
