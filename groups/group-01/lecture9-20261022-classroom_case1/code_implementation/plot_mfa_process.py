# -*- coding: utf-8 -*-
"""
第九讲 案例一 任务2：Python 绘制 PET 瓶回收工艺物质流程图（BFD）
依赖: matplotlib（conda env `mfa_lca_tea` 已安装）
运行: python plot_mfa_process.py
输出: process_flow_diagram.png (dpi=300)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "process_flow_diagram.png")

# 颜色方案
C_PROC = "#2C6FBB"   # 工艺单元（蓝）
C_MAIN = "#1F8A4C"   # 主物料流（绿）
C_WASTE = "#C0392B"  # 废弃物流（红）
C_BY = "#D68910"     # 副产品流（橙）
C_IN = "#5B2C6F"     # 原料（紫）

fig, ax = plt.subplots(figsize=(12.5, 8.5))
ax.set_xlim(0, 12.5)
ax.set_ylim(-0.7, 8.5)
ax.axis("off")

def box(x, y, w, h, text, fc, fs=9.5, tc="white", bold=True):
    ax.add_patch(FancyBboxPatch((x - w/2, y - h/2), w, h,
                 boxstyle="round,pad=0.06", fc=fc, ec="none", alpha=0.95, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            color=tc, fontweight="bold" if bold else "normal", zorder=4, linespacing=1.4)

def arrow(p1, p2, color, label="", lw=2.2, lx=0.0, ly=0.0, fs=8.5, lp=0.5):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=16,
                 color=color, lw=lw, zorder=2))
    if label:
        mx, my = (p1[0]+(p2[0]-p1[0])*lp, p1[1]+(p2[1]-p1[1])*lp)
        ax.text(mx+lx, my+ly, label, fontsize=fs, color=color, ha="center",
                va="center", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85), zorder=5)

# ---- 主干工艺单元（垂直链） ----
X = 4.6
box(X, 7.7, 3.6, 0.75, "原料输入：废弃打包 PET 瓶砖\n1000 kg（含瓶盖/标签/泥沙杂质）", C_IN, 9)
box(X, 6.3, 3.2, 0.7, "1. 拆包、筛选与干式脱标机", C_PROC)
box(X, 4.9, 3.2, 0.7, "2. 湿式粉碎与热碱洗单元\n85 °C，1.5% NaOH", C_PROC, 8.5)
box(X, 3.5, 3.2, 0.7, "3. 密度浮选分离槽（水介质）", C_PROC)
box(X, 2.1, 3.2, 0.7, "4. 光学色选、脱水与干燥", C_PROC)
box(X, 0.75, 3.4, 0.75, "5. 真空挤出造粒与固相增粘 SSP\n270 °C 熔融 / 210 °C 增粘", C_PROC, 8.5)
box(X, -0.9+0.75, 3.6, 0.8, "主产品：瓶级 rPET 颗粒\n800 kg（总收率 80.0%）", C_MAIN, 9.5)

# ---- 主干箭头 ----
arrow((X, 7.32), (X, 6.65), C_MAIN, "1000 kg", lw=3.0, lx=0.55)
arrow((X, 5.95), (X, 5.25), C_MAIN, "脱标瓶体", lw=2.6, lx=0.62)
arrow((X, 4.55), (X, 3.85), C_MAIN, "混合塑料碎屑", lw=2.6, lx=0.75)
arrow((X, 3.15), (X, 2.45), C_MAIN, "下沉相 PET", lw=2.6, lx=0.68)
arrow((X, 1.75), (X, 1.13), C_MAIN, "高洁净 PET 片料", lw=2.6, lx=0.85)
arrow((X, 0.37), (X, -0.15), C_MAIN, "800 kg", lw=3.2, lx=0.62, ly=0.28)

# ---- 废弃物流（右侧分支） ----
XW = 9.6
box(XW, 6.3, 3.4, 0.7, "废标签(PP/PVC)与灰尘泥沙：45 kg\n→ 外运焚烧 / 填埋骨料", C_WASTE, 8)
box(XW, 4.9, 3.4, 0.7, "溶解胶水残渣与悬浮物：35 kg\n→ 厂内污水站", C_WASTE, 8)
box(XW, 3.5, 3.4, 0.7, "HDPE 夹带损失：5 kg\n→ 沉渣脱水后焚烧", C_WASTE, 8)
box(XW, 2.1, 3.4, 0.7, "黄变杂质与超细粉：40 kg\n→ 降级造粒 / 焚烧", C_WASTE, 8)

arrow((X+1.6, 6.3), (XW-1.7, 6.3), C_WASTE, "脱除杂质 45 kg", lw=1.8, lp=0.45)
arrow((X+1.6, 4.9), (XW-1.7, 4.9), C_WASTE, "洗涤废液 35 kg", lw=1.8, lp=0.45)
arrow((X+1.6, 3.5), (XW-1.7, 3.5), C_WASTE, "沉渣 5 kg", lw=1.4, lp=0.45)
arrow((X+1.6, 2.1), (XW-1.7, 2.1), C_WASTE, "剔除 40 kg", lw=1.8, lp=0.45)

# ---- 副产品（左侧分支） ----
XB = 1.15
box(XB, 3.5, 2.3, 0.85, "副产品：HDPE 瓶盖碎料\n75 kg（回收率 93.75%）\n外售托盘/管道原料", C_BY, 8)
arrow((X-1.6, 3.5), (XB+1.15, 3.5), C_BY, "上浮相", lw=2.2, lp=0.55)

# ---- 标题与图例 ----
ax.text(6.25, 8.2, "废弃 PET 瓶机械物理再生系统 — 物质流工艺图（功能基准：1000 kg 瓶砖）",
        ha="center", fontsize=13, fontweight="bold")
import matplotlib.patches as mpatches
handles = [mpatches.Patch(fc=c, label=l) for c, l in
           [(C_MAIN, "主物料流"), (C_BY, "副产品流"), (C_WASTE, "废弃物流"), (C_IN, "原料输入")]]
ax.legend(handles=handles, loc="lower right", fontsize=9, framealpha=0.9)

fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"[saved] {OUT} (dpi=300)")
