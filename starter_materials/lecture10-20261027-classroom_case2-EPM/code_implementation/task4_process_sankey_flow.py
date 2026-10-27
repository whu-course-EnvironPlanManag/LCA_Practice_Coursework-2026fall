# -*- coding: utf-8 -*-
"""\n课程名称：《环境规划与管理》\n案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统\n任务编号：任务 4（学生随堂实训版）\n脚本名称：task4_process_sankey_flow.py\n功能描述：\n  基于任务 3 求解出的帕累托拐点（锚点 B）工程通量基准数据，绘制工业园区\n  10 万吨/年绿色甲醇系统物质流（MFA）与能量流（EFA）全流程拓扑图 (figures_output/fig1_mfa_process_flow.png)。\n  包含：\n    1. 物质流向与质量通量 (万吨/年)；\n    2. 未反应气内循环闭环回路 (46.40 万吨/年)；\n    3. 精馏冷凝生成水闭环循环至制氢进水池 (5.75 万吨/年)；\n    4. 各工段综合电耗分布 (亿 kWh/年)；\n    5. 出版级 300 DPI 矢量渲染输出。\n"""

import sys
import io
import os

# 针对 Windows 控制台编码环境进行 UTF-8 容错封装
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import matplotlib.pyplot as plt
import matplotlib.patches as patches

# 统一中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False


