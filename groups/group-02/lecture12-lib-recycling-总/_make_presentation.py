# -*- coding: utf-8 -*-
"""生成《退役动力电池回收园区规划》综合汇报 PPT（A/B/C 分工 + 脚标归属）。"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from PIL import Image

# ---------------- 主题 ----------------
DARK   = RGBColor(0x0F, 0x3D, 0x2A)   # 深绿（封面/页眉）
PRIMARY= RGBColor(0x21, 0x78, 0x4E)   # 主绿
SECOND = RGBColor(0x5A, 0xA7, 0x81)   # 浅绿
ACCENT = RGBColor(0xE8, 0xB8, 0x4B)   # 金
LIGHT  = RGBColor(0xF1, 0xF7, 0xF3)   # 浅底
INK    = RGBColor(0x24, 0x33, 0x2B)   # 正文深色
MUTED  = RGBColor(0x6E, 0x7F, 0x74)   # 弱化
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
TEAL   = RGBColor(0x02, 0x80, 0x90)   # 成员B
GOLD   = RGBColor(0xE8, 0xB8, 0x4B)   # 成员C
LINE   = RGBColor(0xD8, 0xE6, 0xDD)

HEAD_FONT = "微软雅黑"
SERIF_FONT = "宋体"

BASE = r"E:\LCA_Practice_Coursework-2026fall\groups\group-02\lecture12-lib-recycling-总"
FIGS = BASE + r"\figures_output\final_20261104"
FIGB = r"E:\LCA_Practice_Coursework-2026fall\groups\group-02\lecture12-lib-recycling-B\figures_output"
FIGA = r"E:\LCA_Practice_Coursework-2026fall\groups\group-02\lecture12-lib-recycling\figures_output"

OUT_PPTX = BASE + r"\退役动力电池回收园区规划_综合汇报_A_B_C分工.pptx"

MEMBER = {
    "A":   ("成员A", "物质流 · 工艺", PRIMARY, WHITE),
    "B":   ("成员B", "环境 · LCA",   TEAL,    WHITE),
    "C":   ("成员C", "经济 · 政策",  GOLD,    INK),
    "ALL": ("综合",   "联合汇报",     DARK,    WHITE),
}

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

SW = 13.333
SH = 7.5
PAGE = {"n": 0}


def set_run(run, text=None, size=14, bold=False, color=INK, font=HEAD_FONT, italic=False):
    if text is not None:
        run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {})
        rPr.append(ea)
    ea.set('typeface', font)
    return run


def rect(slide, x, y, w, h, fill, line=None, rounded=False, radius=0.08):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def text(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=4, line_spacing=1.0, wrap=True):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    if isinstance(runs, str):
        runs = [[(runs, {})]]
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        for seg in para:
            txt, st = seg
            r = p.add_run()
            set_run(r, txt, **st)
    return tb


def header(slide, title, member, section_note):
    rect(slide, 0, 0, SW, 1.18, DARK)
    rect(slide, 0, 1.18, SW, 0.045, ACCENT)
    text(slide, 0.62, 0.24, 9.6, 0.8,
         [[(title, {"size": 26, "bold": True, "color": WHITE, "font": HEAD_FONT})]],
         anchor=MSO_ANCHOR.MIDDLE)
    nm, role, col, tcol = MEMBER[member]
    rect(slide, 10.55, 0.30, 2.25, 0.60, col, rounded=True, radius=0.5)
    text(slide, 10.55, 0.30, 2.25, 0.60,
         [[("【%s】 %s" % (nm[2:], nm) if member != "ALL" else nm, {"size": 15, "bold": True, "color": tcol})]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if section_note:
        text(slide, 0.62, 0.92, 9.6, 0.24,
             [[(section_note, {"size": 11, "color": SECOND, "bold": False})]])


def footer(slide, member, note):
    nm = MEMBER[member][0]
    if member == "ALL":
        label = "综合（A/B/C 联合）"
    else:
        label = "%s %s" % (nm, MEMBER[member][1])
    rect(slide, 0, 7.02, SW, 0.48, LIGHT)
    PAGE["n"] += 1
    text(slide, 0.62, 7.10, 9.4, 0.34,
         [[("所属：%s · %s" % (label, note), {"size": 10.5, "color": MUTED})]],
         anchor=MSO_ANCHOR.MIDDLE)
    text(slide, 11.6, 7.10, 1.15, 0.34,
         [[("第 %d 页" % PAGE["n"], {"size": 10.5, "color": MUTED})]],
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def new_slide(member="ALL", title="", section_note=""):
    slide = prs.slides.add_slide(BLANK)
    rect(slide, 0, 0, SW, SH, WHITE)
    header(slide, title, member, section_note)
    return slide


def figure(slide, path, x, y, w, h, border=True):
    im = Image.open(path)
    ar = im.width / im.height
    box_ar = w / h
    if ar > box_ar:
        nw = w
        nh = w / ar
        nx = x
        ny = y + (h - nh) / 2
    else:
        nh = h
        nw = h * ar
        ny = y
        nx = x + (w - nw) / 2
    pic = slide.shapes.add_picture(path, Inches(nx), Inches(ny), Inches(nw), Inches(nh))
    pic.line.color.rgb = LINE
    pic.line.width = Pt(0.75)
    return pic


def chip_row(slide, x, y, items, size=14, gap=0.25):
    """items: list of (label, color_hex). 依次横向排布胶囊。"""
    cx = x
    for label, col in items:
        w = 0.26 * len(label) + 0.5
        if w < 1.1:
            w = 1.1
        rect(slide, cx, y, w, 0.5, col, rounded=True, radius=0.5)
        text(slide, cx, y, w, 0.5, [[(label, {"size": size, "bold": True, "color": WHITE})]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        cx += w + gap


# ================= Slide 1 封面 =================
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, SW, SH, DARK)
rect(s, 0, 0, SW, 0.16, ACCENT)
text(s, 0.9, 1.05, 11.5, 0.5,
     [[("第十三讲 · 产业园区/工程尺度综合规划", {"size": 15, "color": SECOND, "bold": True})]])
text(s, 0.9, 1.6, 11.5, 1.9,
     [[("退役动力电池回收园区", {"size": 52, "bold": True, "color": WHITE, "font": SERIF_FONT})],
      [("物质流 · 环境影响 · 经济政策", {"size": 30, "bold": True, "color": ACCENT, "font": SERIF_FONT})]],
     space_after=6)
rect(s, 0.92, 4.25, 2.4, 0.03, ACCENT)
text(s, 0.9, 4.45, 11.0, 0.4,
     [[("面向宜昌退役动力电池循环利用园区 · R1 年度物料流 · 1 t LCE-eq · R1_2026_gate",
        {"size": 14, "color": RGBColor(0xC9, 0xDB, 0xD0)})]])
# 成员分工卡片
cards = [
    ("A", "成员A", "物质流 / 工艺", "市域 dMFA · 园区物料流 · 工艺清单与接口"),
    ("B", "成员B", "环境 / LCA", "环境因子 · 多情景仿真 · 帕累托寻优"),
    ("C", "成员C", "经济 / 政策", "投资费用 · LCOR / MAC · 政策引擎与推荐"),
]
cw = 3.85
gap = 0.28
x0 = 0.9
for i, (k, nm, role, desc) in enumerate(cards):
    col = MEMBER[k][2]
    tcol = MEMBER[k][3]
    cx = x0 + i * (cw + gap)
    rect(s, cx, 5.15, cw, 1.55, RGBColor(0x14, 0x50, 0x33), rounded=True, radius=0.10)
    rect(s, cx, 5.15, 0.12, 1.55, col)
    text(s, cx + 0.3, 5.32, cw - 0.5, 0.5,
         [[("%s  %s" % (k, nm), {"size": 18, "bold": True, "color": tcol})]])
    text(s, cx + 0.3, 5.82, cw - 0.5, 0.35, [[(role, {"size": 13, "color": ACCENT, "bold": True})]])
    text(s, cx + 0.3, 6.14, cw - 0.5, 0.5,
         [[(desc, {"size": 10, "color": RGBColor(0xC9, 0xDB, 0xD0)})]])
text(s, 0.9, 6.95, 11.5, 0.4,
     [[("小组 02 · 2026-11-04 · 规划仿真汇报（非企业实测）",
        {"size": 12, "color": RGBColor(0x9E, 0xB7, 0xA7)})]])

# ================= Slide 2 目录 =================
s = new_slide("ALL", "汇报目录与结构", "内容按成员 A / B / C 三线分工展开，脚标标注所属")
toc = [
    ("01", "项目背景与协作分工", "目标 · 功能单位 · 边界 · RACI 职责矩阵", "A/B/C"),
    ("02", "成员 A — 物质流与工艺", "市域 dMFA · R1 园区物料流 · 质量平衡 · 数据接口", "A"),
    ("03", "成员 B — 环境 LCA", "LCA 模型 · 多情景仿真 · 敏感性 · 帕累托寻优", "B"),
    ("04", "成员 C — 经济与政策", "投资费用 · LCOR/MAC · 政策引擎 · 推荐方案", "C"),
    ("05", "综合结论与推荐方案", "一句话方案 · 三阶段路线图 · 五个硬条件", "A/B/C"),
    ("06", "局限边界与致谢", "条件性结论 · 未闭合项 · Q&A", "A/B/C"),
]
y = 1.5
for num, t, d, who in toc:
    rect(s, 0.62, y, 0.06, 0.78, PRIMARY)
    text(s, 0.82, y - 0.05, 1.3, 0.8, [[(num, {"size": 30, "bold": True, "color": SECOND})]])
    text(s, 2.2, y - 0.02, 6.6, 0.45, [[(t, {"size": 18, "bold": True, "color": INK})]])
    text(s, 2.2, y + 0.42, 6.8, 0.34, [[(d, {"size": 12.5, "color": MUTED})]])
    # who chips
    col = PRIMARY if who == "A/B/C" else MEMBER[who][2]
    tcol = MEMBER[who][3] if who in MEMBER else WHITE
    rect(s, 10.4, y + 0.08, 2.3, 0.5, col, rounded=True, radius=0.5)
    text(s, 10.4, y + 0.08, 2.3, 0.5,
         [[(("联合 A·B·C" if who == "A/B/C" else "成员 " + who), {"size": 13, "bold": True, "color": tcol})]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    y += 0.94

# ================= Slide 3 背景与分工 =================
s = new_slide("ALL", "项目背景与三方协作框架", "三方数据同工况咬合，交叉校验 A 侧 FAIL = 0")
# 左：项目背景
rect(s, 0.62, 1.45, 5.6, 5.3, LIGHT, rounded=True, radius=0.06)
text(s, 0.9, 1.62, 5.1, 0.4, [[("项目画像", {"size": 16, "bold": True, "color": PRIMARY})]])
bg = [
    ("规划对象", "宜昌退役动力电池循环利用园区"),
    ("设计来料", "80,000 t/a（负荷 0.85 → 实际 68,000 t/a）"),
    ("功能单位", "1 t 碳酸锂当量（LCE-eq）"),
    ("系统边界", "R1_2026_gate（到厂至产品/副产出厂）"),
    ("再生入口", "60,579.5 t/a；梯次保留 7,420.5 t/a"),
    ("LCE-eq 产量", "3,064.34 t/a（合规改进 3,172.04）"),
    ("数据属性", "组内设定 / 文献原值 / 文献迁移 / 情景假设"),
]
cy = 2.1
for k, v in bg:
    text(s, 0.9, cy, 1.7, 0.32, [[(k, {"size": 12, "bold": True, "color": INK})]])
    text(s, 2.62, cy, 3.45, 0.5, [[(v, {"size": 12, "color": MUTED})]], wrap=True, line_spacing=1.0)
    cy += 0.60
# 右：分工卡片
text(s, 6.55, 1.6, 6.1, 0.4, [[("职责分工（RACI 简表）", {"size": 16, "bold": True, "color": PRIMARY})]])
roles = [
    ("A", "成员A · 物质流与工艺",
     "市域 dMFA、园区物料流、工艺清单、产品去向；交付同源年度活动量与计价接口。"),
    ("B", "成员B · 环境 LCA",
     "环境因子、同工况 LCA、多情景仿真（≥500 组）、敏感性分析与帕累托寻优。"),
    ("C", "成员C · 经济与政策",
     "投资费用、LCOR/MAC、政策引擎与测试、多目标寻优与推荐方案。"),
]
ry = 2.08
for k, nm, d in roles:
    col = MEMBER[k][2]
    tcol = MEMBER[k][3]
    rect(s, 6.55, ry, 6.0, 1.32, WHITE, line=LINE, rounded=True, radius=0.10)
    rect(s, 6.55, ry, 0.1, 1.32, col)
    text(s, 6.82, ry + 0.12, 5.6, 0.4,
         [[(nm, {"size": 14.5, "bold": True, "color": col})]])
    text(s, 6.82, ry + 0.52, 5.62, 0.7, [[(d, {"size": 11.5, "color": INK})]], line_spacing=1.05)
    ry += 1.48
footer(s, "ALL", "A 交付物理数据 · B 交付环境结果 · C 交付经济政策，三线同工况咬合")

# ================= Slide 4 成员A dMFA =================
s = new_slide("A", "市域动态物质流分析（dMFA）", "覆盖既有首装队列 2010—2040，收集率三情景")
# 左：文字
text(s, 0.62, 1.45, 5.1, 0.4, [[("方法与队列", {"size": 15, "bold": True, "color": PRIMARY})]])
am = [
    ("建模对象", "2010—2025 首装整包队列（LFP / 未细分三元），外推 2040"),
    ("存活函数", "Weibull：LFP k=3.1/scale 5.5a；三元 k=2.1/scale 7.3a"),
    ("收集率", "三情景 c = 0.65 / 0.85 / 1.00"),
    ("退役峰值", "2029 年 ≈ 4,817 t/a"),
]
ay = 1.95
for k, v in am:
    text(s, 0.62, ay, 1.35, 0.3, [[(k, {"size": 12, "bold": True, "color": INK})]])
    text(s, 2.0, ay - 0.03, 4.15, 0.52, [[(v, {"size": 11, "color": MUTED})]], wrap=True, line_spacing=1.0)
    ay += 0.58
# 关键数据卡片
stat = [("29,791 t", "累计首装 2010—2025"),
        ("4,817 t/a", "退役峰值 2029"),
        ("239,596 kg", "LFP 在用锂存量")]
sx = 0.62
for val, lab in stat:
    rect(s, sx, ay + 0.1, 1.62, 0.8, LIGHT, rounded=True, radius=0.10)
    text(s, sx, ay + 0.16, 1.62, 0.4, [[(val, {"size": 15, "bold": True, "color": PRIMARY})]],
         align=PP_ALIGN.CENTER)
    text(s, sx, ay + 0.55, 1.62, 0.3, [[(lab, {"size": 8.5, "color": MUTED})]],
         align=PP_ALIGN.CENTER)
    sx += 1.74
# 右：图
figure(s, FIGA + r"\fig3_dmfa_retirement_collection.png", 5.85, 1.5, 6.9, 3.35)
text(s, 5.85, 4.95, 6.9, 0.35,
     [[("图 A-1 退役与收集时序（三情景收集率，收集率只改 C(t)，不改 R(t)）",
        {"size": 10, "color": MUTED, "italic": True})]])
# 结论条
rect(s, 0.62, 5.35, 12.1, 1.5, LIGHT, rounded=True, radius=0.06)
text(s, 0.9, 5.5, 11.6, 0.4, [[("口径结论", {"size": 13, "bold": True, "color": PRIMARY})]])
text(s, 0.9, 5.9, 11.6, 0.85,
     [[("收集率仅影响收集量 C(t)，不影响退役量 R(t)；该队列年供给贡献 ≈ 68,000 t/a 的 6.02%，"
        "因此【不能】据此推断“全市收集量不足以支撑园区” —— 替换电池、未来新装机与跨区域来源未建模。",
        {"size": 11.5, "color": INK})]], line_spacing=1.1)
footer(s, "A", "dMFA 覆盖既有首装队列剩余释放，不代表全市退役总量")

# ================= Slide 5 成员A R1物料流 =================
s = new_slide("A", "园区 R1 年度物料流", "整包—电芯—黑粉—产品/残渣/废水 连续清单，33 条流股")
# 左：分流数字
text(s, 0.62, 1.45, 5.3, 0.4, [[("来料分流（R1，t/a）", {"size": 15, "bold": True, "color": PRIMARY})]])
flow = [
    ("退役整包到厂", "68,000.00"),
    ("梯次保留（整包当量）", "7,420.50"),
    ("再生入口", "60,579.50"),
    ("　├ LFP 再生", "36,347.70"),
    ("　└ 未细分三元再生", "24,231.80"),
    ("黑粉（LFP 电芯×0.5）", "12,043.81"),
]
fy = 2.05
for k, v in flow:
    bar_col = PRIMARY if not k.startswith("　") else SECOND
    rect(s, 0.62, fy + 0.03, 0.05, 0.34, bar_col)
    text(s, 0.78, fy, 3.1, 0.36, [[(k, {"size": 12.5, "bold": True, "color": INK})]])
    text(s, 3.55, fy, 2.3, 0.36, [[(v, {"size": 12.5, "bold": True, "color": TEAL})]],
         align=PP_ALIGN.RIGHT)
    fy += 0.46
# 主要产品
text(s, 0.62, fy + 0.12, 5.3, 0.4, [[("主要产品/去向", {"size": 15, "bold": True, "color": PRIMARY})]])
prod = [
    ("LFP 粗碳酸锂（湿/干纯）", "1,710.95 / 1,355.08"),
    ("磷酸铁（湿/干纯）", "9,027.87 / 5,362.56"),
    ("铜箔 / 铝箔", "3,341.24 / 1,431.96"),
    ("三元元素产品", "8,021.79（Ni 1,774.13 等）"),
]
py = fy + 0.55
for k, v in prod:
    rect(s, 0.62, py + 0.03, 0.05, 0.30, ACCENT)
    text(s, 0.78, py, 3.1, 0.34, [[(k, {"size": 12, "color": INK})]], wrap=True)
    text(s, 3.55, py, 2.3, 0.34, [[(v, {"size": 12, "bold": True, "color": INK})]],
         align=PP_ALIGN.RIGHT, wrap=True)
    py += 0.52
# 右：图
figure(s, FIGS + r"\fig01_material_flow.png", 5.95, 1.5, 6.75, 3.1)
text(s, 5.95, 4.7, 6.75, 0.35,
     [[("图 A-2 整包在梯次/再生间分流，及再生产品/残渣去向",
        {"size": 10, "color": MUTED, "italic": True})]])
rect(s, 5.95, 5.2, 6.75, 1.15, LIGHT, rounded=True, radius=0.08)
text(s, 6.18, 5.34, 6.3, 0.9,
     [[("三元元素产品含 Ni 1,774.13 / Co 593.80 / Mn 553.54 / Cu 2,228.41 / Al 1,162.65 t/a；"
        "硫酸盐为商品质量，硫酸根与结晶水不计入电芯质量。", {"size": 11, "color": INK})]],
     line_spacing=1.08)
footer(s, "A", "R1 数量优先，不与旧 59,500 t/a 工况混用")

# ================= Slide 6 成员A 质量平衡 =================
s = new_slide("A", "元素平衡与数据纪律", "7 项质量平衡校核全部 PASS，Li 回收率为关键短板")
# 左：质量平衡
text(s, 0.62, 1.45, 5.6, 0.4, [[("质量平衡校核（R1）", {"size": 15, "bold": True, "color": PRIMARY})]])
mb = [
    ("整包分流", "68,000 = 68,000", "PASS"),
    ("再生=电芯+非电芯", "60,579.5 = 60,579.5", "PASS"),
    ("LFP 电芯=黑粉+箔+其他", "24,087.62 = 24,087.62", "PASS"),
    ("三元电芯=元素产品+其他", "15,378.95 = 15,378.95", "PASS"),
    ("LFP Li 输入=产品+未分配", "290.918 = 290.918", "PASS"),
    ("未分配 Li 去向", "36.371 = 36.371", "PASS"),
]
my = 1.95
for k, v, st in mb:
    text(s, 0.62, my, 2.5, 0.34, [[(k, {"size": 12, "bold": True, "color": INK})]])
    text(s, 3.15, my, 2.5, 0.34, [[(v, {"size": 11.5, "color": MUTED})]])
    text(s, 5.55, my, 0.7, 0.34, [[(st, {"size": 11.5, "bold": True, "color": PRIMARY})]],
         align=PP_ALIGN.RIGHT)
    my += 0.42
# 锂回收率短板
rect(s, 0.62, 4.7, 5.6, 1.7, LIGHT, rounded=True, radius=0.08)
text(s, 0.9, 4.85, 5.1, 0.4, [[("锂电池回收率：需改进", {"size": 13.5, "bold": True, "color": PRIMARY})]])
text(s, 0.9, 5.25, 5.1, 1.0,
     [[("LFP 锂回收率 87.50%、全链 88.88%，低于课程 90% 目标 → 基准工况 FAIL。"
        "未分配 Li 36.37 t/a 按 45%/35%/20% 定位到废水/碳渣/磷酸铁晶格（平衡约束下的显式假设）。",
        {"size": 11.5, "color": INK})]], line_spacing=1.1)
# 右：数据纪律
text(s, 6.55, 1.45, 6.1, 0.4, [[("数据纪律（接口红线）", {"size": 15, "bold": True, "color": PRIMARY})]])
disc = [
    ("商品吨 / 有效吨成对", "32%液碱 13,788.6 t = 4,412.4 t 有效 NaOH，混用偏差 3%—68%"),
    ("单位原样传递", "蒸汽只给 t（不转 MJ），天然气只给 Nm³（不折 MJ）"),
    ("互斥不取均值", "JR 与 LS 情景互斥；EV I（0.9328）与 EV II（0.8353）并列"),
    ("缺失写 UNKNOWN", "可售品/分线电耗/蒸汽能量/取水/危废量 一律 null，不填 0"),
]
dy = 1.95
for k, v in disc:
    rect(s, 6.55, dy, 6.1, 0.82, WHITE, line=LINE, rounded=True, radius=0.10)
    text(s, 6.8, dy + 0.08, 5.7, 0.32, [[(k, {"size": 12.5, "bold": True, "color": TEAL})]])
    text(s, 6.8, dy + 0.40, 5.7, 0.38, [[(v, {"size": 10.5, "color": INK})]], wrap=True, line_spacing=1.0)
    dy += 0.94
footer(s, "A", "阻断清单 14 项：M02 捕集 / M05 产品合格 / M08 电耗等，待实测解除")

# ================= Slide 7 成员B LCA模型 =================
s = new_slide("B", "LCA 模型与系统边界", "环境维度主交付：清单因子 + GWP100 + 水耗核算")
# 左：边界流程
text(s, 0.62, 1.45, 4.0, 0.4, [[("系统边界（cradle-to-gate）", {"size": 15, "bold": True, "color": TEAL})]])
steps = ["收集运输", "放电拆解", "破碎分选", "精炼再生", "污染治理"]
sy = 1.95
for i, st_ in enumerate(steps, 1):
    rect(s, 0.62, sy, 0.44, 0.44, TEAL, rounded=True, radius=0.5)
    text(s, 0.62, sy, 0.44, 0.44, [[(str(i), {"size": 14, "bold": True, "color": WHITE})]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    rect(s, 1.2, sy, 3.3, 0.44, WHITE, line=LINE, rounded=True, radius=0.16)
    text(s, 1.2, sy, 3.3, 0.44, [[(st_, {"size": 12.5, "bold": True, "color": INK})]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    sy += 0.5
# 功能单位 + 基准
text(s, 0.62, sy + 0.05, 5.6, 0.4, [[("功能单位与原生基准", {"size": 14, "bold": True, "color": TEAL})]])
text(s, 0.62, sy + 0.5, 4.0, 0.4,
     [[("功能单位：", {"size": 12.5, "bold": True, "color": INK}),
       ("1 t LCE 当量", {"size": 12.5, "bold": True, "color": TEAL})]])
base = [
    ("盐湖卤水提锂", "4,000 kg CO₂e/t", "470,000 L/t"),
    ("硬岩锂辉石提锂", "9,000 kg CO₂e/t", "170,000 L/t"),
]
by = sy + 0.95
for k, g, wtr in base:
    rect(s, 0.62, by, 4.3, 0.66, LIGHT, rounded=True, radius=0.10)
    text(s, 0.78, by + 0.1, 1.8, 0.4, [[(k, {"size": 12, "bold": True, "color": INK})]])
    text(s, 2.6, by + 0.1, 2.3, 0.28, [[(g, {"size": 11, "color": MUTED})]])
    text(s, 2.6, by + 0.38, 2.3, 0.26, [[(wtr, {"size": 11, "color": MUTED})]])
    by += 0.78
# 右：因子与自检
text(s, 5.9, 1.45, 6.8, 0.4, [[("环境因子与自检基准", {"size": 15, "bold": True, "color": TEAL})]])
text(s, 5.9, 1.9, 6.8, 0.8,
     [[("环境因子五类：电力 / 热能 / 化学试剂 / 运输 / 污染治理，逐条标注出处；"
        "区域电网水因子随碳强度档位联动（0.314→1.50、0.556→2.00、0.749→2.50 L/kWh）。",
        {"size": 12, "color": INK})]], line_spacing=1.12)
rect(s, 5.9, 2.85, 6.8, 1.7, LIGHT, rounded=True, radius=0.08)
text(s, 6.15, 3.0, 6.3, 0.4, [[("模型自检（占位活动量，绿电 80%）", {"size": 13, "bold": True, "color": TEAL})]])
text(s, 6.15, 3.42, 6.3, 1.0,
     [[("净 GWP100 = 6,709.2 kg CO₂e/t；净水耗 50.2 m³/t。"
        "试剂上游隐含负荷与高电耗使占位口径偏高 —— 正式结论待 A 工序级活动量替换后重算。",
        {"size": 11.5, "color": INK})]], line_spacing=1.12)
# 多产品分配提示
rect(s, 5.9, 4.75, 6.8, 0.95, WHITE, line=LINE, rounded=True, radius=0.10)
text(s, 6.15, 4.86, 6.3, 0.75,
     [[("多产品分配：主产品 Li₂CO₃ 承担 100% 负荷，副产 Ni/Co/Mn 盐、FePO₄、Cu/Al 箔按"
        "避免 burden（系统扩展）折减 —— 当前为占位口径，待 A 物料衡算校准。", {"size": 11, "color": INK})]],
     line_spacing=1.1)
footer(s, "B", "cradle-to-gate + 运输，不含电池使用阶段与下游正极制造")

# ================= Slide 8 成员B 多情景 =================
s = new_slide("B", "多情景仿真（3,267 工况）", "决策变量与外部情景分离，覆盖环境维度全貌")
# 左：变量
text(s, 0.62, 1.45, 5.4, 0.4, [[("变量设定（笛卡尔积）", {"size": 15, "bold": True, "color": TEAL})]])
text(s, 0.62, 1.92, 5.4, 0.34, [[("决策变量（规划可控）", {"size": 13, "bold": True, "color": INK})]])
cont = [
    ("绿电消纳比例 green_ratio", "11 档 ∈ [0,1]"),
    ("直接正极再生占比 process_mix", "11 档 ∈ [0,1]"),
]
cy = 2.3
for k, v in cont:
    rect(s, 0.62, cy, 5.4, 0.42, WHITE, line=LINE, rounded=True, radius=0.14)
    text(s, 0.82, cy, 5.0, 0.42, [[(k + "　" + v, {"size": 11.5, "color": INK})]],
         anchor=MSO_ANCHOR.MIDDLE)
    cy += 0.5
text(s, 0.62, cy + 0.05, 5.4, 0.34, [[("外部情景（与决策变量分离）", {"size": 13, "bold": True, "color": INK})]])
ext = [
    ("电网碳强度 grid_ef", "0.314 / 0.556 / 0.749"),
    ("碳酸锂价格 lithium_price", "10,000 / 22,000 / 50,000 USD/t"),
    ("工艺能效 energy_efficiency", "0.80 / 1.00 / 1.20"),
]
ey = cy + 0.45
for k, v in ext:
    rect(s, 0.62, ey, 5.4, 0.42, WHITE, line=LINE, rounded=True, radius=0.14)
    text(s, 0.82, ey, 5.0, 0.42, [[(k + "　" + v, {"size": 11.5, "color": INK})]],
         anchor=MSO_ANCHOR.MIDDLE)
    ey += 0.5
# 结果数字卡片
statb = [("3,267", "工况数（≥500 达标）"),
         ("2,538~17,283", "GWP100 kg CO₂e/t"),
         ("13,097~83,876", "水耗 L/t")]
sxx = 0.62
for val, lab in statb:
    rect(s, sxx, ey + 0.15, 1.72, 1.0, LIGHT, rounded=True, radius=0.10)
    text(s, sxx, ey + 0.22, 1.72, 0.42, [[(val, {"size": 16, "bold": True, "color": TEAL})]],
         align=PP_ALIGN.CENTER)
    text(s, sxx, ey + 0.63, 1.72, 0.4, [[(lab, {"size": 9, "color": MUTED})]],
         align=PP_ALIGN.CENTER, wrap=True)
    sxx += 1.84
# 右：水碳权衡图
figure(s, FIGB + r"\fig_b2_water_carbon_tradeoff.png", 6.2, 1.5, 6.5, 3.6)
text(s, 6.2, 5.2, 6.5, 0.35,
     [[("图 B-1 水耗—碳排放权衡，颜色编码为区域电网碳强度", {"size": 10, "color": MUTED, "italic": True})]])
rect(s, 6.2, 5.6, 6.5, 0.85, LIGHT, rounded=True, radius=0.08)
text(s, 6.4, 5.7, 6.1, 0.7,
     [[("政策判定（联调状态）：PASS 0 / FAIL 99 / UNKNOWN 3,168，说明需 A 工序级数据补入后方可判定。",
        {"size": 11, "color": INK})]], line_spacing=1.1)
footer(s, "B", "3,267 组工况覆盖环境维度，LCOR 待 C 年度 TEA 就绪后接入")

# ================= Slide 9 成员B 敏感性 =================
s = new_slide("B", "环境端敏感性与帕累托寻优", "工艺配比与绿电比例是环境端主导变量")
# 敏感性排序（文本 + 条形）
text(s, 0.62, 1.45, 6.0, 0.4, [[("GWP100 单因素敏感性摆幅", {"size": 15, "bold": True, "color": TEAL})]])
sens = [
    ("process_mix 直接再生占比", 5129.0),
    ("green_ratio 绿电比例", 4668.2),
    ("grid_ef 电网碳强度", 2011.9),
    ("energy_efficiency 能效", 1398.5),
    ("lithium_price 碳酸锂价格", 0.0),
]
maxv = 5129.0
sy = 1.98
for k, v in sens:
    text(s, 0.62, sy, 3.1, 0.32, [[(k, {"size": 11.5, "color": INK})]])
    bw = 2.6 * (v / maxv)
    rect(s, 3.75, sy + 0.02, bw, 0.26, TEAL)
    text(s, 3.85 + bw, sy, 1.5, 0.3, [[("%.0f" % v, {"size": 11, "bold": True, "color": TEAL})]])
    sy += 0.46
# 结论
rect(s, 0.62, 4.35, 5.7, 1.6, LIGHT, rounded=True, radius=0.08)
text(s, 0.9, 4.5, 5.2, 0.4, [[("主导变量结论", {"size": 13, "bold": True, "color": TEAL})]])
text(s, 0.9, 4.9, 5.2, 0.95,
     [[("工艺配比（5,129）与绿电比例（4,668）居前，与“再生精炼电力消耗占碳足迹主导”设定一致；"
        "碳酸锂价格为经济变量，对 GWP100 影响恒为 0（符合预期）。", {"size": 11.5, "color": INK})]],
     line_spacing=1.12)
# 右：敏感性图 + 帕累托
figure(s, FIGB + r"\fig_b3_sensitivity.png", 6.55, 1.5, 6.2, 2.6)
text(s, 6.55, 4.2, 6.2, 0.35,
     [[("图 B-2 GWP 敏感性（各参数水平均值极差）", {"size": 10, "color": MUTED, "italic": True})]])
text(s, 6.55, 4.6, 6.2, 0.4, [[("帕累托寻优（待 LCOR 就绪）", {"size": 14, "bold": True, "color": TEAL})]])
text(s, 6.55, 5.0, 6.2, 1.2,
     [[("以 (min GWP, min LCOR) 为双目标，在政策可行域内提取帕累托前沿，并标定拐点（Knee Point）"
        "为推荐方案 B，另标成本最优锚点 A 与环境最优锚点 C。", {"size": 11.5, "color": INK})]],
     line_spacing=1.12)
footer(s, "B", "B-1~B-4 环境类图表由脚本 300 DPI 同步渲染")

# ================= Slide 10 成员C 投资费用 =================
s = new_slide("C", "投资与年度费用", "金额为 2026 含税报价现金口径，未计税费/资金成本")
# 左：投资
text(s, 0.62, 1.45, 5.5, 0.4, [[("工程投资（万元）", {"size": 15, "bold": True, "color": GOLD})]])
inv = [
    ("预处理（仓储/放电/拆解/破碎/分选）", "7,200"),
    ("梯次重组线（1万 t/a，单独核算）", "3,600"),
    ("湿法冶金主产线", "22,400"),
    ("三废综合治理", "6,400"),
    ("公辅工程（循环水/蒸汽/配电/消防）", "4,800"),
    ("数字化平台（电池数字护照+MRV）", "1,200"),
    ("合计（再生线 42,000 + 梯次 3,600）", "45,600"),
]
iy = 1.95
for k, v in inv:
    last = k.startswith("合计")
    bg = LIGHT if last else None
    bar_col = DARK if last else GOLD
    if bg is not None:
        rect(s, 0.62, iy, 5.5, 0.44, bg, rounded=True, radius=0.14)
    else:
        rect(s, 0.62, iy + 0.02, 0.05, 0.36, bar_col)
    text(s, 0.82 if bg else 0.78, iy, 4.1, 0.4,
         [[(k, {"size": 11.5, "bold": last, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE, wrap=True)
    text(s, 4.6, iy, 1.4, 0.4, [[(v, {"size": 12, "bold": True, "color": DARK if last else INK})]],
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    iy += 0.5
# 合规改造说明
text(s, 0.62, iy + 0.05, 5.5, 0.8,
     [[("合规改造追加 2,000 万元 → 再生线资本 44,000 万元；CRF = 0.09439（7%/20年），"
        "年资本年金 4,153.29 万元/a。", {"size": 11.5, "color": MUTED})]], line_spacing=1.1)
# 右：年度费用
text(s, 6.4, 1.45, 6.3, 0.4, [[("年度费用构成（123,226.7 万元）", {"size": 15, "bold": True, "color": GOLD})]])
cost = [
    ("原料（LFP/NMC 整包采购）", "98,579.6", "80.0%"),
    ("药剂（片碱/液碱/硫酸等）", "8,662.0", "7.0%"),
    ("公用工程（电/氮/汽/气）", "2,767.2", "2.2%"),
    ("人工/研发/维修/服务/其他", "5,744.0", "4.7%"),
    ("三废治理", "1,574.2", "1.3%"),
    ("运输 / 年金 / 合规改造", "946.4 / 4,153.3 / 800", "—"),
]
cyy = 1.95
for k, v, pct in cost:
    rect(s, 6.4, cyy, 6.3, 0.44, WHITE, line=LINE, rounded=True, radius=0.14)
    text(s, 6.6, cyy, 3.3, 0.4, [[(k, {"size": 11, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 9.9, cyy, 1.5, 0.4, [[(v, {"size": 11, "bold": True, "color": DARK})]],
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 11.45, cyy, 1.0, 0.4, [[(pct, {"size": 11, "bold": True, "color": GOLD})]],
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    cyy += 0.5
# 单位成本
rect(s, 6.4, cyy + 0.1, 6.3, 0.85, LIGHT, rounded=True, radius=0.08)
text(s, 6.6, cyy + 0.2, 6.0, 0.65,
     [[("单位毛成本 = 123,226.7 / 3,172.04 = ", {"size": 12, "color": INK}),
       ("38.85 万元/t LCE", {"size": 14, "bold": True, "color": GOLD}),
       ("；净成本（扣收入）≈ 6 元/t LCE。", {"size": 12, "color": INK})]])
footer(s, "C", "原料占毛成本 80%，本项目首先是采购价风险而非加工费风险")

# ================= Slide 11 成员C LCOR =================
s = new_slide("C", "LCOR 与采购价联动", "采购价联动占比是第一位敏感变量")
# 左：关键工况
text(s, 0.62, 1.45, 5.5, 0.4, [[("关键工况 LCOR（元/t LCE）", {"size": 15, "bold": True, "color": GOLD})]])
kc = [
    ("K1 组内采购价 + 基准回收率", "-190,938", "不可持续低价"),
    ("K2 金属价值 80% 联动", "-11,311", "基准回收率"),
    ("K3 联动 + 合规改进", "6", "保本基准"),
    ("K4 K3 + 100% 绿电", "-355", "财务更优"),
    ("K8 K3 + NMC811 + 绿电", "+1,028", "环境锚点"),
]
ky = 1.95
for k, v, note in kc:
    neg = v.startswith("-")
    col = PRIMARY if neg else (GOLD if v == "6" else ACCENT)
    rect(s, 0.62, ky, 5.5, 0.5, WHITE, line=LINE, rounded=True, radius=0.12)
    text(s, 0.8, ky, 2.75, 0.5, [[(k, {"size": 11, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 3.5, ky, 1.3, 0.5, [[(v, {"size": 12.5, "bold": True, "color": col})]],
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 4.95, ky, 1.05, 0.5, [[(note, {"size": 9.5, "color": MUTED})]],
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    ky += 0.58
text(s, 0.62, ky + 0.05, 5.5, 0.8,
     [[("K1 的 -19 万元/t 不是盈利，而是采购价仅为可回收价值的 30—38%，2026 年现货不存在可持续供货基础。",
        {"size": 11, "color": MUTED})]], line_spacing=1.1)
# 右：采购价联动
text(s, 6.4, 1.45, 6.3, 0.4, [[("采购价联动敏感性", {"size": 15, "bold": True, "color": GOLD})]])
text(s, 6.4, 1.9, 6.3, 0.7,
     [[("采购联动每变动 1 个百分点，LCOR 约变动 3,885 元/t LCE —— 本项目第一敏感变量，"
        "高于锂实现率（1pp ≈ 1,290）与金属实现率（1pp ≈ 2,722）。", {"size": 11.5, "color": INK})]],
     line_spacing=1.12)
figure(s, FIGS + r"\fig06_price_impact.png", 6.4, 2.7, 6.3, 2.35)
text(s, 6.4, 5.15, 6.3, 0.35,
     [[("图 C-1 采购联动比例与保本点（80%）", {"size": 10, "color": MUTED, "italic": True})]])
rect(s, 6.4, 5.55, 6.3, 0.85, LIGHT, rounded=True, radius=0.08)
text(s, 6.6, 5.65, 6.0, 0.65,
     [[("建议采购合同设“金属价值 80% 联动 + 锂价上下限”，而非固定吨价。",
        {"size": 11.5, "bold": True, "color": DARK})]], wrap=True)
footer(s, "C", "合规改造（研发 3% + Li/Cu/Al 改造）基本吃掉全部净收益，需产品溢价覆盖")

# ================= Slide 12 成员C MAC =================
s = new_slide("C", "环境减排贡献与 MAC", "联产品系统扩展抵扣是负 MAC 的关键前提")
# 左：GWP 瀑布
text(s, 0.62, 1.45, 5.6, 0.4, [[("净 GWP 与联产品抵扣", {"size": 14.5, "bold": True, "color": GOLD})]])
env = [
    ("毛排放（合规工况）", "23,468 t CO₂e/a", "7.4 t/t LCE"),
    ("联产品抵扣", "−135,682 t CO₂e/a", "铝/LCE/铜/镍/FePO₄"),
    ("净排放", "−112,214 t CO₂e/a", "−35,376 kg/t LCE"),
]
ey = 1.9
for k, v, note in env:
    neg = v.startswith("−") or v.startswith("-")
    col = PRIMARY if neg else INK
    rect(s, 0.62, ey, 5.6, 0.52, WHITE, line=LINE, rounded=True, radius=0.12)
    text(s, 0.8, ey, 2.1, 0.5, [[(k, {"size": 11.5, "bold": True, "color": INK})]],
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, 2.95, ey, 2.1, 0.5, [[(v, {"size": 11.5, "bold": True, "color": col})]],
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, 5.15, ey, 0.95, 0.5, [[(note, {"size": 9, "color": MUTED})]],
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    ey += 0.6
# MAC 结果卡片
macs = [("-2,997", "MAC·锂辉石基准"),
        ("-2,890", "MAC·100%绿电"),
        ("-37,149", "净GWP·绿电 kg/t")]
mx = 0.62
for val, lab in macs:
    rect(s, mx, ey + 0.12, 1.78, 1.05, LIGHT, rounded=True, radius=0.10)
    text(s, mx, ey + 0.22, 1.78, 0.42, [[(val, {"size": 17, "bold": True, "color": TEAL})]],
         align=PP_ALIGN.CENTER)
    text(s, mx, ey + 0.66, 1.78, 0.35, [[(lab, {"size": 9.5, "color": MUTED})]],
         align=PP_ALIGN.CENTER)
    mx += 1.9
text(s, 0.62, ey + 1.4, 5.6, 0.8,
     [[("负 MAC = 回收路线在系统扩展口径下同时降本减碳，即“负成本减排机会”。",
        {"size": 11.5, "bold": True, "color": DARK})]])
# 右：瀑布图
figure(s, FIGS + r"\fig04_gwp_waterfall.png", 6.45, 1.5, 6.3, 3.4)
text(s, 6.45, 5.0, 6.3, 0.4,
     [[("图 C-2 过程排放与联产品抵扣（100% 绿电，净 −117,839 t CO₂e/a）",
        {"size": 10, "color": MUTED, "italic": True})]])
rect(s, 6.45, 5.45, 6.3, 0.95, LIGHT, rounded=True, radius=0.08)
text(s, 6.65, 5.56, 5.95, 0.75,
     [[("若不允许联产品抵扣，回收毛 GWP 仅略低于原生 9,000 kg/t，MAC 失去经济意义；"
        "故表述为“含联产品抵扣的系统扩展 MAC”，不与单产品碳足迹混用。", {"size": 10.5, "color": INK})]],
     line_spacing=1.08)
footer(s, "C", "MAC 对抵扣因子与产品实现率敏感，不作独立投资决策依据")

# ================= Slide 13 成员C 政策与推荐 =================
s = new_slide("C", "政策引擎判定与推荐方案", "基准 4 项 FAIL → 合规改进全项 PASS")
# 左：政策
text(s, 0.62, 1.45, 5.7, 0.4, [[("政策引擎逐项判定", {"size": 15, "bold": True, "color": GOLD})]])
pol = [
    ("锂冶炼回收率", "88.88% → 92%", "FAIL→PASS"),
    ("铜回收率 / 铝回收率", "90% → 98%", "FAIL→PASS"),
    ("研发费用占收入", "0.336% → 3%", "FAIL→PASS"),
    ("镍/钴/锰回收率", "98%（ANL 默认）", "PASS"),
    ("单位综合能耗", "2,054 kgce/t", "PASS*"),
]
py = 1.95
for k, v, st in pol:
    fail = st.startswith("FAIL")
    col = ACCENT if fail else PRIMARY
    rect(s, 0.62, py, 5.7, 0.5, WHITE, line=LINE, rounded=True, radius=0.12)
    text(s, 0.8, py, 2.3, 0.5, [[(k, {"size": 11, "bold": True, "color": INK})]],
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, 3.1, py, 2.4, 0.5, [[(v, {"size": 10.5, "color": MUTED})]],
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, 5.55, py, 0.7, 0.5, [[(st, {"size": 10.5, "bold": True, "color": col})]],
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    py += 0.58
text(s, 0.62, py + 0.05, 5.7, 0.8,
     [[("*R1 三元电耗为 ANL 代理值（34.7 kWh/t），保守口径 561 kWh/t 下能耗约 2,298 kgce/t、"
        "转为 FAIL —— 列为 2030 前工程验证条件。", {"size": 10, "color": MUTED})]], line_spacing=1.08)
# 右：前沿 + 图
text(s, 6.55, 1.45, 6.1, 0.4, [[("多目标前沿（960 组中 220 可行）", {"size": 14.5, "bold": True, "color": GOLD})]])
front = [
    ("成本锚点", "NMC622 + 100%绿电", "LCOR −355 · GWP −37,149"),
    ("环境锚点/膝点", "NMC811 + 100%绿电", "LCOR +1,028 · GWP −38,824"),
]
fy = 1.95
for tag, k, v in front:
    rect(s, 6.55, fy, 6.1, 0.66, WHITE, line=LINE, rounded=True, radius=0.10)
    text(s, 6.75, fy + 0.06, 1.5, 0.5, [[(tag, {"size": 11, "bold": True, "color": TEAL})]])
    text(s, 7.95, fy + 0.06, 4.6, 0.3, [[(k, {"size": 12, "bold": True, "color": INK})]])
    text(s, 7.95, fy + 0.36, 4.6, 0.26, [[(v, {"size": 10.5, "color": MUTED})]])
    fy += 0.76
figure(s, FIGS + r"\fig07_pareto.png", 6.55, fy + 0.1, 6.1, 2.2)
text(s, 6.55, fy + 2.35, 6.1, 0.35,
     [[("图 C-3 名义工况 GWP—LCOR 前沿，星号为膝点 811", {"size": 10, "color": MUTED, "italic": True})]])
footer(s, "C", "政策判定仅覆盖已编码定量项，缺失保持 UNKNOWN，不构成法律合规认证")

# ================= Slide 14 综合结论 =================
s = new_slide("ALL", "综合结论与推荐方案", "一句话方案 + 三阶段路线图 + 五个硬条件")
# 一句话方案
rect(s, 0.62, 1.45, 12.1, 1.35, DARK, rounded=True, radius=0.06)
text(s, 0.95, 1.62, 11.4, 0.4, [[("推荐方案（一句话）", {"size": 14, "bold": True, "color": ACCENT})]])
text(s, 0.95, 2.05, 11.4, 0.7,
     [[("在 80% 金属价值联动采购、Li≥92% / Cu-Al≥98% 回收、研发 3%、100% 绿电条件下，"
        "以 NMC622 为主力、NMC811 为环境备选 —— LCOR 约 −355 ~ +1,028 元/t LCE，基本保本，"
        "净减排 37—39 t CO₂e/t，MAC 约 −2,760 ~ −2,890 元/t CO₂e。",
        {"size": 12.5, "color": WHITE})]], line_spacing=1.15)
# 三阶段
text(s, 0.62, 3.0, 6.0, 0.4, [[("三阶段路线图", {"size": 15, "bold": True, "color": PRIMARY})]])
stages = [
    ("2026 基准", "来料计量/批次溯源/元素平衡；研发补足 3%；绿电 ≥50%"),
    ("2030 近期", "Li≥92%、Cu/Al≥98%、能耗≤2,100、绿电≥80%；政策全项 PASS"),
    ("2035 远期", "Li≥95%、Cu/Al≥99%、净GWP≤−40、LCOR≤−5,000；数字护照+MRV 全覆盖"),
]
sty = 3.45
for t, d in stages:
    rect(s, 0.62, sty, 1.5, 0.5, PRIMARY, rounded=True, radius=0.18)
    text(s, 0.62, sty, 1.5, 0.5, [[(t, {"size": 12.5, "bold": True, "color": WHITE})]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 2.3, sty + 0.02, 10.0, 0.5, [[(d, {"size": 11.5, "color": INK})]],
         anchor=MSO_ANCHOR.MIDDLE, wrap=True)
    sty += 0.62
# 五个硬条件
text(s, 0.62, 5.4, 12.1, 0.4, [[("推荐方案的五个硬条件", {"size": 15, "bold": True, "color": PRIMARY})]])
conds = ["采购价 ≤ 金属价值 80%", "Li ≥ 92%", "Cu / Al ≥ 98%",
         "研发 ≥ 收入 3%", "绿电 ≥ 80%（目标 100%）"]
csx = 0.62
for c in conds:
    w = 2.28
    rect(s, csx, 5.86, w, 0.72, LIGHT, rounded=True, radius=0.12)
    text(s, csx, 5.86, w, 0.72, [[(c, {"size": 12, "bold": True, "color": PRIMARY})]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    csx += w + 0.18
footer(s, "ALL", "任一硬条件不成立，应回到敏感性表重算，而非沿用结论")

# ================= Slide 15 局限与致谢 =================
s = new_slide("ALL", "局限、边界与致谢", "条件性规划结论，须人工复核后签认")
# 局限
text(s, 0.62, 1.45, 5.9, 0.4, [[("主要局限与未闭合项", {"size": 15, "bold": True, "color": PRIMARY})]])
lims = [
    "价格均为规划参考价，未取得成交原件",
    "产品未取得电池级合格证，LCE-eq 非合格品产量",
    "实际捕集率、完整水平衡、逐工段元素分配未闭合",
    "税费、资金成本、营运资金、建设期利息未计",
    "能耗为 ANL 代理值（34.7 kWh/t），需分线计量复核",
    "政策判定不构成法律合规认证 / 环评 / 排污许可",
]
ly = 1.95
for l in lims:
    rect(s, 0.62, ly + 0.03, 0.14, 0.34, ACCENT)
    text(s, 0.9, ly, 6.2, 0.36, [[(l, {"size": 12, "color": INK})]], wrap=True)
    ly += 0.5
# 数据属性说明
rect(s, 0.62, 5.15, 5.9, 1.3, LIGHT, rounded=True, radius=0.08)
text(s, 0.9, 5.3, 5.4, 0.4, [[("数据属性与贡献声明", {"size": 13, "bold": True, "color": PRIMARY})]])
text(s, 0.9, 5.7, 5.4, 0.7,
     [[("引用数字须同时引用数据属性（组内设定/文献原值/文献迁移/情景假设）与边界（R1_2026_gate，1 t LCE-eq）；"
        "AI 辅助生成代码与文字，由成员逐项复核签认。", {"size": 11, "color": INK})]], line_spacing=1.1)
# 致谢
rect(s, 6.85, 1.45, 5.85, 4.9, DARK, rounded=True, radius=0.06)
text(s, 7.2, 3.0, 5.2, 1.0,
     [[("谢谢 · Q & A", {"size": 40, "bold": True, "color": WHITE, "font": SERIF_FONT})]])
text(s, 7.2, 4.15, 5.2, 0.4,
     [[("成员 A · 成员 B · 成员 C　联合汇报", {"size": 14, "bold": True, "color": ACCENT})]])
text(s, 7.2, 4.6, 5.2, 0.9,
     [[("退役动力电池回收园区规划 · 物质流 × 环境 × 经济",
        {"size": 12, "color": RGBColor(0xC9, 0xDB, 0xD0)})]], line_spacing=1.2)
text(s, 7.2, 5.6, 5.2, 0.6,
     [[("2026-11-04 · 小组 02", {"size": 12, "color": RGBColor(0x9E, 0xB7, 0xA7)})]])
footer(s, "ALL", "规划仿真结论，非企业实测、非投资建议")

prs.save(OUT_PPTX)
print("SAVED:", OUT_PPTX)
print("slides:", len(prs.slides.__iter__.__self__._sldIdLst))