# =============================================================
# 案例二 任务 3：纯 matplotlib 工艺流程图 (含未反应气循环回路)
# 输出: case2_process_flow.png (300 dpi)
# 无需 schemdraw — 纯 matplotlib
# =============================================================
import warnings
from pathlib import Path
warnings.filterwarnings('ignore')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle, FancyBboxPatch

OUT_DIR = Path(__file__).resolve().parent
print("=" * 70)
print("案例二 · 绿色甲醇合成 · matplotlib 工艺流程图 (含循环回路)")
print("=" * 70)

# ---- 中文字体 ----
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(-1, 16)
ax.set_ylim(-1, 9)
ax.axis('off')
fig.patch.set_facecolor('white')

# ---- 画框辅助函数 ----
def box(ax, x, y, w, h, text, color='#3498db', fc='#ecf0f1', lw=2, fontsize=10, text_color='#2c3e50'):
    """圆角矩形 + 文字"""
    rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                          boxstyle="round,pad=0.05",
                          fc=fc, ec=color, lw=lw)
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            color=text_color, fontweight='bold', wrap=True)

def arrow(ax, x1, y1, x2, y2, color='#34495e', lw=2, style='->'):
    """箭头"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                connectionstyle='arc3,rad=0'))

def curved_arrow(ax, x1, y1, x2, y2, color='#8e44ad', lw=2, rad=-0.3):
    """弯曲箭头 (用于循环回路)"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                connectionstyle=f'arc3,rad={rad}'))

def label(ax, x, y, text, fontsize=9, color='#7f8c8d', ha='center'):
    ax.text(x, y, text, ha=ha, va='center', fontsize=fontsize, color=color, style='italic')

# =============================================================
# 节点坐标设计
# =============================================================
# 主流程 (从左到右)
# x: 1 → 3 → 5.5 → 8 → 10.5 → 13 → 14.5
# y: 中层 y=4.0  (主流程线)

# ---- 新鲜进料 ----
box(ax, 1.0, 5.5, 2.0, 0.9, '新鲜 CO₂ 进料\n1423 kg', color='#2980b9', fc='#d6eaf8')
box(ax, 1.0, 2.5, 2.0, 0.9, '新鲜绿氢进料\n198 kg', color='#2980b9', fc='#d6eaf8')

# ---- 混合预热器 ----
box(ax, 3.5, 4.0, 1.8, 1.0, '气体混合器\n& 预热器', color='#7f8c8d', fc='#f4f6f6')

# ---- 固定床反应器 ----
box(ax, 6.0, 4.0, 2.8, 1.4, '固定床甲醇合成反应器\nCu/ZnO/Al₂O₃ · 250℃ · 5.0 MPa\n单程转化率 25%',
    color='#e67e22', fc='#fef9e7', lw=2.5)

# ---- 冷却冷凝器 + 气液分离器 ----
box(ax, 9.0, 4.0, 2.2, 1.0, '冷却冷凝器\n& 高压气液分离器', color='#7f8c8d', fc='#f4f6f6')

# ---- 双塔精馏 ----
box(ax, 11.5, 4.0, 2.2, 1.0, '双塔精馏提纯\n(常压脱轻 + 加压脱水)', color='#16a085', fc='#d5f5e3')

# ---- 主产品 ----
box(ax, 14.0, 4.0, 2.2, 1.0, '主产品: 精甲醇 1000 kg\n(纯度 > 99.85%)',
    color='#27ae60', fc='#abebc6', lw=2.5)

# ---- 副产水 ----
box(ax, 11.5, 1.8, 2.0, 0.8, '副产生成水 575 kg\n(回流电解槽)', color='#5dade2', fc='#d6eaf8')

# =============================================================
# 循环回路 (上方紫色 99% 回流)
# =============================================================
# 循环气分流器 (CoolN 上方)
box(ax, 9.0, 7.2, 2.2, 0.9, '循环气分流器\n99%循环 / 1%驰放', color='#8e44ad', fc='#f4ecf7')

# 循环压缩机
box(ax, 4.0, 7.2, 1.8, 0.9, '循环压缩机', color='#8e44ad', fc='#f4ecf7')