def get_figures_output_dir():
    """跨层级定位 figures_output 目录，确保脚本从任意工作路径均能正确定位"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "..", "figures_output"),
        os.path.join("figures_output"),
        os.path.join("..", "figures_output")
    ]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            continue
    return "."


# ==============================================================================
# TODO: [学生可视化实训任务 4] 园区级工艺物质与能量流动拓扑图绘制
# 实训要求：
#   1. 提取帕累托拐点（锚点 B，f_green=1.0, r_purge=0.0216）的 10 万吨/年工程规划通量数据；
#   2. 编写可视化绘图程序，清晰表达碳捕集、绿电制氢、催化合成、双塔精馏各工段的物料通量与综合电耗分布；
#   3. 明确标识未反应气闭环内循环流与精馏副产生成水回用流；
#   4. 输出 300 DPI 高清拓扑图至 figures_output/fig1_mfa_process_flow.png。
# ==============================================================================

def draw_mfa_process_flow(output_filename="fig1_mfa_process_flow.png"):
    """\n    绘制园区级 10 万吨/年绿色甲醇工程物质与能量流动拓扑图（MFA-EFA）。\n    风格：SCI 期刊插图 / 莫兰迪低饱和度配色 / 矢量风 / 无阴影。\n    所有文本、数值、箭头走向严格保留，不做任何删减。\n    """
    import matplotlib.patches as patches

    out_dir = get_figures_output_dir()
    output_path = os.path.join(out_dir, output_filename)

    # ========== 画布：大幅面 + 精细坐标 ==========
    fig, ax = plt.subplots(figsize=(22, 13), dpi=300, facecolor="white")
    fig.subplots_adjust(left=0.015, right=0.985, top=0.97, bottom=0.02)
    ax.set_xlim(-4, 104)
    ax.set_ylim(-3, 104)
    ax.axis("off")
    ax.set_facecolor("white")

    # ========== 莫兰迪低饱和度配色 ==========
    MORANDI = {
        "edge":    "#8a8f95",   # 模块描边（细灰）
        "text":    "#2c3e50",   # 主文字
        "sub":     "#6b7a8a",   # 副文字
        "co2":     "#b8876b",   # 暖棕（碳源）
        "h2":      "#7fa27f",   # 灰绿（绿氢）
        "water":   "#7d9ab5",   # 灰蓝（水）
        "meoh":    "#9a7fa6",   # 灰紫（甲醇产品）
        "gas_loop":"#6ea0a0",   # 灰青（循环气）
        "purge":   "#c27878",   # 灰红（弛放废气）
        "o2":      "#85b3a0",   # 灰青绿（副产氧）
        "elec":    "#a37d5a",   # 电耗标签（暖棕）
        "panel":   "#f5f6f7",   # 面板填充
    }

    # ========== 辅助函数 ==========
    def draw_unit(x, y, w, h, title, subtitle="", elec_str="", face="#ffffff"):
        rect = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.0",
            facecolor=face, edgecolor=MORANDI["edge"], linewidth=1.3, zorder=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.75, title,
                fontsize=11.0, fontweight="bold", ha="center", va="center",
                color=MORANDI["text"], zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.48, subtitle,
                    fontsize=9.0, ha="center", va="center",
                    color=MORANDI["sub"], zorder=3)
        if elec_str:
            ax.text(x + w / 2, y + h * 0.22, elec_str,
                    fontsize=8.5, fontweight="semibold", ha="center", va="center",
                    color=MORANDI["elec"], zorder=3)

    def arrow(x0, y0, x1, y1, label="", color="#444444", width=1.8, rad=0.0,
              lx=None, ly=None):
        style = f"Simple,tail_width={width},head_width={width*2.6},head_length={width*2.2}"
        kw = dict(arrowstyle=style, color=color, zorder=4)
        cs = f"arc3,rad={rad}" if rad != 0 else None
        arr = patches.FancyArrowPatch((x0, y0), (x1, y1),
                                      connectionstyle=cs, **kw) if cs               else patches.FancyArrowPatch((x0, y0), (x1, y1), **kw)
        ax.add_patch(arr)
        if label:
            if lx is None: lx = (x0 + x1) / 2
            if ly is None: ly = (y0 + y1) / 2
            ax.text(lx, ly, label, fontsize=8.8, fontweight="bold",
                    ha="center", va="center", color=color, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                              edgecolor="white", linewidth=0.4, alpha=0.98))

    # ========== 标题栏 ==========
    ax.text(50, 98.2, "工业园区 10 万吨/年二氧化碳加氢制绿色甲醇系统物质与能量流向拓扑图 (MFA-EFA)",
            fontsize=16, fontweight="bold", ha="center", va="center",
            color=MORANDI["text"])
    ax.text(50, 95.8,
            "年运行基准：8,000 h  |  聚合级精甲醇产能：100,000 t/a  |  全厂综合电耗：10.826 亿 kWh/a  |  总碳转化利用率：96.0%",
            fontsize=11.5, ha="center", va="center", color=MORANDI["sub"])

    # ========== 核心单元布局（重新规划坐标，每个单元独立呼吸空间）==========
    # 行 1（上部）：CO2 捕集
    draw_unit(3, 73, 20, 14,
              "烟气 CO2 捕集与压缩单元",
              "MEA 化学吸收 + 三级压缩 (5.0 MPa)",
              "电耗: 0.255 亿 kWh/a (2.36%)",
              face="#f7f1ec")

    # 行 1（中部）：反应链左→右（分散间距）
    draw_unit(33, 60, 14, 14,
              "反应进料混合预热器",
              "新进料与循环气深度混合\n230 ℃, 5.0 MPa", "",
              face="#f4f1f8")
    draw_unit(52, 60, 15, 15,
              "固定床甲醇合成反应器",
              "Cu/ZnO/Al₂O₃ 催化剂\n250 ℃, 5.0 MPa, 单程转化率 25%",
              "副产中压蒸汽回供再沸器",
              face="#f3f0f7")
    draw_unit(73, 60, 14, 15,
              "冷凝分离与循环分流器",
              "气液闪蒸冷凝分离器\n循环比 3.8:1, 驰放比 1.0%",
              "循环压缩电耗: 0.155 亿 kWh/a",
              face="#f3f0f7")

    # 行 2（下部左）：PEM 电解槽
    draw_unit(3, 33, 20, 18,
              "130 MW PEM 电解水制氢站",
              "质子交换膜电解槽阵列 (3.0 MPa)",
              "电耗: 10.296 亿 kWh/a (95.10%)",
              face="#eef4ee")

    # 行 2（下部右）：精馏
    draw_unit(73, 16, 14, 15,
              "双塔精馏分离系统",
              "常压脱轻塔 + 加压脱水精馏塔\n甲醇纯度 ≥ 99.85 wt%",
              "脱水精馏电耗: 0.120 亿 kWh/a",
              face="#f0ecf3")

    # ========== 物质流箭头（每条独立坐标，标签不重叠）==========
    # ① 原料烟气 CO2 → 捕集单元（左入口）
    arrow(-2, 80, 3, 80,
          "原料烟气 CO2 捕集\n14.23 万吨/a (100%)",
          color=MORANDI["co2"], width=2.2, ly=84.5)

    # ② 捕集单元 → 混合器（斜下）
    arrow(23, 77, 33, 67,
          "高纯 CO2 气体: 14.23 万吨/a",
          color=MORANDI["co2"], width=2.0, lx=26, ly=74)

    # ③ 新鲜脱盐纯水 → 电解槽（左入口）
    arrow(-2, 42, 3, 42,
          "新鲜脱盐纯水补水\n13.85 万吨/a (70.7%)",
          color=MORANDI["water"], width=2.0, ly=46.5)

    # ④ 电解槽 → 混合器（斜上）
    arrow(23, 40, 33, 63,
          "电解高纯绿氢: 1.98 万吨/a",
          color=MORANDI["h2"], width=2.0, lx=25, ly=48)

    # ⑤ 混合器 → 反应器（水平）
    arrow(47, 67, 52, 67,
          "反应器入口混合气\n62.61 万吨/a",
          color=MORANDI["text"], width=2.8, ly=72)

    # ⑥ 反应器 → 分离器（水平）
    arrow(67, 67, 73, 67,
          "反应出口生成物\n62.61 万吨/a",
          color=MORANDI["text"], width=2.8, ly=72)

    # ⑦ 分离器 → 弛放废气（右上旁路）
    arrow(80, 73, 95, 83,
          "驰放废气 (1.0% 排放至供热锅炉)\n0.46 万吨/a (全流程碳损耗 4.0%)",
          color=MORANDI["purge"], width=1.3, rad=0.20, lx=90, ly=86)

    # ⑧ 分离器 → 精馏塔（垂直下）
    arrow(80, 60, 80, 31,
          "粗甲醇液体\n15.75 万吨/a",
          color=MORANDI["meoh"], width=2.4, lx=88, ly=46)

    # ⑨ 精馏塔 → 产品输出（右出口）
    arrow(87, 23, 102, 23,
          "目标产品：聚合级精甲醇\n10.00 万吨/a (纯度 ≥ 99.85%)",
          color=MORANDI["meoh"], width=2.6, ly=27.5)

    # ⑩ 分离器顶部 → 混合器顶部（循环回路，大弧度）
    arrow(80, 75, 40, 74,
          "分离器顶部未反应气循环流 (99.0% 回流)\n46.40 万吨/a (循环比 3.8:1)",
          color=MORANDI["gas_loop"], width=2.4, rad=0.30, lx=60, ly=83)

    # ⑪ 电解槽阳极 → 副产氧气外售（左旁路，向下）
    arrow(3, 37, -2, 14,
          "阳极副产高纯氧气 (外售)\n15.84 万吨/a",
          color=MORANDI["o2"], width=2.0, rad=-0.30, lx=-1.5, ly=26)

    # ⑫ 精馏塔釜 → 电解槽（闭环水循环，大弧度绕过右侧）
    arrow(73, 22, 23, 36,
          "精馏塔釜副产生成水 (100% 闭环回流至制氢池)\n5.75 万吨/a (削减园区新鲜水消耗 29.3%)",
          color=MORANDI["water"], width=1.8, rad=-0.18, lx=48, ly=12)

    # ========== 电解槽总进水标注（独立浮动框，不与箭头重叠）==========
    ax.text(13, 30,
            "PEM 电解槽总进水\n19.60 万吨/a (100%)\n[净补水 70.7% + 回用水 29.3%]",
            fontsize=8.8, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#e6eef5",
                      edgecolor=MORANDI["water"], linewidth=1.0, alpha=0.95),
            color=MORANDI["water"], zorder=6)

    # ========== 底部关键工程指标看板（横向两行，不再 4 列挤一行）==========
    board_rect = patches.FancyBboxPatch(
        (2, -2), 96, 16, boxstyle="round,pad=0.5,rounding_size=1.0",
        facecolor=MORANDI["panel"], edgecolor=MORANDI["edge"], linewidth=1.0, zorder=2
    )
    ax.add_patch(board_rect)

    ax.text(50, 12.5, "【关键规划工程指标对齐汇总 (10 万吨/年规模)】",
            fontsize=10.5, fontweight="bold", ha="center", va="center",
            color=MORANDI["text"])

    # 第一行：原料 / 能量指标
    ax.text(6, 7.5,
            "原料捕集需求：高纯 CO₂ 14.23 万吨/年 (1.423 t/t)\n绿氢原料需求：高纯绿氢 1.98 万吨/年 (0.198 t/t)",
            fontsize=9.2, ha="left", va="center", color=MORANDI["sub"])
    ax.text(38, 7.5,
            "水资源循环率：精馏水回用 5.75 万吨/年 (节水 29.3%)\n净除盐水消耗：13.85 万吨/年 (吨水指标 1.385 t/t)",
            fontsize=9.2, ha="left", va="center", color=MORANDI["sub"])
    ax.text(70, 7.5,
            "全系统总碳利用率：96.0% (驰放碳损耗 4.0%)\n副产工业高纯纯氧：外售量 15.84 万吨/年 (1.584 t/t)",
            fontsize=9.2, ha="left", va="center", color=MORANDI["sub"])

    # 第二行：能量 / 系统集成
    ax.text(50, 1.5,
            "全厂年用电负荷：10.826 亿 kWh/年 (制氢占比 95.1%)     |     "
            "热力学耦合集成：反应副产蒸汽回用碳捕集再沸器",
            fontsize=9.2, ha="center", va="center", color=MORANDI["sub"])

    # ========== 保存 ==========
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[成功] 工艺物质能量流向拓扑图已保存至: {output_path}")

if __name__ == "__main__":
    draw_mfa_process_flow()
