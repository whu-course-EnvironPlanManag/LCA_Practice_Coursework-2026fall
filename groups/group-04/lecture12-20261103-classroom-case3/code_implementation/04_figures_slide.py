# -*- coding: utf-8 -*-
"""04_figures_slide.py —— 生成汇报级图表
产出：
  fig_process_flow_clean.png  工艺链通量流程图（清晰、无交叉、无裁切）
  fig_compliance.png          金属回收率合规对比图（对标工信部红线）
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["mathtext.fontset"] = "dejavusans"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(BASE, "figures_output")
os.makedirs(FIG, exist_ok=True)

# ---- 主题色（与 PPT 统一）----
INK    = "#12232B"
TEAL   = "#0F5C6E"
COPPER = "#C06B3E"
GREEN  = "#42795C"
RED    = "#A03028"
GRAY   = "#7D8A93"
BG     = "#F7F5F0"
BAND   = "#E4EDE7"


def box(ax, x0, y0, w, h, title, value, fc, tc="white", fs_title=12, fs_val=11.5):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.006,rounding_size=0.014",
                                fc=fc, ec="none", zorder=3))
    ax.text(x0 + w / 2, y0 + h * 0.655, title, ha="center", va="center",
            fontsize=fs_title, color=tc, fontweight="bold", zorder=4)
    ax.text(x0 + w / 2, y0 + h * 0.255, value, ha="center", va="center",
            fontsize=fs_val, color=tc, zorder=4)


def arrow_h(ax, x0, x1, y, label=None, color=INK):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>",
                                 mutation_scale=15, lw=1.6, color=color,
                                 zorder=2, shrinkA=0, shrinkB=0))
    if label:
        ax.text((x0 + x1) / 2, y + 0.020, label, ha="center", va="bottom",
                fontsize=9.5, color=INK, zorder=5)


def arrow_v(ax, x, y0, y1, color=INK):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>",
                                 mutation_scale=13, lw=1.3, color=color,
                                 zorder=2, shrinkA=0, shrinkB=0))


# ================================================================
# 图 1：工艺流程通量图
# ================================================================
fig, ax = plt.subplots(figsize=(14, 6.4), dpi=300)
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), 1, 1, fc=BG, zorder=0))

ax.text(0.035, 0.955, "衢州华友园区退役动力电池物质流通量", fontsize=17,
        fontweight="bold", color=INK, ha="left", va="center")
ax.text(0.035, 0.907, "基准年 20,000 t/a　·　LFP∶NMC = 6∶4　·　数值单位 t/a",
        fontsize=10.5, color="#5E6E77", ha="left", va="center")

# ---- 主链 ----
Y_MAIN, H_MAIN = 0.670, 0.150
box(ax, 0.035, Y_MAIN, 0.175, H_MAIN, "退役动力电池", "20,000", TEAL)
box(ax, 0.275, Y_MAIN, 0.175, H_MAIN, "S0 分流 · S1 拆解", "16,000", TEAL)
box(ax, 0.515, Y_MAIN, 0.175, H_MAIN, "S2 破碎分选（电芯）", "10,296", TEAL)
box(ax, 0.755, Y_MAIN, 0.210, H_MAIN, "S3–S6 再生提取（黑粉）", "5,983", TEAL)

arrow_h(ax, 0.210, 0.275, Y_MAIN + H_MAIN / 2, "80%")
arrow_h(ax, 0.450, 0.515, Y_MAIN + H_MAIN / 2, "电芯")
arrow_h(ax, 0.690, 0.755, Y_MAIN + H_MAIN / 2, "黑粉")

# ---- 支流 ----
Y_BR, H_BR = 0.400, 0.112
branch = [
    (0.195, "梯次利用", "4,000", GREEN, 0.272),
    (0.375, "副产 钢 / 塑 / 线束", "5,488", COPPER, 0.452),
    (0.545, "副产 Cu / Al / 隔膜", "4,004", COPPER, 0.602),
    (0.715, "尾渣 · 废水 · 损耗", "≈ 1,000", GRAY, 0.860),
]
for x0, t, v, c, ax_src in branch:
    box(ax, x0, Y_BR, 0.155, H_BR, t, v, c, fs_title=10.2, fs_val=10.2)
    arrow_v(ax, ax_src, Y_MAIN - 0.004, Y_BR + H_BR + 0.014)

# ---- 产品出厂（括号 + 箭头）----
Y_BKT = 0.258
ax.plot([0.180, 0.965], [Y_BKT, Y_BKT], color=GREEN, lw=1.2, zorder=2)
for xx in [0.180, 0.965]:
    ax.plot([xx, xx], [Y_BKT, Y_BKT - 0.014], color=GREEN, lw=1.2, zorder=2)
ax.text(0.035, Y_BKT + 0.075, "产品出厂", fontsize=11, color=GREEN,
        fontweight="bold", ha="left", va="center")
arrow_v(ax, 0.950, Y_MAIN - 0.004, Y_BKT + 0.006, color=GREEN)

Y_PD, H_PD = 0.108, 0.122
prods = [
    (0.185, "电池级 Li$_2$CO$_3$", "702"),
    (0.385, "混合 (Ni, Co, Mn) 盐", "3,242"),
    (0.590, "再生 LFP 正极", "839"),
    (0.770, "FePO$_4$", "738"),
]
for x0, t, v in prods:
    box(ax, x0, Y_PD, 0.180, H_PD, t, v, GREEN, fs_title=9.8, fs_val=10.2)

ax.text(0.035, 0.052,
        "数据：01_mfa_model.py 计算输出　|　工序回收率引自 Machala et al. 2025 (Nature Communications) 与工信部 2024 年本"
        "　|　混合盐按含水合物计",
        fontsize=8.5, color="#5E6E77", ha="left", va="center")

fig.savefig(os.path.join(FIG, "fig_process_flow_clean.png"),
            dpi=300, bbox_inches="tight", facecolor=BG)
plt.close(fig)


# ================================================================
# 图 2：金属回收率合规对比
# ================================================================
fig, ax = plt.subplots(figsize=(9.2, 4.4), dpi=300)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

metals = ["锂 Li", "镍 Ni", "钴 Co", "锰 Mn"]
rates = [92, 95, 95, 90]
colors = [GREEN, COPPER, COPPER, COPPER]
status = ["达标（≥90%）", "缺口（<98%）", "缺口（<98%）", "缺口（<98%）"]

y = list(range(len(metals)))
ax.barh(y, rates, height=0.52, color=colors, zorder=3)

ax.set_xlim(0, 128)
ax.set_ylim(-0.62, 3.85)
ax.set_xticks([0, 20, 40, 60, 80, 100])
ax.set_xlabel("冶炼段金属回收率（%）", fontsize=11, color=INK)
ax.set_yticks(y)
ax.set_yticklabels(metals, fontsize=11.5, color=INK)
ax.set_title("冶炼段回收率对标工信部约束性红线", fontsize=14,
             fontweight="bold", color=INK, pad=16, loc="left")

ax.axvline(90, ls="--", lw=1.7, color=GREEN, zorder=4)
ax.axvline(98, ls="--", lw=1.7, color=RED, zorder=4)

# 阈值标签（顶部并列，避免与刻度冲突）
ax.text(89.0, 3.62, "锂红线 90%", fontsize=9.5, color=GREEN, ha="right", va="center")
ax.text(99.0, 3.62, "镍钴锰红线 98%", fontsize=9.5, color=RED, ha="left", va="center")

for i, (r, c, st) in enumerate(zip(rates, colors, status)):
    ax.text(r - 2.5, i, f"{r}%", va="center", ha="right",
            fontsize=12.5, fontweight="bold", color="white", zorder=5)
    ax.text(104, i, st, va="center", fontsize=9.5, color=c, ha="left")

ax.grid(axis="x", alpha=0.22, zorder=1)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
ax.tick_params(colors=INK, labelsize=10.5)

fig.savefig(os.path.join(FIG, "fig_compliance.png"),
            dpi=300, bbox_inches="tight", facecolor=BG)
plt.close(fig)

print("已生成: fig_process_flow_clean.png, fig_compliance.png")
