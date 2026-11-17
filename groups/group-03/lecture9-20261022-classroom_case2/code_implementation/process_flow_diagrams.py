"""
========================================================================
Case2 任务 3: 绿色甲醇合成工艺流程图
========================================================================
- Part A: matplotlib 绘制工艺方框图 BFD (含循环回路 Recycle Loop)
- Part B: plotly 绘制 MFA 质量流桑基图 Sankey
========================================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = Path(__file__).parent
DATA_DIR   = Path(__file__).parent.parent / "case_files" / "data_cohort"

print("=" * 70)
print("【Case2 任务 3】工艺流程图绘制")
print("=" * 70)

# ===================== 读取 MFA 数据 =====================
df = pd.read_csv(DATA_DIR / "mfa_reaction_recycle_balance.csv")
print(f"✅ 已加载 {len(df)} 条物料流数据")

# 提取流股数据方便引用
S = {row.stream_id: row for _, row in df.iterrows()}

# ============================================================
# Part A: matplotlib BFD 方框图 (含循环回路)
# ============================================================
print("\n--- Part A: 工艺方框图 BFD ---")

def draw_bfd():
    fig, ax = plt.subplots(1, 1, figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title(
        "绿色甲醇合成工艺流程图 (BFD)\n"
        "CO₂ 捕集 + PEM 电解绿氢 → 甲醇合成 → 循环回路",
        fontsize=16, fontweight='bold', pad=20
    )

    # ---------- 样式 ----------
    box_blue   = dict(facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2)
    box_orange = dict(facecolor='#FFF3E0', edgecolor='#E65100', linewidth=2)
    box_green  = dict(facecolor='#E8F5E9', edgecolor='#2E7D32', linewidth=2)
    box_pink   = dict(facecolor='#FCE4EC', edgecolor='#AD1457', linewidth=2)

    def box(x, y, text, style, fs=9):
        ax.text(x, y, text, ha='center', va='center', fontsize=fs,
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4', **style))

    def arrow(x1, y1, x2, y2, color='#333', lw=2, curve=None):
        if curve:
            ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                        connectionstyle=f'arc3,rad={curve}'))
        else:
            ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle='->', color=color, lw=lw))

    # ---------- 节点 ----------
    # 输入
    box(1.2, 7.2, '新鲜 CO₂ 进料\n1423 kg', box_orange)
    box(1.2, 4.8, '新鲜 PEM 绿氢\n198 kg', box_orange)
    box(1.2, 2.2, '净外购除盐水\n1385 kg', box_orange)

    # 混合器
    box(3.8, 6.0, '气体混合器\n预热', box_blue)

    # 反应器
    box(6.5, 6.0, '固定床甲醇合成反应器\n(Cu/ZnO/Al₂O₃, 250℃, 5 MPa)\n单程转化率 25%', box_green, fs=8)

    # 冷却分离器
    box(9.5, 6.0, '冷却冷凝器\n高压气液分离器', box_blue)

    # 分流器
    box(11.8, 6.8, '循环气分流器\n99%循环 / 1%驰放', box_blue)

    # 驰放废气
    box(14.2, 8.2, '驰放废气 → 锅炉\n46 kg', box_pink)

    # 精馏塔
    box(11.8, 3.8, '双塔精馏\n提纯系统', box_blue)

    # 产品
    box(14.2, 2.2, '聚合级精甲醇\n1000 kg\n>99.85%', box_green)

    # 副产物
    box(6.5, 2.2, '副产工业氧气\n1584 kg (外售)', box_orange)

    # 生成水回流
    box(9.5, 2.2, '生成水 575 kg\n(回流电解槽)', box_orange)

    # PEM 电解槽 (隐藏在 H2 后面，虚线框)
    box(3.8, 3.5, 'PEM 电解槽\n(绿氢来源)', box_pink, fs=8)

    # ---------- 连线 ----------
    # CO2 → Mix
    arrow(2.3, 7.2, 2.9, 6.0)
    # H2 → Mix (经过 PEM)
    arrow(2.3, 4.8, 2.9, 4.2, curve=-0.2)
    arrow(2.9, 4.2, 2.9, 6.0)

    # Mix → 反应器
    arrow(4.9, 6.0, 5.4, 6.0)

    # 反应器 → 分离器
    arrow(7.6, 6.0, 8.4, 6.0)

    # 分离器 → 分流器 (顶部气)
    arrow(10.6, 6.2, 10.9, 6.8)

    # 分流器 → 驰放
    arrow(12.9, 7.2, 13.4, 8.0)

    # 分流器 → 循环 (关键！循环回路)
    arrow(11.8, 7.8, 11.8, 9.2, curve=0.15)
    arrow(11.8, 9.2, 3.8, 9.2, curve=0.1)
    arrow(3.8, 9.2, 3.8, 6.8, curve=0.1)
    arrow(3.8, 6.8, 4.2, 6.2, curve=-0.1)
    # 循环标注
    ax.text(7.5, 9.5, '循环气 4640 kg\n(循环比 2.86:1)', ha='center', fontsize=9,
            color='#E65100', fontweight='bold')

    # 分离器 → 精馏 (底部液相)
    arrow(9.5, 4.8, 11.0, 3.8)

    # 精馏 → 产品
    arrow(12.9, 3.8, 13.4, 2.5)

    # 精馏底部 → 生成水回流
    arrow(11.8, 3.2, 10.0, 2.4)

    # PEM 副产 O2
    arrow(3.8, 2.8, 5.5, 2.3)

    # 净补水 → PEM
    arrow(2.3, 2.2, 2.9, 3.2, curve=0.1)

    # ---------- 图例 ----------
    legend_elements = [
        mpatches.Patch(**box_orange, label='进料/副产'),
        mpatches.Patch(**box_blue,   label='分离/换热'),
        mpatches.Patch(**box_green,  label='反应器/产品'),
        mpatches.Patch(**box_pink,   label='驰放/损失'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10, framealpha=0.9)

    plt.tight_layout()
    out = OUTPUT_DIR / "process_bfd_matplotlib.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ BFD 已保存: {out}")

draw_bfd()

# ============================================================
# Part B: plotly 桑基图
# ============================================================
print("\n--- Part B: MFA 质量流桑基图 ---")

def draw_sankey():
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("⚠️  plotly 未安装, 跳过 Sankey。请先 pip install plotly")
        return None

    # 定义节点和流
    # 节点索引
    nodes = [
        dict(name='新鲜 CO₂ (S01)',     color='#FF9800'),  # 0
        dict(name='新鲜 H₂ (S02)',      color='#FF9800'),  # 1
        dict(name='净外购水 (S03)',     color='#FF9800'),  # 2
        dict(name='循环气 (S06)',       color='#2196F3'),  # 3
        dict(name='气体混合器 (S07)',   color='#2196F3'),  # 4
        dict(name='反应器 (S08)',       color='#4CAF50'),  # 5
        dict(name='分离器顶 (S10)',     color='#2196F3'),  # 6
        dict(name='分离器底 (S09)',     color='#2196F3'),  # 7
        dict(name='驰放气 (S11)',       color='#F44336'),  # 8
        dict(name='精馏 (S12/S13)',     color='#2196F3'),  # 9
        dict(name='精甲醇产品',          color='#4CAF50'),  # 10
        dict(name='生成水回流',          color='#9C27B0'),  # 11
        dict(name='副产 O₂ (S05)',      color='#FF9800'),  # 12
    ]

    # 连接 (source → target, value = kg)
    flows = [
        # 进料 → 混合
        dict(source=0, target=4, value=S['S01'].mass_flow_per_ton_product_kg),
        dict(source=1, target=4, value=S['S02'].mass_flow_per_ton_product_kg),
        # 循环 → 混合
        dict(source=3, target=4, value=S['S06'].mass_flow_per_ton_product_kg),
        # 混合 → 反应器
        dict(source=4, target=5, value=S['S07'].mass_flow_per_ton_product_kg),
        # 反应器 → 分离器
        dict(source=5, target=6, value=S['S08'].mass_flow_per_ton_product_kg * 0.749),  # 74.9% 气相
        dict(source=5, target=7, value=S['S09'].mass_flow_per_ton_product_kg),
        # 分离器顶 → 循环/驰放
        dict(source=6, target=3, value=S['S06'].mass_flow_per_ton_product_kg),
        dict(source=6, target=8, value=S['S11'].mass_flow_per_ton_product_kg),
        # 分离器底 → 精馏
        dict(source=7, target=9, value=S['S09'].mass_flow_per_ton_product_kg),
        # 精馏 → 产品
        dict(source=9, target=10, value=S['S12'].mass_flow_per_ton_product_kg),
        # 精馏 → 生成水回流
        dict(source=9, target=11, value=S['S13'].mass_flow_per_ton_product_kg),
        # 净补水 + H2O回流 → PEM (简化: 并入 H2 源)
        # 副产 O2 流出系统 (来自 PEM, 简化为 H2 的副产)
        dict(source=1, target=12, value=S['S05'].mass_flow_per_ton_product_kg),
        dict(source=2, target=1, value=S['S03'].mass_flow_per_ton_product_kg),
    ]

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=15, thickness=25, line=dict(color='black', width=0.5),
            label=[n['name'] for n in nodes],
            color=[n['color'] for n in nodes],
        ),
        link=dict(
            source=[f['source'] for f in flows],
            target=[f['target'] for f in flows],
            value=[f['value'] for f in flows],
            color='rgba(100,100,100,0.4)',
        ),
    )])

    fig.update_layout(
        title=dict(
            text='绿色甲醇合成 MFA 桑基图 (kg/吨精甲醇)',
            font=dict(size=18),
        ),
        font=dict(size=12),
        height=700,
        width=1400,
    )

    out_html = OUTPUT_DIR / "process_sankey.html"
    out_png  = OUTPUT_DIR / "process_sankey.png"
    fig.write_html(out_html)
    try:
        fig.write_image(out_png, scale=2)
        print(f"✅ Sankey 图已保存: {out_png}")
    except Exception as e:
        print(f"⚠️  Sankey PNG 保存失败 ({e}), 但 HTML 可打开查看")
    print(f"✅ Sankey HTML 已保存: {out_html}")

draw_sankey()

print("\n" + "=" * 70)
print("🎯 任务 3 完成!")
print("=" * 70)