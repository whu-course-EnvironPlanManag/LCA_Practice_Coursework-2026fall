# -*- coding: utf-8 -*-
"""
任务 2：绘制"PET 瓶回收机械物理再生工艺与物质流控制边界"流程图（BFD）
------------------------------------------------------------------
纯 matplotlib 实现，无额外系统依赖；输出 300 dpi PNG 与矢量 SVG。
数据来源：case1_documentation.md 第一、二部分（1000 kg 瓶砖控制体）

运行：python plot_mfa_process.py
输出：process_flow_diagram.png、process_flow_diagram.svg
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False

OUT_DIR = Path(__file__).resolve().parent

# 配色
C_IN = "#fff2cc"       # 原料输入
C_PROC = "#dbe9f6"     # 单元操作
C_PROD = "#cfe8d5"     # 主产品
C_COPROD = "#e6dcf0"   # 副产品
C_WASTE = "#f6e0cc"    # 废弃物

fig, ax = plt.subplots(figsize=(13.5, 10.5))
ax.set_xlim(0, 12)
ax.set_ylim(0, 15.5)
ax.axis("off")


def box(x, y, w, h, text, color, fs=9.5, bold=False):
    """以 (x, y) 为中心绘制圆角方框并添加文字"""
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        facecolor=color, edgecolor="#333333", linewidth=1.2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.4)


def arrow(p1, p2, color="#333333", lw=1.6, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle=style, mutation_scale=14,
        color=color, linewidth=lw, linestyle=ls,
        shrinkA=0, shrinkB=0))


# ---------------- 主干工艺链（自下而上阅读，符合物料流方向）----------------
X = 4.3          # 主干中心线
W, H = 4.6, 0.95
main = [
    (14.30, "原料输入：废弃打包 PET 瓶砖 1000 kg\n（含瓶盖、标签及泥沙杂质）", C_IN, True),
    (12.50, "① 拆包、筛选与干式脱标机", C_PROC, False),
    (10.70, "② 湿式粉碎与热碱洗单元\n85 ℃，1.5% NaOH", C_PROC, False),
    (8.90, "③ 密度浮选分离槽\n水介质 ρ = 1.0 g/cm³", C_PROC, False),
    (7.10, "④ 光学色选、脱水与干燥系统", C_PROC, False),
    (5.30, "⑤ 真空挤出造粒与固相增粘 SSP\n270 ℃ 熔融，210 ℃ 增粘", C_PROC, False),
    (3.50, "主产品：瓶级 rPET 颗粒 800 kg\n（产品总收率 80.0%）", C_PROD, True),
]
for y, txt, color, bold in main:
    box(X, y, W, H, txt, color, bold=bold)

# 主干物流箭头及其质量标注
flows = [(13.82, 12.98, "1000 kg"), (12.02, 11.18, "955 kg"),
         (10.22, 9.38, "920 kg"), (8.42, 7.58, "840 kg"),
         (6.62, 5.78, "800 kg"), (4.82, 3.98, "800 kg")]
for y1, y2, label in flows:
    arrow((X, y1), (X, y2))
    ax.text(X - 0.18, (y1 + y2) / 2, label, ha="right", va="center",
            fontsize=9, color="#1f4e79", fontweight="bold")

# ---------------- 右侧支流：废弃物与副产品 ----------------
B = 9.55          # 支流方框中心线
BW, BH = 3.5, 0.72
branches = [
    # (源 y, 源 x 起, 目标 y, 文本, 颜色)
    (12.50, 12.90, "废标签膜 PP/PVC  20 kg\n→ 外运焚烧发电", C_WASTE),
    (12.50, 12.10, "泥沙与干灰渣  25 kg\n→ 填埋 / 建材骨料", C_WASTE),
    (10.70, 10.70, "洗涤胶水与溶解性 COD  35 kg\n→ 厂内污水站", C_WASTE),
    (8.90, 9.55, "副产品：HDPE 瓶盖碎料  75 kg\n→ 外售塑料托盘/管道原料", C_COPROD),
    (8.90, 8.25, "HDPE 夹带损失  5 kg\n→ 沉渣脱水外运焚烧", C_WASTE),
    (7.10, 7.10, "黄变杂质与超细粉  40 kg\n→ 降级造粒 / 焚烧处置", C_WASTE),
]
for src_y, tgt_y, txt, color in branches:
    box(B, tgt_y, BW, BH, txt, color, fs=8.8)
    # 从工艺框右缘引出折线箭头到支流框左缘
    ax.plot([X + W / 2, 7.55, 7.55, B - BW / 2],
            [src_y, src_y, tgt_y, tgt_y],
            color="#666666", linewidth=1.3, linestyle=(0, (4, 2)))
    arrow((7.62, tgt_y), (B - BW / 2, tgt_y), color="#666666", lw=1.3)

# ---------------- 注释 ----------------
ax.text(0.3, 15.1, "PET 瓶机械物理再生系统物质流图（功能单位：1 t rPET；控制体：1000 kg 瓶砖）",
        fontsize=15, fontweight="bold", ha="left", va="center")
ax.text(10.9, 15.05, "Cradle-to-Gate 系统边界", fontsize=9, color="#8c8c8c",
        ha="right", fontstyle="italic")

ax.text(0.3, 1.5,
        "物质平衡校验：输入 1000 kg = 主产品 800 kg + 副产品 75 kg + 废弃物 125 kg（标签 20 + 泥沙 25 + COD 35 + HDPE 损失 5 + 超细粉 40）",
        fontsize=9, color="#444444")
ax.text(0.3, 0.75,
        "数据来源：case1_documentation.md 第一、二部分（MFA 物质平衡核算表）",
        fontsize=8.5, color="#888888", fontstyle="italic")

fig.tight_layout()
fig.savefig(OUT_DIR / "process_flow_diagram.png", dpi=320, bbox_inches="tight",
            facecolor="white")
fig.savefig(OUT_DIR / "process_flow_diagram.svg", bbox_inches="tight",
            facecolor="white")
print("已生成：process_flow_diagram.png (320 dpi)、process_flow_diagram.svg")