# 驰放气
box(ax, 12.5, 7.2, 1.8, 0.9, '驰放气 46 kg\n(送锅炉)', color='#c0392b', fc='#fadbd8')

# =============================================================
# 箭头连线
# =============================================================
# ---- 主流程 (中层蓝色箭头) ----
arrow(ax, 2.0, 5.5, 2.6, 4.3, color='#2980b9')  # CO2 → Mix
arrow(ax, 2.0, 2.5, 2.6, 3.7, color='#2980b9')  # H2 → Mix
arrow(ax, 4.4, 4.0, 4.6, 4.0, color='#34495e')  # Mix → Reactor
arrow(ax, 7.4, 4.0, 7.9, 4.0, color='#34495e')  # Reactor → Cool
arrow(ax, 10.1, 4.0, 10.4, 4.0, color='#34495e')  # Cool → Distill
arrow(ax, 12.6, 4.0, 12.9, 4.0, color='#34495e')  # Distill → Product

# Distill → 副产水
arrow(ax, 11.5, 3.5, 11.5, 2.2, color='#5dade2')

# ---- 循环回路 (上方紫色) ----
# Cool 顶部出 → 分流器
arrow(ax, 9.0, 4.5, 9.0, 6.75, color='#8e44ad')
label(ax, 9.7, 5.7, '气相未反应气 4686 kg', color='#8e44ad', fontsize=8)

# 分流器 → 99% 左走压缩机
arrow(ax, 7.9, 7.2, 4.9, 7.2, color='#8e44ad')
label(ax, 6.4, 7.5, '99.0% · 循环气 4640 kg', color='#8e44ad', fontsize=9)

# 分流器 → 1% 右走驰放
arrow(ax, 10.1, 7.2, 11.6, 7.2, color='#c0392b')
label(ax, 10.8, 7.6, '1.0% · 驰放气 46 kg', color='#c0392b', fontsize=9)

# 压缩机 → 回流到 Mix 顶部
curved_arrow(ax, 3.1, 7.2, 3.5, 4.6, color='#8e44ad', rad=-0.25)
label(ax, 1.8, 6.0, '未反应循环气\n(循环比 3.8 : 1)', color='#8e44ad', fontsize=9, ha='center')

# =============================================================
# 物料通量标注
# =============================================================
label(ax, 3.5, 3.2, '反应器入口混合气: 6261 kg\n(新鲜 + 循环)', fontsize=8, color='#555')
label(ax, 6.0, 3.2, '反应后出口: 6261 kg\n(粗甲醇液相 + 未反应气相)', fontsize=8, color='#555')
label(ax, 9.0, 3.2, '液相粗甲醇: 1575 kg →', fontsize=8, color='#555')

# =============================================================
# 标题 & 图例
# =============================================================
ax.text(7.5, 8.6, '绿色甲醇合成工艺流程 — 含未反应气循环回路',
        ha='center', va='center', fontsize=16, fontweight='bold', color='#2c3e50')
ax.text(7.5, 8.25, 'Recycle Ratio = 3.8 : 1  ·  单程转化率 = 25%  ·  碳转化利用率 = 96%',
        ha='center', va='center', fontsize=11, color='#7f8c8d', style='italic')

# 图例
legend_elements = [
    mpatches.Patch(facecolor='#d6eaf8', edgecolor='#2980b9', label='原料 / 进料'),
    mpatches.Patch(facecolor='#fef9e7', edgecolor='#e67e22', label='核心反应器'),
    mpatches.Patch(facecolor='#abebc6', edgecolor='#27ae60', label='主产品'),
    mpatches.Patch(facecolor='#f4ecf7', edgecolor='#8e44ad', label='循环回路 (99%)'),
    mpatches.Patch(facecolor='#fadbd8', edgecolor='#c0392b', label='驰放 / 排出 (1%)'),
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=10,
          framealpha=0.9, edgecolor='#bdc3c7')

plt.tight_layout()

out_png = OUT_DIR / "case2_process_flow.png"
plt.savefig(out_png, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ 工艺流程图已保存: {out_png}")
print(f"   文件大小: {out_png.stat().st_size / 1024:.1f} KB")
plt.close()

print()
print("=" * 70)
print("🎉 任务 3 完成：matplotlib 工艺流程图 (无 schemdraw 依赖)")
print("=" * 70)
