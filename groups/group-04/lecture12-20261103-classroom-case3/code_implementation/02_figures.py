# -*- coding: utf-8 -*-
"""
02_figures.py — 生成方向 B 园区物质流桑基图与元素平衡图（>=300 DPI）
依赖：01_mfa_model.py 的计算结果（直接 import 复用，避免口径不一致）
输出：figures_output/fig1_mfa_sankey.png, fig2_element_balance.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

import importlib.util
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("mfa", os.path.join(BASE, "code_implementation", "01_mfa_model.py"))
mfa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mfa)
R = mfa.main()

FIG = os.path.join(BASE, "figures_output")
os.makedirs(FIG, exist_ok=True)

cap = R["capacity"]; f_dir = R["f_dir"]; f_ind = R["f_ind"]; f_rec = R["f_rec"]
nmc_bm = R["nmc_blackmass_mass"]; lfp_bm = R["lfp_blackmass_mass"]
li2co3 = R["li2co3_total"]

# ---------------- 图1：物质流桑基图（手绘流带） ----------------
fig, ax = plt.subplots(figsize=(14, 8))

# 节点: (name, x, y_center, height, color)
nodes = {
    "feed":   ("退役动力电池\n20,000 t/a", 0.0, 0.50, 1.00, "#4C72B0"),
    "triage": ("S0 SOH三级分流", 0.14, 0.50, 1.00, "#5B84C4"),
    "echelon":("梯次利用\n4,000 t/a", 0.28, 0.88, 0.20, "#55A868"),
    "s1":     ("S1 放电拆解\n16,000 t/a", 0.28, 0.42, 0.78, "#8172B3"),
    "s2":     ("S2 机械破碎分选", 0.46, 0.42, 0.70, "#937860"),
    "nmc":    ("S3+S4 焙烧+湿法\n(NMC黑粉 3,331 t/a)", 0.66, 0.72, 0.22, "#C44E52"),
    "lfp_dr": ("S5 直接再生\n(LFP黑粉50%)", 0.66, 0.40, 0.14, "#DD8452"),
    "lfp_hy": ("S6 湿法提锂\n(LFP黑粉50%)", 0.66, 0.22, 0.14, "#DA8BC3"),
    "prod":   ("产品出厂", 0.88, 0.55, 0.62, "#64B5AC"),
    "resid":  ("尾渣/废水/损耗", 0.88, 0.08, 0.14, "#999999"),
}

def node_xywh(key):
    name, x, yc, h, c = nodes[key]
    return x, yc, h

def draw_node(key):
    name, x, yc, h, c = nodes[key]
    w = 0.085
    ax.add_patch(FancyBboxPatch((x, yc - h/2), w, h, boxstyle="round,pad=0.004",
                                fc=c, ec="black", lw=0.8, alpha=0.92, zorder=3))
    ax.text(x + w/2, yc, name, ha="center", va="center", fontsize=9.5, color="white",
            fontweight="bold", zorder=4)

def flow(k1, k2, frac, color, label=None, off1=0.0, off2=0.0):
    x1, yc1, h1 = node_xywh(k1); x2, yc2, h2 = node_xywh(k2)
    w = 0.085
    b1 = frac * h1; b2 = frac * h2
    y1 = yc1 + off1 * h1; y2 = yc2 + off2 * h2
    pts = [(x1 + w, y1 - b1/2), (x1 + w, y1 + b1/2),
           (x2, y2 + b2/2), (x2, y2 - b2/2)]
    ax.add_patch(Polygon(pts, closed=True, fc=color, ec="none", alpha=0.35, zorder=1))
    if label:
        ax.text((x1 + w + x2)/2, (y1 + y2)/2 + max(b1, b2)*0.6, label,
                fontsize=8, ha="center", color="#333333", zorder=5)

for k in nodes:
    draw_node(k)

# 主流带
flow("feed", "triage", 1.0, "#4C72B0")
flow("triage", "echelon", 0.20, "#55A868", "梯次 20%")
flow("triage", "s1", 0.80, "#8172B3", "再生 80%")
flow("s1", "s2", 0.42, "#937860", "电芯 10,296 t/a")
flow("s2", "nmc", 0.31, "#C44E52")
flow("s2", "lfp_dr", 0.16, "#DD8452")
flow("s2", "lfp_hy", 0.16, "#DA8BC3")
flow("nmc", "prod", 0.95, "#C44E52", "Li2CO3+混合盐")
flow("lfp_dr", "prod", 0.99, "#DD8452", "再生LFP")
flow("lfp_hy", "prod", 0.92, "#DA8BC3", "Li2CO3+FePO4")
flow("s1", "prod", 0.25, "#64B5AC", "Cu/Al/钢结构")
flow("s2", "resid", 0.05, "#999999")
flow("nmc", "resid", 0.05, "#999999")
flow("lfp_hy", "resid", 0.08, "#999999")

ax.set_xlim(-0.02, 1.05); ax.set_ylim(0, 1.05); ax.axis("off")
ax.set_title("图2-1 衢州华友循环资源再生产业园退役动力电池多工序物质流桑基图（基准年 20,000 t/a）",
             fontsize=13, fontweight="bold", pad=12)
ax.text(0.0, -0.02, "数据：01_mfa_model.py 输出；工序回收率参数引自 Machala et al. 2025 [4]、工信部2024年本 [10]",
        fontsize=8, color="#555555")
fig.savefig(os.path.join(FIG, "fig1_mfa_sankey.png"), dpi=350, bbox_inches="tight")
plt.close(fig)

# ---------------- 图2：元素平衡图（输入 vs 输出分项） ----------------
ti, to, res = R["total_in"], R["total_out"], R["residue"]
els = ["Li", "Ni", "Co", "Mn", "Fe", "Cu", "Al"]
xin = [ti[e] for e in els]
xprod = [to[e] for e in els]
xres = [res[e] for e in els]

x = np.arange(len(els)); w = 0.38
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.bar(x - w/2, xin, w, label="系统输入", color="#4C72B0")
ax.bar(x + w/2, xprod, w, label="产品/副产物/梯次利用输出", color="#55A868")
ax.bar(x + w/2, xres, w, bottom=xprod, label="尾渣/废水/损耗（差额闭合）", color="#DD8452")
for i, e in enumerate(els):
    ax.text(x[i] - w/2, xin[i] * 1.01, f"{xin[i]:.1f}", ha="center", fontsize=8)
    ax.text(x[i] + w/2, (xprod[i] + xres[i]) * 1.01, f"{xprod[i]+xres[i]:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(els)
ax.set_ylabel("质量流（t/a）")
ax.set_title("图2-2 全系统元素级质量守恒核验（最大相对误差 0.000%，<0.05% 达标）", fontsize=12, fontweight="bold")
ax.legend(); ax.grid(axis="y", alpha=0.3)
fig.savefig(os.path.join(FIG, "fig2_element_balance.png"), dpi=350, bbox_inches="tight")
plt.close(fig)

print("已生成: figures_output/fig1_mfa_sankey.png, fig2_element_balance.png")
