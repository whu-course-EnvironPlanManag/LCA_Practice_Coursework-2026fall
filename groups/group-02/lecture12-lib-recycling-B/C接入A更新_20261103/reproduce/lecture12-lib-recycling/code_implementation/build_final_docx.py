"""AI-assisted Word export of the conditional C submission; no invented signatures."""
from pathlib import Path
import re
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from finalize_member_c import DELIVERY

def fontstyle(style,name='微软雅黑',size=11):
    style.font.name=name;style.font.size=Pt(size)
    style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),name)
    style.font.color.rgb=RGBColor(0,0,0)

def plain(s):
    s=re.sub(r'\[([^\]]+)\]\([^\)]+\)',r'\1',s)
    return s.replace('**','').replace('`','')

def add_table(doc,lines):
    body=[]
    for line in lines:
        cells=[plain(x.strip()) for x in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r'[-: ]+',x or '-') for x in cells):continue
        body.append(cells)
    table=doc.add_table(rows=0,cols=len(body[0]));table.autofit=False
    widths={2:[2.0,4.8],3:[1.7,1.4,3.7],5:[.7,1.3,1.7,1.6,1.5]}.get(len(body[0]))
    if widths:
        for col,w in zip(table.columns,widths):col.width=Inches(w)
    for i,cells in enumerate(body):
        row=table.add_row()
        for j,text in enumerate(cells):
            cell=row.cells[j];cell.text=text;cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcPr=cell._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            tcPr.append(borders)
            margins=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),'80');e.set(qn('w:type'),'dxa');margins.append(e)
            tcPr.append(margins)
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'DBE6EF' if i==0 else ('F5F7F9' if i%2==0 else 'FFFFFF'));tcPr.append(shade)
            for p in cell.paragraphs:
                p.paragraph_format.space_after=Pt(2);p.paragraph_format.space_before=Pt(2)
                p.paragraph_format.line_spacing=1.12
                for run in p.runs:run.font.size=Pt(9.5);run.bold=(i==0)
                if i>0 and j>0 and len(text)<28:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        trPr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trPr.append(cant)
        if i==0:repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
    doc.add_paragraph().paragraph_format.space_after=Pt(3)

def main():
    source=DELIVERY/'C成员经济与管理交付稿.md'
    doc=Document();sec=doc.sections[0]
    sec.page_width=Inches(8.5);sec.page_height=Inches(11)
    sec.top_margin=Inches(.7);sec.bottom_margin=Inches(.7);sec.left_margin=Inches(.75);sec.right_margin=Inches(.75)
    for name in ['Normal','Body Text','Caption','List Bullet']:fontstyle(doc.styles[name])
    for name,size in [('Title',21),('Heading 1',15),('Heading 2',12)]:fontstyle(doc.styles[name],size=size)
    normal=doc.styles['Normal'].paragraph_format;normal.line_spacing=1.25;normal.space_after=Pt(6)
    for name in ['Heading 1','Heading 2']:
        p=doc.styles[name].paragraph_format;p.space_before=Pt(12);p.space_after=Pt(6);p.keep_with_next=True
    doc.core_properties.title='宜昌退役动力电池园区成员C经济与管理交付稿'
    doc.core_properties.author='成员C  AI辅助整理'
    doc.core_properties.subject='条件仿真版本  不等同实证全厂利润与合规认证'
    lines=source.read_text(encoding='utf-8').splitlines();i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('|'):
            group=[]
            while i<len(lines) and lines[i].startswith('|'):group.append(lines[i]);i+=1
            add_table(doc,group);continue
        match=re.match(r'!\[([^\]]*)\]\(([^)]+)\)',line)
        if match:
            p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
            p.add_run().add_picture(str(DELIVERY/match.group(2)),width=Inches(6.8))
            cap=doc.add_paragraph(match.group(1),'Caption');cap.alignment=WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.keep_with_next=False
        elif line.startswith('# '):doc.add_paragraph(plain(line[2:]),'Title')
        elif line.startswith('## '):doc.add_paragraph(plain(line[3:]),'Heading 1')
        elif line.startswith('- '):doc.add_paragraph(plain(line[2:]),'List Bullet')
        else:doc.add_paragraph(plain(line))
        i+=1
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=footer.add_run('成员C 条件仿真交付稿  ');r.font.size=Pt(9)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    path=DELIVERY/'C成员经济与管理交付稿.docx';doc.save(path);print(path)

if __name__=='__main__':main()
