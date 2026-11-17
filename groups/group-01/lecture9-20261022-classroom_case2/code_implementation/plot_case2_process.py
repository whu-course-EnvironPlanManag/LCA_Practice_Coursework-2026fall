# -*- coding: utf-8 -*-
"""
案例二 任务3：CO2捕集+绿氢合成绿色甲醇 工艺物质流程图（含循环回路 BFD）
依赖: matplotlib（conda env `mfa_lca_tea`）
运行: python plot_case2_process.py
输出: case2_process_flow_diagram.png (dpi=300)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "case2_process_flow_diagram.png")

C_PROC = "#2C6FBB"; C_MAIN = "#1F8A4C"; C_WASTE = "#C0392B"
C_BY = "#D68910"; C_IN = "#5B2C6F"; C_REC = "#8E44AD"

fig, ax = plt.subplots(figsize=(13.5, 8.6))
ax.set_xlim(0, 13.5); ax.set_ylim(0, 9.3); ax.axis("off")

def box(x, y, w, h, text, fc, fs=9, tc="white"):
    ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.07",
                 fc=fc, ec="none", alpha=0.95, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold", zorder=4, linespacing=1.4)

def arrow(p1, p2, color, label="", lw=2.2, fs=8.5, rad=0.0, lx=0.0, ly=0.0):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=15,
                 color=color, lw=lw, zorder=2,
                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx = (p1[0]+p2[0])/2 + lx; my = (p1[1]+p2[1])/2 + ly
        ax.text(mx, my, label, fontsize=fs, color=color, ha="center", va="center",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.88), zorder=5)

# ---- 主干（水平链） ----
box(1.35, 5.6, 2.1, 0.85, "新鲜 CO2 进料\n1423 kg\n(MEA 捕集提纯)", C_IN, 8.5)
box(1.35, 3.4, 2.1, 0.85, "新鲜 H2 进料\n198 kg\n(PEM 电解 10296 kWh)", C_IN, 8.5)
box(4.1, 4.5, 1.9, 0.8, "混合器\n预热器", C_PROC)
box(6.55, 4.5, 2.5, 1.0, "固定床甲醇合成反应器\nCu/ZnO/Al2O3\n250 C / 5.0 MPa / 单程 25%", C_PROC, 8.5)
box(9.35, 4.5, 2.0, 0.9, "冷却冷凝器\n高压气液分离器", C_PROC, 8.5)
box(11.9, 4.5, 1.9, 0.85, "双塔精馏\n脱轻 + 脱水", C_PROC)
box(11.9, 6.6, 2.3, 0.8, "主产品：聚合级精甲醇\n1000 kg (>99.85%)", C_MAIN, 8.5)
box(11.9, 2.5, 2.1, 0.8, "副产生成水 575 kg\n(微滤后回流电解槽)", C_BY, 8.5)

arrow((2.4, 5.6), (3.15, 4.85), C_MAIN, "1423 kg", rad=-0.12, lx=0.25, ly=0.18)
arrow((2.4, 3.4), (3.15, 4.15), C_MAIN, "198 kg", rad=0.12, lx=0.25, ly=-0.18)
arrow((5.05, 4.5), (5.3, 4.5), C_MAIN, "6261 kg", lw=2.8, lx=0.0, ly=0.68)
arrow((7.8, 4.5), (8.35, 4.5), C_MAIN, "6261 kg", lw=2.8, lx=0.0, ly=0.68)
arrow((10.35, 4.5), (10.95, 4.5), C_MAIN, "粗甲醇 1575 kg", lw=2.4, fs=8, lx=0.1, ly=0.32)
arrow((11.9, 4.93), (11.9, 6.2), C_MAIN, "1000 kg", lw=2.8, ly=0.0, lx=0.55)
arrow((11.9, 4.07), (11.9, 2.9), C_BY, "575 kg", lw=2.0, lx=0.5)

# ---- 分离顶部气相 -> 分流器 ----
box(9.35, 6.6, 1.7, 0.65, "循环气分流器", C_PROC)
arrow((9.35, 4.95), (9.35, 6.27), C_REC, "未反应气\n4686 kg", lw=2.6, fs=8, lx=0.72)

# ---- 主循环 99% -> 循环压缩机 -> 返回混合器 ----
box(6.55, 6.6, 1.9, 0.65, "循环压缩机", C_PROC)
arrow((8.5, 6.6), (7.5, 6.6), C_REC, "99.0% 循环 4640 kg", lw=3.0, fs=8, ly=0.34)
arrow((5.6, 6.6), (4.1, 6.6), C_REC, "", lw=2.6)
arrow((4.1, 6.6), (4.1, 4.9), C_REC, "循环回路\nRecycle Loop", lw=2.6, fs=8, rad=0.0, lx=0.85, ly=0.25)

# ---- 驰放 1% -> 锅炉 ----
box(12.35, 7.75, 2.15, 0.7, "驰放废气 46 kg → 厂内锅炉\n(1.0% 分流, 碳损耗 4.0%)", C_WASTE, 8)
arrow((9.8, 6.93), (11.28, 7.6), C_WASTE, "驰放 1.0%", lw=1.8, fs=8, rad=0.15, lx=0.1, ly=0.28)

# ---- 标题与图例 ----
ax.text(6.75, 8.95, "CO2 捕集 + 绿氢合成绿色甲醇系统 — 物质流工艺图（含未反应气循环回路 | 功能单位: 1 t 精甲醇）",
        ha="center", fontsize=12.5, fontweight="bold")
import matplotlib.patches as mpatches
handles = [mpatches.Patch(fc=c, label=l) for c, l in
           [(C_IN, "新鲜进料"), (C_MAIN, "主物料流"), (C_REC, "循环回路"),
            (C_BY, "副产品/回用水"), (C_WASTE, "驰放废气")]]
ax.legend(handles=handles, loc="lower left", fontsize=8.5, framealpha=0.9, ncol=5,
          bbox_to_anchor=(0.02, -0.02))

fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"[saved] {OUT} (dpi=300)")
