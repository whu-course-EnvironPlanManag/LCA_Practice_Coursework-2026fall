# -*- coding: utf-8 -*-
"""
任务2：调用 Python 第三方包绘制"工艺物质流程图"（MFA 桑基图）
案例：废弃PET塑料瓶机械物理再生系统

使用 plotly 库绘制桑基图（Sankey Diagram）
作者: Group-04
日期: 2026-10-22
"""

import plotly.graph_objects as go
import os

# ============================================================
# MFA 物质流数据定义（基于1000kg废瓶砖输入）
# ============================================================

# 节点定义（按工艺流程顺序）
nodes = [
    # 输入节点 (0)
    "废旧PET瓶砖\n(1000 kg)",           # 0: 原料输入
    
    # 工段1: 拆包脱标 (1-3)
    "拆包脱标工段",                      # 1
    "废标签膜(PP/PVC)\n20 kg",          # 2
    "泥沙干灰渣\n25 kg",                # 3
    
    # 工段2: 热碱洗 (4-5)
    "热碱洗工段",                       # 4
    "洗涤废水(COD)\n35 kg",             # 5
    
    # 工段3: 密度浮选 (6-8)
    "密度浮选工段",                     # 6
    "HDPE瓶盖碎屑\n(损耗5 kg)",         # 7
    "回收HDPE颗粒\n75 kg",              # 8
    
    # 工段4: 光学色选 (9-10)
    "光学色选工段",                     # 9
    "杂色黄变切片\n40 kg",              # 10
    
    # 工段5: 挤出造粒 (11)
    "真空挤出造粒+SSP",                 # 11
    
    # 最终产品 (12)
    "瓶级rPET颗粒\n800 kg (主产品)"     # 12
]

# 定义颜色方案
node_colors = [
    "#4A90D9",  # 0: 原料 - 蓝色
    "#7FB3D5",  # 1: 拆包 - 浅蓝
    "#E74C3C",  # 2: 废标签 - 红色(废弃物)
    "#95A5A6",  # 3: 泥沙 - 灰色
    "#7FB3D5",  # 4: 热碱洗 - 浅蓝
    "#E67E22",  # 5: 废水 - 橙色
    "#7FB3D5",  # 6: 浮选 - 浅蓝
    "#E74C3C",  # 7: HDPE损耗 - 红色
    "#27AE60",  # 8: HDPE副产 - 绿色(副产品)
    "#7FB3D5",  # 9: 色选 - 浅蓝
    "#E74C3C",  # 10: 杂色切片 - 红色
    "#7FB3D5", # 11: 挤出造粒 - 浅蓝
    "#2ECC71"   # 12: 主产品 - 亮绿色
]

# 连接关系定义 (source, target, value)
# 基于工艺流程和质量平衡
links = [
    # 原料输入 → 拆包脱标
    (0, 1, 1000),   # 1000 kg 瓶砖进入拆包
    
    # 拆包脱标 → 各输出
    (1, 2, 20),     # 20 kg 废标签
    (1, 3, 25),     # 25 kg 泥沙
    (1, 4, 955),    # 955 kg 脱标瓶体进入热碱洗
    
    # 热碱洗 → 各输出
    (4, 5, 35),     # 35 kg 洗涤废水
    (4, 6, 920),    # 920 kg 洁净瓶片进入浮选
    
    # 密度浮选 → 各输出
    (6, 7, 5),      # 5 kg HDPE损耗入沉渣
    (6, 8, 75),     # 75 kg 回收HDPE颗粒
    (6, 9, 840),    # 840 kg PET瓶片进入色选
    
    # 光学色选 → 各输出
    (9, 10, 40),    # 40 kg 杂色黄变切片
    (9, 11, 800),   # 800 kg 洁净PET进入造粒
    
    # 挤出造粒 → 主产品
    (11, 12, 800),  # 800 kg rPET颗粒
]

# 分离 source, target, value
sources = [link[0] for link in links]
targets = [link[1] for link in links]
values = [link[2] for link in links]

