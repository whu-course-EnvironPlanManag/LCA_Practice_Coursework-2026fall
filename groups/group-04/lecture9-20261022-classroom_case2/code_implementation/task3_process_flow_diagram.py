"""
案例二 任务3：CO2 捕集耦合绿氢合成绿色甲醇 - 工艺物质流程图
============================================================
使用 matplotlib 绘制含循环回路（Recycle Loop）的工艺流程方框图，
展示 CO2 捕集、PEM 电解制氢、甲醇合成、气液分离与精馏提纯全流程。
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# 颜色定义
C_INPUT = '#4A90D9'      # 原料输入
C_REACTOR = '#7FB3D5'    # 工艺单元
C_PRODUCT = '#2ECC71'    # 主产品
C_BYPRODUCT = '#27AE60'  # 副产品
C_WASTE = '#E74C3C'      # 废弃物
C_WATER = '#3498DB'      # 水循环
C_ENERGY = '#F39C12'     # 能量/电力
C_PURPLE = '#9B59B6'     # 粗甲醇

print("=" * 70)
print("案例二 任务3：绘制 CO2 绿氢合成甲醇工艺流程图")
print("=" * 70)

fig, ax = plt.subplots(figsize=(18, 22))
ax.set_xlim(-1, 15)
ax.set_ylim(-1, 23)
ax.axis('off')
ax.set_aspect('equal')

def draw_box(x, y, w, h, label, color, fontsize=9):
    """绘制带圆角的方框"""
    rect = mpatches.FancyBboxPatch((x - w/2, y - h/2), w, h,
                                    boxstyle="round,pad=0.1",
                                    linewidth=2, edgecolor=color,
                                    facecolor=color + '25', zorder=2)
    ax.add_patch(rect)
    ax.text(x, y, label, ha='center', va='center', fontsize=fontsize,
            fontweight='bold', zorder=3, linespacing=1.4)

def arrow(x1, y1, x2, y2, color='#333', lw=2, label='', lo=(0, 0.25)):
    """绘制箭头"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw), zorder=1)
    if label:
        ax.text((x1+x2)/2 + lo[0], (y1+y2)/2 + lo[1], label,
                ha='center', va='center', fontsize=8, color=color,
                bbox=dict(boxstyle='round,pad=0.15', facecolor='lightyellow',
                          edgecolor='none', alpha=0.85), zorder=4)

# 标题
ax.text(7, 22.2, 'CO\u2082 捕集耦合绿氢合成绿色甲醇工艺流程图',
        ha='center', fontsize=18, fontweight='bold', color='#2C3E50')
ax.text(7, 21.6, 'Power-to-Methanol / CCU System (MFA Mass Flow Diagram)',
        ha='center', fontsize=12, color='#7F8C8D', style='italic')

# ===================== 原料输入层 (y=20.5) =====================
draw_box(1.5, 20.5, 2.8, 1.0, '新鲜CO\u2082进料\n1423 kg/t\n(烟气MEA捕集)', C_INPUT)
draw_box(5.5, 20.5, 2.8, 1.0, '新鲜H\u2082进料\n198 kg/t\n(PEM电解水)', C_INPUT)
draw_box(10.0, 20.5, 2.8, 1.0, '电解水净补水\n1385 kg/t\n(除盐纯水)', C_WATER)

# ===================== PEM 电解槽 (y=18.5) =====================
draw_box(5.5, 18.5, 3.2, 1.0, 'PEM电解水制氢站\n10,296 kWh/t\n(130 MW PEM电解槽)', C_ENERGY)
arrow(5.5, 20.0, 5.5, 19.0, C_INPUT)
arrow(10.0, 20.0, 7.1, 18.8, C_WATER, label='总进水\n1960 kg/t')

# 副产O2
draw_box(10.5, 18.5, 2.5, 0.8, '副产工业O\u2082\n1584 kg/t\n(外售)', C_BYPRODUCT)
arrow(7.1, 18.5, 9.25, 18.5, C_BYPRODUCT)

# ===================== 混合器 (y=16.8) =====================
draw_box(3.5, 16.8, 2.2, 0.7, '气体混合器\n预热器', C_REACTOR)
arrow(1.5, 20.0, 3.0, 17.2, C_INPUT)
arrow(5.5, 18.0, 4.0, 17.2, C_INPUT)

# ===================== 甲醇合成反应器 (y=15.0) =====================
draw_box(3.5, 15.0, 3.5, 1.2, '甲醇合成反应器\nCu/ZnO/Al\u2082O\u2083催化剂\n250\u2103, 5.0 MPa\n单程转化率 25%', C_REACTOR)
arrow(3.5, 16.45, 3.5, 15.6, C_REACTOR)

# ===================== 高压气液分离器 (y=13.0) =====================
draw_box(3.5, 13.0, 3.2, 0.9, '高压气液分离器\n冷却冷凝至45\u2103\n4.8 MPa', C_REACTOR)
arrow(3.5, 14.4, 3.5, 13.45, C_REACTOR)

# ===================== 液相路径: 粗甲醇 → 精馏 → 产品 =====================
draw_box(3.5, 11.2, 2.8, 0.7, '粗甲醇液相\n1575 kg/t', C_PURPLE)
arrow(3.5, 12.55, 3.5, 11.55, C_PURPLE, label='液相', lo=(0.8, 0))

