# -*- coding: utf-8 -*-
"""
案例一 · 任务 2：绘制"废弃 PET 瓶机械物理再生"工艺物质流程图（BFD, 块状流程图）

依赖：仅需 matplotlib（纯 Python，零底层 C 依赖，随 conda 环境自带）。
输出：
    process_flow_diagram.png  (300 dpi 高清位图)
    process_flow_diagram.svg  (矢量图)
物质平衡基准：1000 kg 瓶砖 -> 800 kg 瓶级 rPET (收率 80.0%)
"""

import matplotlib
matplotlib.use("Agg")  # 无界面环境安全渲染
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ----------------------------------------------------------------------------
# 中文字体与全局样式（Windows 下自动回退到雅黑/黑体）
# ----------------------------------------------------------------------------
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

# 节点配色
C_INPUT = "#dbeafe"      # 原料输入：浅蓝
C_PROC  = "#e8f5e9"      # 单元操作：浅绿
C_WASTE = "#fdecea"      # 废物流：浅红
C_BYP   = "#fff8e1"      # 副产品：浅黄
C_PROD  = "#c8e6c9"      # 主产品：深一点的绿
C_EDGE  = "#37474f"      # 边框

BOX_W = 13.0             # 主流程框宽
BOX_H = 12.5             # 主流程框高


def add_box(ax, cx, cy, text, fc, w=BOX_W, h=BOX_H, fs=9.5, ec=C_EDGE):
    """在 (cx, cy) 处绘制圆角方框，cy 为框中心。"""
    x, y = cx - w / 2, cy - h / 2
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.25,rounding_size=0.8",
        linewidth=1.4, edgecolor=ec, facecolor=fc, zorder=2,
    )
    ax.add_patch(box)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, zorder=3, linespacing=1.5)
    return box


def add_arrow(ax, x1, y1, x2, y2, label="", label_dy=2.6, color=C_EDGE, lw=1.6):
    """绘制带可选标签的有向箭头，标签置于中点上方。"""
    ax.add_patch(
        FancyArrowPatch((x1, y1), (x2, y2),
                        arrowstyle="-|>", mutation_scale=16,
                        linewidth=lw, color=color, zorder=1)
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + label_dy, label,
                ha="center", va="bottom", fontsize=8.6, color="#1a237e", zorder=4)


def build_diagram():
    fig, ax = plt.subplots(figsize=(17, 8.2))
    ax.set_xlim(0, 108)
    ax.set_ylim(0, 74)
    ax.axis("off")
    ax.set_title("废弃 PET 瓶机械物理再生 · 工艺物质流程图（MFA，基准 1000 kg 瓶砖）",
                 fontsize=15, fontweight="bold", pad=14, color="#1a237e")

    # ------------------------------------------------------------------
    # 主流程链（横排）：原料 -> 5 个工段 -> 主产品
    # ------------------------------------------------------------------
    y_main = 56.0
    y_waste = 30.0

    add_box(ax, 5, y_main, "原料输入\n废弃打包 PET 瓶砖\n1000 kg", C_INPUT, w=14, fs=9.5)
    add_box(ax, 20, y_main, "1. 拆包、筛选与\n干式脱标机", C_PROC)
    add_box(ax, 35, y_main, "2. 湿式粉碎与\n热碱洗单元\n(85 °C, 1.5% NaOH)", C_PROC, h=15)
    add_box(ax, 50, y_main, "3. 密度浮选\n分离槽\n(水介质 1.0 g/cm$^3$)", C_PROC, h=15)
    add_box(ax, 65, y_main, "4. 光学色选、\n脱水与干燥", C_PROC)
    add_box(ax, 80, y_main, "5. 真空挤出造粒\n与固相增粘 SSP\n(270/210 °C)", C_PROC, h=15)
    add_box(ax, 98, y_main, "主产品\n瓶级 rPET 颗粒\n800 kg (收率 80%)", C_PROD, w=15, fs=9.5)

    # 废物流 / 副产品节点（主链下方）
    add_box(ax, 20, y_waste, "废标签(PP/PVC)\n+ 灰尘泥沙\n45 kg", C_WASTE, h=13)
    add_box(ax, 35, y_waste, "洗涤废液\n(胶水残渣/COD)\n35 kg", C_WASTE, h=13)
    add_box(ax, 50, y_waste, "副产品\n回收 HDPE 瓶盖\n75 kg", C_BYP, h=13)
    add_box(ax, 65, y_waste, "杂色黄变切片\n+ 超细粉\n40 kg", C_WASTE, h=13)

    # ------------------------------------------------------------------
    # 主链箭头（水平，标注中间段质量通量）
    # ------------------------------------------------------------------
    add_arrow(ax, 12, y_main, 13.5, y_main, "1000 kg")
    add_arrow(ax, 26.5, y_main, 28.5, y_main, "955 kg")
    add_arrow(ax, 41.5, y_main, 43.5, y_main, "920 kg")
    add_arrow(ax, 56.5, y_main, 58.5, y_main, "840 kg")
    add_arrow(ax, 71.5, y_main, 73.5, y_main, "800 kg")
    add_arrow(ax, 86.5, y_main, 89.5, y_main, "800 kg")

    # ------------------------------------------------------------------
    # 分流箭头（主链 -> 废物流/副产品）
    # ------------------------------------------------------------------
    add_arrow(ax, 20, y_main - BOX_H / 2, 20, y_waste + 6.5, "45 kg")
    add_arrow(ax, 35, y_main - 7.5, 35, y_waste + 6.5, "35 kg")
    add_arrow(ax, 50, y_main - 7.5, 50, y_waste + 6.5, "75 kg\n(另 5 kg 入沉渣)")
    add_arrow(ax, 65, y_main - BOX_H / 2, 65, y_waste + 6.5, "40 kg")

    # ------------------------------------------------------------------
    # 图注
    # ------------------------------------------------------------------
    legend_items = [
        ("原料输入", C_INPUT), ("单元操作", C_PROC), ("副产品", C_BYP),
        ("废物流", C_WASTE), ("主产品", C_PROD),
    ]
    lx = 3
    for name, color in legend_items:
        ax.add_patch(FancyBboxPatch((lx, 3.5), 9, 4.6,
                                    boxstyle="round,pad=0.15,rounding_size=0.5",
                                    facecolor=color, edgecolor=C_EDGE, linewidth=1.1))
        ax.text(lx + 4.5, 5.8, name, ha="center", va="center", fontsize=8.6)
        lx += 11.5

    ax.text(3, 1.2, "箭头旁数字为质量通量 (kg)；物质平衡：Σ输入 1000 kg = Σ输出 1000 kg（800 rPET + 75 HDPE + 125 杂质损失）",
            fontsize=8.8, color="#546e7a")

    fig.tight_layout()
    return fig


if __name__ == "__main__":
    fig = build_diagram()
    fig.savefig("process_flow_diagram.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig("process_flow_diagram.svg", bbox_inches="tight", facecolor="white")
    print("已生成 process_flow_diagram.png / process_flow_diagram.svg (300 dpi)")