# 连接颜色（与目标节点一致）
link_colors = []
for target in targets:
    if target in [2, 3, 5, 7, 10]:  # 废弃物节点
        link_colors.append("rgba(231, 76, 60, 0.3)")  # 红色半透明
    elif target == 8:  # HDPE副产品
        link_colors.append("rgba(39, 174, 96, 0.4)")  # 绿色半透明
    elif target == 12:  # 主产品
        link_colors.append("rgba(46, 204, 113, 0.5)")  # 亮绿色半透明
    else:
        link_colors.append("rgba(127, 179, 213, 0.4)")  # 蓝色半透明

# ============================================================
# 创建 Sankey 图
# ============================================================

fig = go.Figure(data=[go.Sankey(
    valueformat=".0f",
    valuesuffix=" kg",
    
    # 节点配置
    node=dict(
        pad=20,
        thickness=25,
        line=dict(color="black", width=0.5),
        label=nodes,
        color=node_colors,
        x=[0.05, 0.2, 0.35, 0.35, 0.4, 0.55, 0.55, 0.7, 0.7, 0.7, 0.85, 0.85, 0.95],
        y=[0.5, 0.5, 0.1, 0.9, 0.5, 0.1, 0.5, 0.15, 0.85, 0.5, 0.1, 0.5, 0.5]
    ),
    
    # 连接配置
    link=dict(
        source=sources,
        target=targets,
        value=values,
        color=link_colors,
        hovertemplate='物质流: %{value} kg<extra></extra>'
    )
)])

# ============================================================
# 图表布局与样式
# ============================================================

fig.update_layout(
    title=dict(
        text="<b>废弃PET塑料瓶机械物理再生系统 - 物质流分析(MFA)桑基图</b><br>" +
             "<sub>功能单位: 生产1000 kg瓶级rPET颗粒 | 主产品收率: 80%</sub>",
        font=dict(size=20),
        x=0.5,
        xanchor='center'
    ),
    font=dict(
        family="SimHei, Microsoft YaHei, Arial",
        size=12
    ),
    width=1400,
    height=800,
    margin=dict(l=50, r=50, t=100, b=50),
    
    # 添加注释
    annotations=[
        dict(
            text="<b>【输入】</b>",
            x=0.02, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=14, color="#4A90D9")
        ),
        dict(
            text="<b>【废弃物/损耗】</b>",
            x=0.5, y=0.02,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=12, color="#E74C3C")
        ),
        dict(
            text="<b>【副产品】</b>",
            x=0.75, y=0.95,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=12, color="#27AE60")
        ),
        dict(
            text="<b>【主产品】</b>",
            x=0.98, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=14, color="#2ECC71")
        ),
        dict(
            text="数据说明: 基于1000 kg废PET瓶砖输入的质量平衡核算<br>" +
                 "总输入 = 总输出 = 1000 kg (质量守恒)",
            x=0.5, y=-0.05,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=10, color="gray"),
            align="center"
        )
    ]
)

# ============================================================
# 保存输出
# ============================================================

# 获取当前脚本所在目录
output_dir = os.path.dirname(os.path.abspath(__file__))

# 保存为交互式HTML
html_path = os.path.join(output_dir, "mfa_sankey_diagram.html")
fig.write_html(html_path)
print(f"交互式HTML已保存: {html_path}")

# 保存为静态PNG图片 (需要kaleido库)
try:
    png_path = os.path.join(output_dir, "mfa_sankey_diagram.png")
    fig.write_image(png_path, scale=3, width=1400, height=800)
    print(f"高清PNG图片已保存: {png_path}")
except Exception as e:
    print(f"PNG导出需要安装kaleido库: pip install kaleido")
    print(f"错误信息: {e}")
    print("已保存为HTML格式，可用浏览器打开后截图")

# 保存为SVG矢量图
try:
    svg_path = os.path.join(output_dir, "mfa_sankey_diagram.svg")
    fig.write_image(svg_path, format="svg", width=1400, height=800)
    print(f"SVG矢量图已保存: {svg_path}")
except Exception as e:
    print(f"SVG导出需要安装kaleido库: pip install kaleido")

print("\n" + "=" * 60)
print("MFA桑基图绘制完成！")
print("=" * 60)
print("\n节点说明:")
print("  • 蓝色节点: 工艺处理工段")
print("  • 红色节点: 废弃物/损耗")
print("  • 绿色节点: 副产品和主产品")
print("\n流线宽度与物料通量成正比")