draw_box(3.5, 9.5, 3.0, 0.8, '双塔精馏提纯\n常压脱轻 + 加压脱水', C_REACTOR)
arrow(3.5, 10.85, 3.5, 9.9, C_REACTOR)

# 主产品
draw_box(3.5, 7.5, 3.2, 1.0, '★ 聚合级精甲醇\n1000 kg/t\n(纯度>99.85%)', C_PRODUCT)
arrow(3.5, 9.1, 3.5, 8.0, C_PRODUCT, label='产品', lo=(0.9, 0))

# 生成水 (副产)
draw_box(8.0, 9.5, 2.5, 0.7, '副产生成水\n575 kg/t', C_WATER)
arrow(5.0, 9.5, 6.75, 9.5, C_WATER)
# 回流箭头: 生成水 → 电解槽
ax.annotate('', xy=(10.0, 20.0), xytext=(9.25, 9.5),
            arrowprops=dict(arrowstyle='->', color=C_WATER, lw=2,
                          connectionstyle='arc3,rad=-0.4', shrinkA=5, shrinkB=5))
ax.text(12.5, 14.5, '微滤回流\n至电解槽\n575 kg/t', ha='center', fontsize=8,
        color=C_WATER, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor=C_WATER, alpha=0.8))

# ===================== 气相路径: 分离器 → 分流器 → 循环/驰放 =====================
draw_box(9.0, 13.0, 2.5, 0.7, '未冷凝气相\n4686 kg/t', C_REACTOR)
arrow(5.1, 13.0, 7.75, 13.0, C_REACTOR, label='气相', lo=(0, 0.3))

draw_box(9.0, 11.5, 2.5, 0.7, '循环气分流器\n99%循环 / 1%驰放', C_REACTOR)
arrow(9.0, 12.65, 9.0, 11.85, C_REACTOR)

# 循环压缩机 + 回路
draw_box(12.5, 15.0, 2.5, 0.8, '循环压缩机\n升压返回反应器', C_REACTOR)
arrow(10.25, 11.5, 12.5, 14.6, C_REACTOR, label='循环气 4640 kg/t\n(循环比3.8:1)',
      lo=(1.2, 0.5))
# 循环回混合器
ax.annotate('', xy=(4.6, 16.8), xytext=(12.5, 15.4),
            arrowprops=dict(arrowstyle='->', color=C_REACTOR, lw=2,
                          connectionstyle='arc3,rad=-0.15', shrinkA=5, shrinkB=5))
ax.text(8.5, 16.5, '返回混合器', ha='center', fontsize=8, color=C_REACTOR,
        fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor=C_REACTOR, alpha=0.8))

# 驰放气
draw_box(12.5, 11.0, 2.2, 0.7, '驰放废气\n46 kg/t\n(送锅炉供热)', C_WASTE)
arrow(10.25, 11.5, 11.4, 11.2, C_WASTE, label='驰放 1%', lo=(0.5, 0.3))

# ===================== 电力输入标注 =====================
draw_box(12.5, 18.5, 2.5, 0.8, '综合电耗\n10,826 kWh/t', C_ENERGY)
arrow(11.25, 18.5, 7.1, 18.5, C_ENERGY, label='', lo=(0, 0.3))

# ===================== 图例 =====================
legend_y = 5.5
ax.text(0.5, legend_y, '图例:', fontsize=11, fontweight='bold')
legend_items = [
    (C_INPUT, '原料输入'), (C_REACTOR, '工艺处理单元'),
    (C_PRODUCT, '主产品'), (C_BYPRODUCT, '副产品'),
    (C_WASTE, '废弃物/损耗'), (C_WATER, '水循环'),
    (C_ENERGY, '能量/电力'), (C_PURPLE, '中间产物'),
]
for i, (color, label) in enumerate(legend_items):
    x = 0.5 + (i % 4) * 3.2
    y = legend_y - 0.7 - (i // 4) * 0.6
    rect = mpatches.FancyBboxPatch((x - 0.3, y - 0.18), 0.6, 0.36,
                                    boxstyle="round,pad=0.05",
                                    facecolor=color + '40', edgecolor=color, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(x + 0.5, y, label, fontsize=9, va='center')

# ===================== 质量守恒标注 =====================
ax.text(7, 3.5, '质量守恒验证 (系统边界)',
        ha='center', fontsize=11, fontweight='bold', color='#2C3E50',
        bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='#2C3E50', alpha=0.9))
ax.text(7, 2.8, '输入: CO\u2082 1423 + H\u2082 198 + 净补水 1385 = 3006 kg/t',
        ha='center', fontsize=9, color='#555')
ax.text(7, 2.2, '输出: 甲醇 1000 + O\u2082 1584 + 生成水 575 + 驰放 46 = 3205 kg/t',
        ha='center', fontsize=9, color='#555')
ax.text(7, 1.6, '(注: 内部循环水 575 kg/t 在电解槽与精馏塔间闭环回流，不计入净输入)',
        ha='center', fontsize=8, color='#888', style='italic')

plt.tight_layout()
out_png = r"process_flow_diagram.png"
out_svg = r"process_flow_diagram.svg"
plt.savefig(out_png, dpi=300, bbox_inches='tight')
plt.savefig(out_svg, format='svg', bbox_inches='tight')
print(f"\n流程图已保存:")
print(f"  PNG: {out_png}")
print(f"  SVG: {out_svg}")
plt.show()

print("\n" + "=" * 70)
print("任务3 完成!")
print("=" * 70)
