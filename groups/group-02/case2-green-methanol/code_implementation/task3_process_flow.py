# -*- coding: utf-8 -*-
"""
任务 3：调用 matplotlib 自主绘制「绿氢合成绿色甲醇」工艺物质流程图（含循环回路）
案例二 · Power-to-Methanol / CCU

输出：task3_process_flow_diagram.png (300 dpi) + .svg
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(14.5, 7.8))
ax.set_xlim(-0.6, 15.4)
ax.set_ylim(-0.9, 7.7)
ax.axis("off")
ax.set_aspect("equal")

c_in = "#d5f5e3"      # 进料
c_unit = "#d6eaf8"    # 单元设备
c_prod = "#fdebd0"    # 产品
c_loop = "#e8daef"    # 循环/压缩机
c_purge = "#fadbd8"   # 驰放

def box(cx, cy, w, h, text, color, fs=9.5):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.12",
                                linewidth=1.4, edgecolor="#34495e",
                                facecolor=color, zorder=3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, zorder=4)

def arrow(p1, p2, text=None, color="#2c3e50", lw=1.6, fs=8.5, tx=None, ty=None, ha="center"):
    ax.annotate("", xy=p2, xytext=p1,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                shrinkA=2, shrinkB=2, mutation_scale=16))
    if text:
        if tx is None:
            tx = (p1[0] + p2[0]) / 2
        if ty is None:
            ty = (p1[1] + p2[1]) / 2
        ax.text(tx, ty, text, ha=ha, va="center", fontsize=fs, color=color,
                zorder=5, bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.6))

# ------------------------------------------------------------------ 进料
box(0.9, 4.9, 2.3, 1.1, "新鲜 CO2 进料\n1423 kg (纯度 99.8%)", c_in)
box(0.9, 2.0, 2.3, 1.1, "新鲜 H2 进料\n198 kg (PEM 电解)", c_in)

# ---------------------------------------------------------- 主链单元设备
box(3.5, 3.45, 2.1, 1.15, "气体混合器\n与预热器", c_unit)
box(6.7, 3.45, 2.9, 1.30, "固定床甲醇合成反应器\n(Cu/ZnO/Al2O3, 250℃, 5.0 MPa)\n单程转化率 25%", c_unit)
box(9.8, 3.45, 2.6, 1.15, "冷却冷凝器 +\n高压气液分离器", c_unit)
box(12.7, 3.45, 2.4, 1.15, "循环气分流器\n99% 循环 / 1% 驰放", c_unit)

arrow((2.05, 4.9), (2.45, 4.3))
arrow((2.05, 2.0), (2.45, 2.6))
arrow((4.55, 3.45), (5.25, 3.45))
arrow((8.15, 3.45), (8.5, 3.45))
arrow((11.1, 3.45), (11.5, 3.45), text="分离气相 4686 kg", tx=11.3, ty=3.75)

# ---------------------------------------------------------- 循环回路（顶部）
arrow((12.3, 4.03), (12.3, 6.6), text="未反应循环气\n4640 kg (99%)", tx=13.15, ty=6.0, ha="left", color="#7d3c98")
arrow((12.3, 6.6), (9.0, 6.6))
box(7.9, 6.6, 2.2, 1.0, "循环压缩机", c_loop)
arrow((6.8, 6.6), (3.6, 6.6))
arrow((3.5, 6.6), (3.5, 4.03), color="#7d3c98")

# ---------------------------------------------------------- 驰放气（顶右）
box(13.9, 6.7, 2.4, 1.0, "送厂内锅炉燃烧供热\n驰放气 46 kg (1%)", c_purge)
arrow((13.35, 4.05), (13.7, 6.15), text="驰放 46 kg", tx=14.35, ty=5.1, ha="left", color="#c0392b")

# ---------------------------------------------------------- 精馏与产品（底部）
box(9.8, 1.55, 3.0, 1.15, "双塔精馏提纯系统\n(常压脱轻塔 + 加压脱水精馏塔)", c_unit)
arrow((9.8, 2.87), (9.8, 2.13), text="粗甲醇液相\n1575 kg", tx=9.0, ty=2.5, ha="right", color="#935116")

box(12.7, 0.85, 2.7, 1.05, "主产品：聚合级精甲醇\n1000 kg (>99.85%)", c_prod)
arrow((11.3, 1.55), (12.05, 1.25), text="精甲醇", tx=11.8, ty=1.72, color="#935116")

box(6.9, 0.85, 2.7, 1.05, "副产生成水 575 kg\n(微滤后回流至电解槽)", c_prod)
arrow((8.3, 1.55), (7.4, 1.25), text="生成水", tx=7.85, ty=1.72, color="#935116")

# ---------------------------------------------------------- 标题
ax.text(7.2, 7.45,
        "工业园区 CO2 捕集 + 绿氢合成绿色甲醇 —— 工艺物质流程图（含循环回路 Recycle Loop）",
        ha="center", fontsize=13, fontweight="bold", color="#1a252f")

png = os.path.join(os.path.dirname(__file__), "task3_process_flow_diagram.png")
svg = os.path.join(os.path.dirname(__file__), "task3_process_flow_diagram.svg")
fig.savefig(png, dpi=300, bbox_inches="tight")
fig.savefig(svg, bbox_inches="tight")
print("已输出：")
print("  ", png)
print("  ", svg)