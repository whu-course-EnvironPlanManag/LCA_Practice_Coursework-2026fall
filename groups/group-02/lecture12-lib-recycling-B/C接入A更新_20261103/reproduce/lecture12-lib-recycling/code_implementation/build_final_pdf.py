"""Independent ReportLab PDF; not a rendering or verification of the Word draft."""
import re
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,KeepTogether
from finalize_member_c import DELIVERY,REPORT
import pypdfium2 as pdfium

def main():
    pdfmetrics.registerFont(TTFont('MSYH','C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
    normal=ParagraphStyle('normal',fontName='MSYH',fontSize=10,leading=16,spaceAfter=7,wordWrap='CJK')
    title=ParagraphStyle('title',parent=normal,fontSize=20,leading=27,spaceAfter=15)
    heading=ParagraphStyle('heading',parent=normal,fontSize=14,leading=21,spaceBefore=12,spaceAfter=8,keepWithNext=True)
    small=ParagraphStyle('small',parent=normal,fontSize=8,leading=12,spaceAfter=0)
    caption=ParagraphStyle('caption',parent=normal,fontSize=9,alignment=1,leading=13)
    def plain(s):
        s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s).replace('**','').replace('`','')
        return escape(s)
    lines=(DELIVERY/'C成员经济与管理交付稿.md').read_text(encoding='utf-8').splitlines()
    story=[];i=0;width=495
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                parts=[x.strip() for x in lines[i].strip().strip('|').split('|')];i+=1
                if all(re.fullmatch('[-: ]+',x or '-') for x in parts):continue
                rows.append([Paragraph(plain(x),small) for x in parts])
            n=len(rows[0]);ratios={2:[.27,.73],3:[.25,.23,.52],5:[.11,.17,.23,.24,.25]}.get(n,[1/n]*n)
            table=Table(rows,colWidths=[width*r for r in ratios],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9EFF3')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#C1CCD4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,9)]);continue
        match=re.match(r'!\[([^\]]*)\]\(([^)]+)\)',line)
        if match:
            story.append(KeepTogether([Image(str(DELIVERY/match.group(2)),width=width,height=width*.6),Paragraph(plain(match.group(1)),caption)]))
        elif line.startswith('# '):story.append(Paragraph(plain(line[2:]),title))
        elif line.startswith('## '):story.append(Paragraph(plain(line[3:]),heading))
        else:story.append(Paragraph(plain(line),normal))
        i+=1
    output=DELIVERY/'C成员经济与管理交付稿.pdf'
    def footer(canvas,doc):
        canvas.setFont('MSYH',8);canvas.setFillColor(colors.HexColor('#62717F'))
        canvas.drawString(50,25,'成员C | 条件仿真交付稿 | 2026-11-03');canvas.drawRightString(545,25,str(doc.page))
    SimpleDocTemplate(str(output),pagesize=(595,842),leftMargin=50,rightMargin=50,topMargin=42,bottomMargin=45,title='成员C经济与管理条件交付稿',author='成员C（AI辅助）').build(story,onFirstPage=footer,onLaterPages=footer)
    qa=REPORT/'pdf_qa';qa.mkdir(parents=True,exist_ok=True)
    pdf=pdfium.PdfDocument(str(output))
    for j in range(len(pdf)):pdf[j].render(scale=1.5).to_pil().save(qa/f'page_{j+1:02}.png')
    print(f'Pages: {len(pdf)}');print(output)

if __name__=='__main__':main()
