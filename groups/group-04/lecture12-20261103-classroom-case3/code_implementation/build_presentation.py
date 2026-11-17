# -*- coding: utf-8 -*-
"""build_presentation.py —— 成员 A 汇报 PPT（8 页 / 约 5 分钟）
设计基调：工程规划报告风 · 深青主色 + 铜色强调 + 暖白底
版式：16:9，页边距 0.55"，标题宋体，正文雅黑
"""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "..", "figures_output")
OUT = os.path.join(BASE, "..", "A_MFA汇报.pptx")

# ============ 设计令牌 ============
INK    = RGBColor(0x12, 0x23, 0x2B)
TEAL   = RGBColor(0x0F, 0x5C, 0x6E)
TEAL_L = RGBColor(0x1B, 0x84, 0xA0)
COPPER = RGBColor(0xC0, 0x6B, 0x3E)
GREEN  = RGBColor(0x42, 0x79, 0x5C)
GRAY   = RGBColor(0x7D, 0x8A, 0x93)
MUTED  = RGBColor(0x5E, 0x6E, 0x77)
BG     = RGBColor(0xF7, 0xF5, 0xF0)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
DARK   = RGBColor(0x0B, 0x3F, 0x4C)

SERIF = "SimSun"         # 中文标题（宋体）
SANS  = "Microsoft YaHei"  # 正文（雅黑）
SERIF_EN = "Georgia"     # 拉丁数字/字母（避免宋体全角逗号造成 "20, 000"）

SLIDE_W, SLIDE_H = 10.0, 5.625
M = 0.55
CW = SLIDE_W - 2 * M

prs = Presentation()
prs.slide_width = Inches(SLIDE_W)
prs.slide_height = Inches(SLIDE_H)
BLANK = prs.slide_layouts[6]


# ============ 基础工具 ============
def _set_ea(run, zh_font):
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", zh_font)


def text(slide, s, x, y, w, h, size=14, bold=False, color=INK,
         font_zh=SANS, font_en=None, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, line=1.2, space_after=0, wrap=True):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = pt(0); tf.margin_right = pt(0)
    tf.margin_top = pt(0); tf.margin_bottom = pt(0)
    tf.vertical_anchor = anchor
    lines = s.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font_en or font_zh
        _set_ea(r, font_zh)
    return tb


def pt(v):
    return Pt(v)


def bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = color


def rect(slide, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE, line=None, lw=1.0):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(lw)
    shp.shadow.inherit = False
    return shp


def card(slide, x, y, w, h, fill=WHITE, line=None, lw=1.0):
    return rect(slide, x, y, w, h, fill, MSO_SHAPE.ROUNDED_RECTANGLE, line, lw)


