from pathlib import Path
import re,os,json,shutil,subprocess,hashlib,zipfile,csv,sys
from copy import deepcopy
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK,WD_LINE_SPACING
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

BUILD=Path(__file__).resolve().parent
cases=json.loads((BUILD/'usecases.json').read_text(encoding='utf-8'))['cases']
def font(style,cn,size,bold=False):
    style.font.name='宋体';style.font.size=Pt(size);style.font.bold=bold;style.font.italic=False;style.font.color.rgb=RGBColor(0,0,0)
    rf=style.element.get_or_add_rPr().get_or_add_rFonts();rf.set(qn('w:eastAsia'),cn);rf.set(qn('w:ascii'),'宋体');rf.set(qn('w:hAnsi'),'宋体')
def border_table(t):
    pr=t._tbl.tblPr
    for x in pr.xpath('./w:tblBorders'):pr.remove(x)
    b=OxmlElement('w:tblBorders')
    for side in ['top','bottom','left','right','insideH','insideV']:
        x=OxmlElement('w:'+side);x.set(qn('w:val'),'single');x.set(qn('w:sz'),'4');x.set(qn('w:color'),'000000');b.append(x)
    pr.append(b)
    t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
def page_settings(sec):
    sec.page_width=Cm(21);sec.page_height=Cm(29.7);sec.top_margin=Cm(2.54);sec.bottom_margin=Cm(2.54);sec.left_margin=Cm(2.54);sec.right_margin=Cm(2.54);sec.header_distance=Cm(1.45);sec.footer_distance=Cm(1.65)
def field(p,instruction,text=''):
    r=p.add_run();start=OxmlElement('w:fldChar');start.set(qn('w:fldCharType'),'begin');r._r.append(start)
    code=OxmlElement('w:instrText');code.set(qn('xml:space'),'preserve');code.text=' '+instruction+' ';r._r.append(code)
    sep=OxmlElement('w:fldChar');sep.set(qn('w:fldCharType'),'separate');r._r.append(sep)
    if text:p.add_run(text)
    end=OxmlElement('w:fldChar');end.set(qn('w:fldCharType'),'end');p.add_run()._r.append(end)
def page_number(sec,fmt='decimal',start=1):
    pr=sec._sectPr
    for x in pr.xpath('./w:pgNumType'):pr.remove(x)
    n=OxmlElement('w:pgNumType');n.set(qn('w:fmt'),fmt);n.set(qn('w:start'),str(start));pr.append(n)
    sec.footer.is_linked_to_previous=False;p=sec.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=0;p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;field(p,'PAGE')
    for r in p.runs:r.font.size=Pt(9)
def line_header(sec,label=''):
    sec.header.is_linked_to_previous=False;p=sec.header.paragraphs[0];p.text=label;p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0
    for r in p.runs:r.font.size=Pt(9)
    b=OxmlElement('w:pBdr');bottom=OxmlElement('w:bottom');bottom.set(qn('w:val'),'single');bottom.set(qn('w:sz'),'4');bottom.set(qn('w:color'),'000000');bottom.set(qn('w:space'),'3');b.append(bottom);p._p.get_or_add_pPr().append(b)

reference=Document()
page_settings(reference.sections[0])
font(reference.styles['Normal'],'宋体',10.5)
normal=reference.styles['Normal'].paragraph_format;normal.line_spacing=Pt(15.6);normal.left_indent=Pt(18);normal.right_indent=Pt(18);normal.first_line_indent=Pt(21);normal.space_after=Pt(0)
for label,cn,size,align in [('Title','宋体',24,WD_ALIGN_PARAGRAPH.CENTER),('Heading 1','宋体',16,WD_ALIGN_PARAGRAPH.CENTER),('Heading 2','宋体',14,WD_ALIGN_PARAGRAPH.LEFT),('Heading 3','宋体',12,WD_ALIGN_PARAGRAPH.LEFT),('Heading 4','宋体',10.5,WD_ALIGN_PARAGRAPH.LEFT)]:
    st=reference.styles[label];font(st,cn,size)
    pf=st.paragraph_format;pf.alignment=align;pf.left_indent=0 if label in ['Title','Heading 1'] else Pt(18);pf.right_indent=0;pf.first_line_indent=0;pf.space_before=Pt(12);pf.space_after=Pt(8);pf.keep_with_next=True