def header(slide, title, subtitle=None, page=None):
    """标题区：铜色小方块 + 标题 + 可选副标题 + 页码"""
    rect(slide, M, 0.60, 0.13, 0.13, COPPER)
    text(slide, title, M + 0.26, 0.44, CW - 1.2, 0.52, size=25, bold=True,
         color=INK, font_zh=SERIF, font_en=SERIF_EN, anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        text(slide, subtitle, M + 0.26, 1.02, CW - 1.0, 0.36, size=11.5, color=MUTED)
    if page:
        text(slide, page, SLIDE_W - M - 0.9, 0.46, 0.9, 0.3, size=9.5,
             color=GRAY, align=PP_ALIGN.RIGHT)


def footnote(slide, s):
    text(slide, s, M, SLIDE_H - 0.40, CW, 0.26, size=8.5, color=GRAY, line=1.15)


def stat(slide, x, y, w, number, label, note=None, color=TEAL):
    text(slide, number, x, y, w, 0.72, size=30, bold=True, color=color,
         font_zh=SERIF, font_en=SERIF_EN, line=1.0)
    text(slide, label, x, y + 0.70, w, 0.34, size=11, color=INK, line=1.15)
    if note:
        text(slide, note, x, y + 1.04, w, 0.30, size=8.5, color=GRAY, line=1.1)


def image(slide, path, x, y, w):
    """等比缩放放置（给定宽度，自动算高度）"""
    iw, ih = Image.open(path).size
    h = w * ih / iw
    slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
    return h


def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s


# ================================================================
# 1 封面
# ================================================================
s = prs.slides.add_slide(BLANK)
bg(s, DARK)
rect(s, 0, 0, 0.10, SLIDE_H, COPPER)

text(s, "环境规划与管理 · 第十二讲 · 课堂案例三", 0.75, 0.85, 5.6, 0.32,
     size=11, color=RGBColor(0x8F, 0xB8, 0xC2))
text(s, "退役动力电池锂资源\n回收环境规划", 0.75, 1.35, 5.4, 1.35,
     size=33, bold=True, color=WHITE, font_zh=SERIF, font_en=SERIF_EN, line=1.22)
text(s, "浙江衢州华友循环资源再生产业园 · 多工序物质流核算", 0.75, 2.92, 5.5, 0.4,
     size=14, color=RGBColor(0xD7, 0xE6, 0xEA))
rect(s, 0.75, 3.52, 1.1, 0.035, COPPER)
text(s, "第四小组　·　方向 B（产业园区尺度）　·　成员 A", 0.75, 3.75, 5.5, 0.34,
     size=11.5, color=RGBColor(0xBF, 0xD4, 0xDA))
text(s, "数据与物质流　|　对应报告第 1、2 章", 0.75, 4.18, 5.5, 0.30,
     size=10, color=RGBColor(0x8F, 0xB8, 0xC2))

# 右侧三个关键数字
px, pw = 6.75, 2.6
stats = [("20,000", "t/a　设计处理能力"),
         ("92%", "冶炼段锂回收率"),
         ("0.000%", "十元素质量守恒误差")]
for i, (n, l) in enumerate(stats):
    yy = 1.55 + i * 1.16
    text(s, n, px, yy, pw, 0.62, size=26, bold=True, color=WHITE,
         font_zh=SERIF, font_en=SERIF_EN, line=1.0)
    text(s, l, px, yy + 0.60, pw, 0.28, size=10, color=RGBColor(0x9C, 0xC2, 0xCB))
    if i < 2:
        rect(s, px, yy + 1.00, 0.95, 0.018, RGBColor(0x2E, 0x6B, 0x78))

notes(s, "各位同学好，我汇报第四小组方向 B 中成员 A 的部分——数据与物质流。"
         "场景是浙江衢州华友循环资源再生产业园，核心工作是把退役电池的物质流通量算清楚，并做元素级守恒核验。")

# ================================================================
# 2 汇报框架
# ================================================================
s = prs.slides.add_slide(BLANK)
bg(s, BG)
header(s, "汇报框架", "四个部分 · 总时长约 5 分钟", "02 / 08")

items = [
    ("01", "场景", "为什么选衢州华友：真实园区、真实瓶颈", "60 秒"),
    ("02", "方法", "系统边界、功能单位与数据底座", "60 秒"),
    ("03", "结果", "物质流通量、守恒核验与合规判定", "150 秒"),
    ("04", "交接", "结论与移交下游的接口", "60 秒"),
]
cw = (CW - 0.30 * 3) / 4
for i, (no, t, d, dur) in enumerate(items):
    x = M + i * (cw + 0.30)
    card(s, x, 1.70, cw, 2.30, WHITE, RGBColor(0xDD, 0xDA, 0xD2), 1.0)
    rect(s, x, 1.70, cw, 0.06, TEAL if i != 2 else COPPER)
    text(s, no, x + 0.22, 1.92, 1.0, 0.36, size=12, bold=True, color=COPPER)
    text(s, t, x + 0.22, 2.30, cw - 0.44, 0.40, size=17, bold=True,
         color=INK, font_zh=SERIF, font_en=SERIF_EN)
    text(s, d, x + 0.22, 2.78, cw - 0.40, 0.86, size=10, color=MUTED, line=1.35)
    text(s, dur, x + 0.22, 3.62, cw - 0.44, 0.26, size=9, color=GRAY)

text(s, "重点在第 3 部分：物质流图与合规判定，是本次汇报的核心证据。",
     M, 4.42, CW, 0.30, size=10.5, color=MUTED)
footnote(s, "汇报人：成员 A　|　全部数据与代码可在本目录复现")

notes(s, "汇报分四块：场景、方法、结果、交接。重点放在第三块，大约占两分半钟，因为物质流图和合规判定是核心证据。")

# ================================================================
# 3 场景
# ================================================================
s = prs.slides.add_slide(BLANK)
bg(s, BG)
header(s, "为什么是衢州华友：三个关键数字", "产业基础真实、瓶颈典型、工艺正在演进", "03 / 08")

nums = [
    ("6.47 万 t/a", "华友循环衢州基地处理能力", "2018 年投产，全球首家梯次 + 再生“零碳”工厂", TEAL),
    ("22%", "园区产能利用率", "设计 2 万 t/a，2024 年实际利用仅 0.44 万 t", COPPER),
    ("1.2 万 t/a", "在建 LFP 直接再生料产能", "华友绿能项目，直接再生路线具备工程化条件", GREEN),
]
cw3 = (CW - 0.28 * 2) / 3
for i, (n, l, note, c) in enumerate(nums):
    x = M + i * (cw3 + 0.28)
    rect(s, x, 1.80, 0.045, 1.72, c)
    text(s, n, x + 0.24, 1.78, cw3 - 0.30, 0.62, size=25, bold=True, color=c,
         font_zh=SERIF, font_en=SERIF_EN, line=1.0)
    text(s, l, x + 0.24, 2.46, cw3 - 0.30, 0.30, size=10.5, color=INK)
    text(s, note, x + 0.24, 2.82, cw3 - 0.28, 0.62, size=9, color=MUTED, line=1.4)

card(s, M, 3.92, CW, 0.62, RGBColor(0xEA, 0xEE, 0xE9))
text(s, "因此本规划把设计规模锚定在 20,000 t/a，进料结构设为 LFP∶NMC = 6∶4",
     M + 0.28, 4.06, CW - 0.5, 0.34, size=12, bold=True, color=TEAL)
footnote(s, "来源：衢州市生态环境局 2025 年固体废物信息公告；华友钴业官网 / 36 氪报道；衢州智造新城节能报告公示")

notes(s, "选这个园区有三个理由。第一，产业基础真实：华友循环 2018 年就在衢州投产，年处理 6.47 万吨，是全球首家梯次加再生的零碳工厂。"
         "第二，瓶颈典型：园区设计能力 2 万吨，2024 年实际只用了 0.44 万吨，利用率 22%，正规渠道收不到电池是真问题。"
         "第三，工艺在演进：1.2 万吨磷酸铁锂再生料项目在建，说明直接再生路线能落地。所以设计规模锚定 2 万吨，进料按磷酸铁锂比三元 6 比 4。")

# ================================================================
# 4 边界与数据底座
# ================================================================
s = prs.slides.add_slide(BLANK)
bg(s, BG)
header(s, "系统边界与数据底座", "边界先定死，功能单位先统一，避免组内返工", "04 / 08")

# 左：边界卡
card(s, M, 1.72, 4.55, 2.60, WHITE, RGBColor(0xDD, 0xDA, 0xD2))
rect(s, M, 1.72, 0.06, 2.60, TEAL)
text(s, "系统边界", M + 0.28, 1.92, 3.9, 0.28, size=11, bold=True, color=TEAL)
b_lines = [
    ("空间", "Gate-to-Gate（园区大门到大门）"),
    ("功能单位", "1 t 电池级 Li₂CO₃ 当量"),
    ("上游", "收集运输 300 km（长三角）"),
    ("规划年", "2026 · 2030 · 2035"),
]
for i, (k, v) in enumerate(b_lines):
    yy = 2.30 + i * 0.50
    text(s, k, M + 0.28, yy, 0.95, 0.26, size=9.5, color=GRAY)
    text(s, v, M + 1.24, yy - 0.02, 3.2, 0.30, size=10.5, color=INK)

# 右：数据来源
text(s, "数据来源：13 项，全部标注出处", 5.55, 1.92, 4.0, 0.28, size=11, bold=True, color=TEAL)
src = [("6", "篇 参考文献", "Nature 系列为主，含工业级实测数据"),
       ("3", "项 法规标准", "工信部 2024 年本 · 欧盟 2023/1542 · GB/T 系列"),
       ("4", "项 园区公开资料", "政府公告、环评与节能报告公示")]
for i, (n, t, d) in enumerate(src):
    yy = 2.32 + i * 0.68
    text(s, n, 5.55, yy, 0.60, 0.44, size=17, bold=True, color=COPPER,
         font_zh=SERIF, font_en=SERIF_EN, line=1.0)
    text(s, t, 6.18, yy + 0.02, 2.2, 0.26, size=10.5, bold=True, color=INK)
    text(s, d, 6.18, yy + 0.30, 3.4, 0.26, size=9, color=MUTED)

card(s, M, 4.52, CW, 0.58, RGBColor(0xF0, 0xE4, 0xDA))
text(s, "关键参数全部可溯源：锂回收率、能耗、水耗取自 Redwood Materials 工业级实测（Machala et al. 2025）",
     M + 0.26, 4.64, CW - 0.5, 0.32, size=10, color=COPPER)
footnote(s, "参数逐条登记于 data_cohort/数据手册_完整版.md，含文献页码与表号")

notes(s, "方法上两件事先定死。一是边界：从园区大门到大门，上游含 300 公里收集运输，功能单位统一为 1 吨电池级碳酸锂当量，这个必须和做 LCA 的同学提前对齐，否则组内一定返工。"
         "二是数据：13 项来源全部标注出处，其中最关键的是 Machala 2025 那篇，它是唯一给出工业级工序能耗、水耗和回收率的文献。")

# ================================================================
# 5 物质流
# ================================================================
s = prs.slides.add_slide(BLANK)
bg(s, BG)
header(s, "物质流通量：20,000 吨去哪了", "五道工序逐级分流，十种元素全程追踪", "05 / 08")

img_path = os.path.join(FIG, "fig_process_flow_clean.png")
iw, ih = Image.open(img_path).size
w = 8.55
h = w * ih / iw
if 1.62 + h > SLIDE_H - 0.18:
    h = SLIDE_H - 0.18 - 1.62
    w = h * iw / ih
image(s, img_path, (SLIDE_W - w) / 2, 1.62, w)

notes(s, "这张图是核心。两万吨进厂，先按健康状态分流，20% 也就是 4000 吨直接梯次利用，剩下 80% 进拆解。"
         "拆解后电芯 10,296 吨进入破碎分选，得到黑粉 5,983 吨，同时分出 5,488 吨结构件和 4,004 吨铜铝隔膜。"
         "黑粉再进再生提取段，产出碳酸锂 702 吨、混合镍钴锰盐 3,242 吨、再生磷酸铁锂正极 839 吨、磷酸铁 738 吨，尾渣废水约 1000 吨。"
         "注意混合盐是按含水合物计的，所以质量里含结晶水。")

# ================================================================
# 6 合规判定
# ================================================================
s = prs.slides.add_slide(BLANK)
bg(s, BG)
header(s, "合规判定：一项达标、三项缺口", "对标《新能源汽车废旧动力电池综合利用行业规范条件（2024 年本）》", "06 / 08")

img_path = os.path.join(FIG, "fig_compliance.png")
iw, ih = Image.open(img_path).size
w = 5.45
h = w * ih / iw
image(s, img_path, M, 1.72, w)

# 右侧结论
rx = 6.35
rw = SLIDE_W - M - rx
findings = [
    ("达标", "锂 Li 92%", "≥ 90% 红线，压线通过", GREEN),
    ("缺口", "镍 Ni / 钴 Co 95%", "距 98% 红线差 3 个百分点", COPPER),
    ("缺口", "锰 Mn 90%", "距 98% 红线差 8 个百分点", COPPER),
    ("风险", "氟 117 t/a", "进入废水废气，固化率 ≥99.5% 压力大", RGBColor(0x8C, 0x3A, 0x2F)),
]
for i, (tag, t, d, c) in enumerate(findings):
    yy = 1.78 + i * 0.86
    rect(s, rx, yy, 0.05, 0.66, c)
    text(s, tag, rx + 0.18, yy + 0.00, 0.6, 0.24, size=8.5, bold=True, color=c)
    text(s, t, rx + 0.18, yy + 0.22, rw - 0.20, 0.26, size=11, bold=True, color=INK)
    text(s, d, rx + 0.18, yy + 0.48, rw - 0.18, 0.26, size=8.5, color=MUTED)

footnote(s, "回收率为冶炼段口径；镍钴锰 98% 为工信部约束性指标，缺口即工艺强化方向")

notes(s, "合规判定是规划落地的关键。四根柱子对着两条红线：锂 92%，高于 90% 的锂红线，压线达标；"
         "但镍钴锰 95%、95%、90%，都低于 98% 红线，分别差 3 到 8 个百分点，这是我们需要向工艺强化提要求的依据。"
         "另外氟是个隐性风险：153.6 吨氟输入里有 117 吨进到废水废气系统，氟固化率 99.5% 的红线会直接决定环保设施规模。")

# ================================================================
# 7 结论与交接
# ================================================================
s = prs.slides.add_slide(BLANK)
bg(s, BG)
header(s, "结论与数据交接", "三条结论 · 两个接口", "07 / 08")

concl = [
    ("通量自洽", "20,000 t 进料 → 4,000 梯次 + 5,983 黑粉进再生；十元素守恒误差 0.000%"),
    ("合规短板", "锂 92% 达标；镍钴锰 95 / 95 / 90%，差 3–8 点，列入工艺强化清单"),
    ("环境压力", "氟 117 t/a 进入废水废气，固化率 99.5% 决定环保设施规模"),
]
for i, (t, d) in enumerate(concl):
    yy = 1.76 + i * 0.94
    text(s, f"0{i+1}", M, yy, 0.42, 0.30, size=11, bold=True, color=COPPER)
    text(s, t, M + 0.44, yy, 1.30, 0.28, size=12, bold=True, color=INK, font_zh=SERIF, font_en=SERIF_EN)
    text(s, d, M + 1.80, yy - 0.02, 3.55, 0.72, size=9.5, color=MUTED, line=1.35)

# 接口
ix = 6.22
iw_ = SLIDE_W - M - ix
text(s, "移交下游", ix, 1.76, iw_, 0.26, size=10, bold=True, color=TEAL)
ifaces = [
    ("flows_summary.csv", "成员 C · LCA / TEA", "各工序处理量、能耗、水耗、碳排放", TEAL),
    ("recovery_rates.json", "成员 B · 政策引擎", "冶炼段锂 92%、黑粉 98%、材料修复 99%", GREEN),
]
for i, (f, who, d, c) in enumerate(ifaces):
    yy = 2.12 + i * 1.28
    card(s, ix, yy, iw_, 1.10, WHITE, c, 1.2)
    text(s, f, ix + 0.20, yy + 0.16, iw_ - 0.36, 0.26, size=10.5, bold=True, color=c, font_en="Consolas")
    text(s, who, ix + 0.20, yy + 0.44, iw_ - 0.36, 0.24, size=9.5, color=INK)
    text(s, d, ix + 0.20, yy + 0.70, iw_ - 0.34, 0.30, size=8.5, color=MUTED)

card(s, M, 4.62, CW, 0.56, RGBColor(0xEA, 0xEE, 0xE9))
text(s, "全报告一致性锚点：第 4 章重点工程产能、第 5 章 TEA 现金流均以 20,000 t/a 与 60∶40 进料结构为准",
     M + 0.26, 4.74, CW - 0.5, 0.30, size=10, color=TEAL)

notes(s, "最后三条结论。第一，通量是自洽的，两万吨进料，四千吨梯次，五千九百八十三吨黑粉进再生，十种元素守恒误差为零，远好于任务书千分之零点五的要求。"
         "第二，合规上锂达标但镍钴锰有缺口，这是后续工艺强化的靶点。第三，氟的去向是环保设施规模的决定因素。"
         "我把结果拆成两个文件交给下游：流量表交给做 LCA-TEA 的同学，回收率参数交给做政策引擎的同学。我的部分到这里。")

# ================================================================
# 8 致谢
# ================================================================
s = prs.slides.add_slide(BLANK)
bg(s, DARK)
rect(s, 0, 0, 0.10, SLIDE_H, COPPER)
text(s, "谢谢　·　欢迎提问", 0.85, 1.72, 6.0, 0.72, size=31, bold=True,
     color=WHITE, font_zh=SERIF, font_en=SERIF_EN)
rect(s, 0.85, 2.62, 1.1, 0.035, COPPER)
text(s, "第四小组　·　方向 B（产业园区尺度）　·　成员 A", 0.85, 2.92, 6.2, 0.32,
     size=13, color=RGBColor(0xD7, 0xE6, 0xEA))
text(s, "数据、脚本与图表均可在本目录复现：data_cohort / code_implementation / figures_output",
     0.85, 3.36, 7.6, 0.30, size=10, color=RGBColor(0x8F, 0xB8, 0xC2))
text(s, "20,000 t/a", 7.55, 4.10, 1.95, 0.40, size=16, bold=True, color=WHITE,
     font_zh=SERIF, font_en=SERIF_EN, align=PP_ALIGN.RIGHT)
text(s, "设计处理能力", 7.55, 4.48, 1.95, 0.26, size=9, color=RGBColor(0x8F, 0xB8, 0xC2),
     align=PP_ALIGN.RIGHT)

notes(s, "我的部分汇报完毕，欢迎提问。")

prs.save(OUT)
print("PPT saved:", OUT, "| slides:", len(prs.slides))