for i in range(1,4):
    name='TOC '+str(i)
    if name not in reference.styles:reference.styles.add_style(name,1)
    st=reference.styles[name];font(st,'宋体',10.5)
    st.paragraph_format.left_indent=Pt(18+21*(i-1))
for st in reference.styles:
    if st.type==1 and st.name not in ['Normal','Title','Heading 1','Heading 2','Heading 3','Heading 4']:
        if st.name in ['Body Text','First Paragraph','Compact']:font(st,'宋体',10.5)
    if st.name.startswith('TOC'):
        font(st,'宋体',10.5);st.paragraph_format.first_line_indent=0;st.paragraph_format.right_indent=0;st.paragraph_format.space_after=0;st.paragraph_format.line_spacing=Pt(15.6)
for style in ['Source Code','Caption']:
    if style not in reference.styles:reference.styles.add_style(style,1)
font(reference.styles['Source Code'],'宋体',8)
font(reference.styles['Caption'],'宋体',9)
reference.save(BUILD/'repository-reference.docx')

def style_cells(t,widths=None,repeat=True):
    border_table(t)
    if widths is None:
        widths=[15.9/len(t.columns)]*len(t.columns)
        if len(widths)>=3:
            lens=[max(len(row.cells[i].text) for row in t.rows) for i in range(len(widths))]
            weights=[max(4,min(n,140))**.5 for n in lens];widths=[15.9*w/sum(weights) for w in weights]
    for i,col in enumerate(t.columns):col.width=Cm(widths[i])
    for ri,row in enumerate(t.rows):
        trpr=row._tr.get_or_add_trPr()
        if ri==0 and repeat:trpr.append(OxmlElement('w:tblHeader'))
        for ci,c in enumerate(row.cells):
            c.width=Cm(widths[ci]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr=c._tc.get_or_add_tcPr()
            for x in pr.xpath('./w:shd|./w:tcMar'):pr.remove(x)
            margins=OxmlElement('w:tcMar')
            for side,value in [('left',65),('right',65),('top',20),('bottom',20)]:
                m=OxmlElement('w:'+side);m.set(qn('w:w'),str(value));m.set(qn('w:type'),'dxa');margins.append(m)
            pr.append(margins)
            for p in c.paragraphs:
                pf=p.paragraph_format;pf.left_indent=0;pf.right_indent=0;pf.first_line_indent=0;pf.space_before=0;pf.space_after=0;pf.line_spacing=Pt(14);pf.keep_with_next=False;pf.widow_control=True
                for r in p.runs:
                    r.font.size=Pt(10.5);r.font.name='宋体';r.font.bold=False;r.font.color.rgb=RGBColor(0,0,0);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')

def author(source,dest):
    text=source.read_text(encoding='utf-8');title=text.splitlines()[0].lstrip('# ').strip()
    temp_md=BUILD/('body-'+dest.stem+'.md');temp_md.write_text('\n'.join(text.splitlines()[1:]),encoding='utf-8')
    temp_docx=BUILD/('body-'+dest.name)
    subprocess.run(['pandoc',str(temp_md),'-f','markdown-implicit_figures','-t','docx','--shift-heading-level-by=-1','--reference-doc',str(BUILD/'repository-reference.docx'),'--resource-path',str(source.parent),'-o',str(temp_docx)],cwd=source.parent,check=True)
    d=Document(temp_docx)
    for rel in d.part.rels.values():
        if rel.reltype.endswith('/hyperlink') and rel.is_external and not re.match(r'^(https?://|mailto:|#)',rel.target_ref):
            target=(source.parent/rel.target_ref).resolve()
            if not target.is_file():raise ValueError((source,rel.target_ref))
            rel._target=Path(os.path.relpath(target,dest.parent)).as_posix()
    # Remove the parser-generated header row from use-case specification tables.
    for t in d.tables:
        is_uc=len(t.columns)==3 and t.cell(0,0).text=='项目' and len(t.rows)>1 and t.cell(1,0).text=='用例名称'
        if is_uc:
            t._tbl.remove(t.rows[0]._tr)
            uc_id=t.cell(0,2).text.split()[0]
            uc=next(c for c in cases if c['id']==uc_id)
            t.cell(7,2).text='\n'.join(f'{i}. {step}' for i,step in enumerate(uc['steps'],1))
            t.cell(8,2).text='\n'.join(uc['alt'])
            style_cells(t,[.9,.9,14.1],repeat=False)
            for i,row in enumerate(t.rows):
                if row.cells[0].text not in ['后置条件','事件流']:row.cells[0].merge(row.cells[1])
            for start in [5,7]:
                t.cell(start+1,0).text='';t.cell(start,0).merge(t.cell(start+1,0))
            for row in t.rows:
                for c in row.cells[:2]:
                    for p in c.paragraphs:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                if row._tr.xpath('.//wp:inline'):row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        else:style_cells(t)
    for p in d.paragraphs:
        pf=p.paragraph_format;pf.widow_control=True
        if p.style.name in ['Normal','Body Text','First Paragraph']:
            pf.left_indent=Pt(18);pf.right_indent=Pt(18);pf.first_line_indent=Pt(21);pf.line_spacing=Pt(15.6);pf.space_after=0
        if p.text.startswith(('表 ','图 ')):
            p.style='Caption';pf.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.left_indent=0;pf.right_indent=0;pf.first_line_indent=0
        if p.style.name=='Source Code':pf.line_spacing=Pt(10);pf.first_line_indent=0;pf.left_indent=Pt(18);pf.right_indent=0
    for inline in d._element.body.xpath('.//wp:inline'):
        ext=inline.find(qn('wp:extent'));cx=int(ext.get('cx'));cy=int(ext.get('cy'))
        in_table=bool(inline.xpath('ancestor::w:tc'))
        limit_w=Cm(13.7 if in_table else 15.5);limit_h=Cm(17.8 if in_table else 19.0)
        scale=min(limit_w/cx,limit_h/cy,1)
        ext.set('cx',str(int(cx*scale)));ext.set('cy',str(int(cy*scale)))
        for e in inline.xpath('.//a:xfrm/a:ext'):e.set('cx',str(int(cx*scale)));e.set('cy',str(int(cy*scale)))
    for pe in list(d._element.body.xpath('.//w:p')):
        if pe.xpath('.//wp:inline'):
            p=Paragraph(pe,d._body);pf=p.paragraph_format
            pf.line_spacing=1.0;pf.space_before=Pt(6);pf.space_after=Pt(6)
            pf.left_indent=0;pf.right_indent=0;pf.first_line_indent=0
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            caption_text=''.join(pe.xpath('.//w:t/text()')).strip()
            if caption_text:
                for child in list(pe):
                    if child.tag==qn('w:r') and child.xpath('.//w:t') and not child.xpath('.//wp:inline'):pe.remove(child)
                caption_text=re.sub(r'^(图 \d+-\d+) (活动图|状态图|时序图|类图|用例图) ',r'\1 ',caption_text)
                caption_text=re.sub(r'(?<= )\d{2}_','',caption_text).replace('.drawio','').replace('_',' ')
                cap=OxmlElement('w:p');pe.addnext(cap);cp=Paragraph(cap,d._body);cp.style='Caption';cp.add_run(caption_text)
                cp.alignment=WD_ALIGN_PARAGRAPH.CENTER;cpf=cp.paragraph_format
                cpf.line_spacing=1.0;cpf.space_before=0;cpf.space_after=Pt(4);cpf.first_line_indent=0;cpf.left_indent=0;cpf.right_indent=0
                for r in cp.runs:r.font.size=Pt(9)
            pf.keep_with_next=True

    # Prepend front matter inside the same OPC package, preserving all body image relationships.
    body=d._element.body;original=[e for e in list(body) if e.tag!=qn('w:sectPr')]
    for e in original:body.remove(e)
    sec=d.sections[0];page_settings(sec);sec.different_first_page_header_footer=False
    sec.header.is_linked_to_previous=False;sec.header.paragraphs[0].text='';sec.footer.paragraphs[0].text=''
    if title=='需求调研报告':line_header(sec)
    p=d.add_paragraph('软件系统分析与设计作业');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(36);p.paragraph_format.space_after=Pt(14);p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0
    for r in p.runs:r.font.size=Pt(14);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
    p=d.add_paragraph('学术成果分享平台');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(10);p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0
    for r in p.runs:r.font.size=Pt(26);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
    p=d.add_paragraph(title,'Title');p.paragraph_format.space_before=0;p.paragraph_format.space_after=Pt(26)
    meta=d.add_table(rows=4,cols=2);meta.cell(0,0).merge(meta.cell(0,1)).text='项目组成员信息'
    for row,values in zip(meta.rows[1:],[['小组编号','9组'],['小组名称','1011101011'],['小组联系人','待填写']]):
        for c,v in zip(row.cells,values):c.text=v
    style_cells(meta,[2.5,13.4],repeat=False)
    meta.cell(0,0).width=Cm(15.9)
    meta.cell(0,0).paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
    for row in meta.rows[1:]:row.cells[0].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
    p=d.add_paragraph('2026 年');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(32);p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0
    for r in p.runs:r.font.size=Pt(15)
    d.add_page_break()
    p=d.add_paragraph('版本变更历史');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0;p.paragraph_format.space_after=Pt(8)
    for r in p.runs:r.font.size=Pt(14);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
    history=d.add_table(rows=1,cols=5)
    for c,v in zip(history.rows[0].cells,['版本','提交日期','主要编制人','审核人','版本说明']):c.text=v
    for entry in [['v1.0','20261010','待填写','待填写','已有资料整合稿'],['v1.1','20261010','待填写','待填写','原稿记载的文字整理'],['v1.2','20261012','待填写','待填写','当前 images 图文同步'],['v2.0','20261012','待填写','待填写','按参考仓库重构章节、用例与格式']]:
        row=history.add_row()
        for c,v in zip(row.cells,entry):c.text=v
    for _ in range(2):history.add_row()
    style_cells(history,[1.15,2.45,3.0,2.2,7.1],repeat=True)
    toc_sec=d.add_section(WD_SECTION_START.NEW_PAGE);page_settings(toc_sec);toc_sec.different_first_page_header_footer=False;line_header(toc_sec);page_number(toc_sec,'upperRoman',1)
    p=d.add_paragraph('目录','Heading 1');p.paragraph_format.space_before=0
    # Keep the directory title out of its own automatic outline.
    p.style='Normal';p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.left_indent=0;p.paragraph_format.right_indent=0;p.paragraph_format.first_line_indent=0;p.paragraph_format.space_after=Pt(12)
    for r in p.runs:r.font.size=Pt(16);r._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
    toc=d.add_paragraph();toc.paragraph_format.left_indent=Pt(18);toc.paragraph_format.first_line_indent=0;field(toc,'TOC \\o "1-3" \\h \\z \\u','目录由 Word 更新')
    body_sec=d.add_section(WD_SECTION_START.NEW_PAGE);page_settings(body_sec);body_sec.different_first_page_header_footer=False;line_header(body_sec,'软件系统分析与设计课程：'+title);page_number(body_sec,'decimal',1)
    for e in original:body.insert(len(body)-1,e)
    for st in d.styles:
        if st.name in ['Title','Subtitle'] or st.name.startswith('Heading'):
            for x in st.element.xpath('./w:pPr/w:pBdr'):x.getparent().remove(x)
    for cover_p in d.paragraphs:
        if cover_p._p.xpath('.//w:br[@w:type="page"]'):break
        cover_p.paragraph_format.line_spacing=1.2
    for cover_style in ['Title','Heading 1','Heading 2','Heading 3']:
        d.styles[cover_style].paragraph_format.line_spacing=1.2
    update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');d.settings.element.append(update)
    d.core_properties.author='9组 1011101011';d.core_properties.title=title;d.core_properties.subject='v2.0 参考仓库格式重构';d.core_properties.comments='结构与视觉格式参考用户指定仓库；内容为本组材料，人工签核待完成'
    dest.parent.mkdir(parents=True,exist_ok=True);d.save(dest)
    print('AUTHORED',dest.name,'figures',len(d.inline_shapes))

