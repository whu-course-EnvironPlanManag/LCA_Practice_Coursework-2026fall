# -*- coding: utf-8 -*-
"""
《环境规划与管理》第十讲实训任务
作者：帕娜尔·阿克木 (Group 02)
任务：工艺流程物质流与能量流拓扑图绘制

功能说明：
  绘制任务 1 工程流量基准下的 MFA-EFA 全流程拓扑图，并单独标注任务 3 锚点 B 参数。

设计特色：
  - 竖向卡片式布局，主工艺链自上而下
  - 蓝绿主题配色，区分输入/循环/输出物流
  - 底部工程指标汇总看板
"""

import sys
import io
import os

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from task1_mfa_recycle_solver import calculate_mass_balance, scale_to_plant_capacity

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def ensure_output_directory():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "..", "figures_output"),
        os.path.join("figures_output"),
        os.path.join("..", "figures_output")
    ]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except:
            continue
    return "."


# ==============================================================================
# 配色方案 (深蓝+翠绿 专业主题)
# ==============================================================================
C = {
    "bg": "#FFFFFF",
    "title_bar": "#0D2137",
    "title_text": "#0D2137",
    "subtitle": "#4A6785",

    "card_input": "#E8F5E9",
    "card_input_edge": "#2E7D32",
    "card_core": "#E3F2FD",
    "card_core_edge": "#1565C0",
    "card_sep": "#FFF3E0",
    "card_sep_edge": "#E65100",
    "card_product": "#F3E5F5",
    "card_product_edge": "#6A1B9A",

    "flow_co2": "#BF360C",
    "flow_h2": "#1B5E20",
    "flow_meoh": "#4A148C",
    "flow_recycle": "#006064",
    "flow_water": "#01579B",
    "flow_waste": "#B71C1C",
    "flow_main": "#263238",
    "flow_o2": "#33691E",

    "energy_fill": "#FFF8E1",
    "energy_edge": "#F57F17",
    "energy_text": "#E65100",

    "badge_green": "#E8F5E9",
    "badge_green_edge": "#43A047",

    "summary_bg": "#F5F7FA",
    "summary_edge": "#90A4AE",
    "grid_line": "#CFD8DC",
}


# ==============================================================================
# 辅助绘图函数
# ==============================================================================
def draw_process_card(ax, x, y, w, h, title, detail_lines, card_type="core",
                      energy_text="", icon_text=""):
    """绘制带阴影和图标的工艺单元卡片"""
    colors = {
        "input": (C["card_input"], C["card_input_edge"]),
        "core": (C["card_core"], C["card_core_edge"]),
        "sep": (C["card_sep"], C["card_sep_edge"]),
        "product": (C["card_product"], C["card_product_edge"]),
    }
    fill, edge = colors.get(card_type, colors["core"])

    # 阴影
    shadow = FancyBboxPatch(
        (x + 0.3, y - 0.3), w, h,
        boxstyle="round,pad=0.2,rounding_size=1.0",
        facecolor="#000000", edgecolor="none", alpha=0.06, zorder=1
    )
    ax.add_patch(shadow)

    # 卡片主体
    card = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.2,rounding_size=1.0",
        facecolor=fill, edgecolor=edge, linewidth=1.8, zorder=2
    )
    ax.add_patch(card)

    # 顶部色带
    top_bar = FancyBboxPatch(
        (x, y + h - 2.2), w, 2.2,
        boxstyle="round,pad=0.1,rounding_size=0.8",
        facecolor=edge, edgecolor="none", alpha=0.85, zorder=3
    )
    ax.add_patch(top_bar)

    # 图标
    if icon_text:
        ax.text(x + 2.0, y + h - 1.1, icon_text,
                fontsize=11, ha="center", va="center", color="white",
                fontweight="bold", zorder=4)

    # 标题
    title_x = x + w / 2 + (1.0 if icon_text else 0)
    ax.text(title_x, y + h - 1.1, title,
            fontsize=10.5, fontweight="bold", ha="center", va="center",
            color="white", zorder=4)

    # 详情文字
    for i, line in enumerate(detail_lines):
        dy = y + h - 4.0 - i * 2.2
        ax.text(x + w / 2, dy, line,
                fontsize=7.8, ha="center", va="center",
                color=C["title_text"], zorder=4, alpha=0.85)

    # 能耗标签
    if energy_text:
        ey = y + 1.5
        badge = FancyBboxPatch(
            (x + w * 0.12, ey - 0.9), w * 0.76, 1.8,
            boxstyle="round,pad=0.15,rounding_size=0.5",
            facecolor=C["energy_fill"], edgecolor=C["energy_edge"],
            linewidth=0.8, zorder=4
        )
        ax.add_patch(badge)
        ax.text(x + w / 2, ey, energy_text,
                fontsize=7.2, fontweight="bold", ha="center", va="center",
                color=C["energy_text"], zorder=5)


def draw_flow_arrow(ax, x1, y1, x2, y2, label="", color="#333", width=2.0,
                    curve=0.0, label_offset=(0, 2.0), label_bg=True, fontsize=7.8):
    """绘制带标注的物流箭头"""
    style = f"Simple,tail_width={width},head_width={width * 2.8},head_length={width * 2.2}"
    if curve != 0.0:
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            connectionstyle=f"arc3,rad={curve}",
            arrowstyle=style, color=color, zorder=4
        )
    else:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                arrowstyle=style, color=color, zorder=4)
    ax.add_patch(arrow)

    if label:
        lx = x1 + (x2 - x1) * 0.5 + label_offset[0]
        ly = y1 + (y2 - y1) * 0.5 + label_offset[1]
        bbox_kw = {}
        if label_bg:
            bbox_kw = dict(boxstyle="round,pad=0.18", facecolor="white",
                           edgecolor=color, linewidth=0.5, alpha=0.92)
        ax.text(lx, ly, label,
                fontsize=fontsize, fontweight="bold", ha="center", va="center",
                bbox=bbox_kw, color=color, zorder=6)


# ==============================================================================
# 主绘图函数
# ==============================================================================
def draw_process_flow_diagram(output_filename="fig1_mfa_process_flow.png"):
    out_dir = ensure_output_directory()
    output_path = os.path.join(out_dir, output_filename)
    balance = calculate_mass_balance()
    annual = scale_to_plant_capacity(balance, annual_capacity=100000)
    annual_co2_wan = annual["co2_capture"]
    annual_h2_wan = annual["h2_production"]
    annual_meoh_wan = annual["meoh_production"]
    annual_purge_t = annual["purge_gas"] * 10000
    separator_offgas = balance["m_gas_recycle"] + balance["m_gas_purge"]
    recycle_pct = balance["m_gas_recycle"] / separator_offgas * 100
    purge_pct = balance["m_gas_purge"] / separator_offgas * 100

    fig, ax = plt.subplots(figsize=(16, 18), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor(C["bg"])

    # ---- 标题区 (带装饰线) ----
    title_bar = FancyBboxPatch(
        (2, 94.5), 96, 4.5,
        boxstyle="round,pad=0.2,rounding_size=0.8",
        facecolor=C["title_bar"], edgecolor="none", zorder=2
    )
    ax.add_patch(title_bar)
    ax.text(50, 97.2,
            "工业园区 CO2 加氢制绿色甲醇系统",
            fontsize=17, fontweight="bold", ha="center", va="center",
            color="white", zorder=3)
    ax.text(50, 95.4,
            "物质流与能量流拓扑图 (MFA-EFA)  |  产能 10 万吨/年  |  Task 1 工程流量基准  |  全厂用电 10.826 亿 kWh/年",
            fontsize=9.0, ha="center", va="center", color="#B0BEC5", zorder=3)

    # ---- 六大工艺单元卡片 ----
    # 第一行：碳捕集 + 电解制氢
    draw_process_card(ax, 4, 77, 30, 13,
                      "CO2 捕集压缩单元",
                      ["MEA 吸收 + 三级压缩至 5.0 MPa",
                       f"新鲜 CO2 {annual_co2_wan:.2f} 万吨/年"],
                      card_type="input",
                      energy_text="0.255 亿 kWh/年  ·  2.4%",
                      icon_text="1")

    draw_process_card(ax, 66, 77, 30, 13,
                      "130 MW PEM 电解水制氢站",
                      ["质子交换膜电解槽阵列 (3.0 MPa)",
                       f"净水 {annual['water_consumption']:.2f} + 回用水 {annual['water_recycled']:.2f} 万吨/年"],
                      card_type="input",
                      energy_text="10.296 亿 kWh/年  ·  95.1%",
                      icon_text="2")

    # 第二行：混合预热 + 合成反应器
    draw_process_card(ax, 4, 55, 30, 13,
                      "反应进料混合预热器",
                      ["新鲜 CO2/H2 与循环气混合",
                       "预热至 230 °C；5.0 MPa"],
                      card_type="core",
                      icon_text="3")

    draw_process_card(ax, 66, 55, 30, 13,
                      "固定床甲醇合成反应器",
                      ["Cu/ZnO/Al2O3 催化剂；250 °C",
                       "单程转化率 25%；放热反应"],
                      card_type="core",
                      energy_text="副产中压蒸汽 (回用)",
                      icon_text="4")

    # 第三行：冷凝分离 + 双塔精馏
    draw_process_card(ax, 4, 33, 30, 13,
                      "冷凝分离与循环分流器",
                      ["高压气液闪蒸分离器",
                       "回流/驰放按 Task 1 工程流量计算"],
                      card_type="sep",
                      energy_text="",
                      icon_text="5")

    draw_process_card(ax, 66, 33, 30, 13,
                      "双塔精馏分离系统",
                      ["常压脱轻塔 + 加压脱水精馏塔",
                       "产品纯度 ≥99.85 wt%"],
                      card_type="product",
                      energy_text="0.120 亿 kWh/年  ·  1.1%",
                      icon_text="6")

    # ---- 外部输入物流 ----
    draw_flow_arrow(ax, -2, 86, 4, 86,
                    label=f"烟气 CO2\n{annual_co2_wan:.2f} 万吨/年",
                    color=C["flow_co2"], width=2.5, label_offset=(0, 3.0), fontsize=7.5)

    draw_flow_arrow(ax, 60, 69, 66, 78,
                    label=f"净水 {annual['water_consumption']:.2f} 万吨/年",
                    color=C["flow_water"], width=2.0, label_offset=(-6, 3), fontsize=7.0)

    # ---- 单元间主物流连接 ----
    # CO2捕集 -> 混合预热器
    draw_flow_arrow(ax, 19, 77, 19, 68,
                    label=f"CO2 {balance['m_co2_fresh']:.0f} kg/t",
                    color=C["flow_co2"], width=2.2, label_offset=(-7.5, 0))

    # 电解制氢 -> 混合预热器 (跨越)
    draw_flow_arrow(ax, 66, 83, 34, 63,
                    label=f"电解绿 H2：{annual_h2_wan:.2f} 万吨/年",
                    color=C["flow_h2"], width=2.2, curve=0.22, label_offset=(0, -3.0))

    # 混合预热器 -> 合成反应器
    reactor_feed = (
        balance["m_co2_fresh"] + balance["m_h2_fresh"] + balance["m_gas_recycle"]
    )
    draw_flow_arrow(ax, 34, 61.5, 66, 61.5,
                    label=f"反应器进料 {reactor_feed:,.0f} kg/t  ({reactor_feed / 10:,.2f} 万吨/年)",
                    color=C["flow_main"], width=3.0, label_offset=(0, 2.8))

    # 合成反应器 -> 冷凝分离器
    draw_flow_arrow(ax, 66, 61.5, 34, 39,
                    label=f"反应器出口 {reactor_feed:,.0f} kg/t\n含甲醇、水、未反应气及惰性组分",
                    color=C["flow_main"], width=3.0, curve=-0.15,
                    label_offset=(0, 3.0), fontsize=7.2)

    # 冷凝分离器 -> 精馏塔
    crude_methanol = 1575.0
    draw_flow_arrow(ax, 34, 39, 66, 39,
                    label=f"粗甲醇液相 {crude_methanol:,.0f} kg/t  ({crude_methanol / 10:,.2f} 万吨/年)",
                    color=C["flow_meoh"], width=2.5, label_offset=(0, 2.8), fontsize=7.0)

    # ---- 循环与副产物流 ----
    # 未反应气闭环循环
    draw_flow_arrow(ax, 4, 42, 4, 55,
                    label=f"循环气经压缩机回流：{balance['m_gas_recycle']:,.0f} kg/t\n"
                    f"{recycle_pct:.2f}% of {separator_offgas:,.0f} kg/t off-gas\n"
                    f"质量循环比 {balance['recycle_ratio_mass']:.2f}:1；"
                    f"摩尔比 {balance['recycle_ratio_molar']:.2f}:1",
                    color=C["flow_recycle"], width=2.8, curve=-0.30,
                    label_offset=(7.0, 0), fontsize=6.8)

    # 驰放废气
    draw_flow_arrow(ax, 34, 35, 62, 35,
                    label=f"驰放 {balance['m_gas_purge']:.0f} kg/t\n"
                    f"{annual_purge_t:,.0f} t/年 · {purge_pct:.2f}% · 送锅炉掺烧",
                    color=C["flow_waste"], width=1.5, label_offset=(0, 2.8), fontsize=7.0)

    # 精馏塔 -> 产品输出
    draw_flow_arrow(ax, 81, 33, 81, 22,
                    label=f"聚合级精甲醇\n{annual_meoh_wan:.2f} 万吨/年\n纯度 ≥99.85 wt%",
                    color=C["flow_meoh"], width=3.0, label_offset=(7.5, 0))

    # 产品高亮框
    product_box = FancyBboxPatch(
        (68, 16), 26, 7,
        boxstyle="round,pad=0.3,rounding_size=1.0",
        facecolor="#F3E5F5", edgecolor="#6A1B9A",
        linewidth=2.0, linestyle="--", zorder=3
    )
    ax.add_patch(product_box)
    ax.text(81, 19.5, "目标产品\n聚合级甲醇",
            fontsize=8.5, fontweight="bold", ha="center", va="center",
            color="#4A148C", zorder=4)

    # 电解副产 O2 外售
    draw_flow_arrow(ax, 96, 83, 100, 83,
                    label=f"副产 O2 {annual['o2_byproduct']:.2f} 万吨/年",
                    color=C["flow_o2"], width=1.8, label_offset=(0, 3.0), fontsize=7.2)

    # 精馏釜水回用
    ax.plot([96, 98], [39, 39], color=C["flow_water"], linewidth=1.8, zorder=3)
    ax.plot([98, 98], [39, 72], color=C["flow_water"], linewidth=1.8, zorder=3)
    draw_flow_arrow(ax, 98, 72, 96, 77,
                    color=C["flow_water"], width=1.8)
    ax.text(96, 54,
            f"回用水 {annual['water_recycled']:.2f} 万吨/年\n"
            f"水回用率 {annual['water_recycling_rate']:.1f}%",
            fontsize=6.8, ha="right", color=C["flow_water"],
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor=C["flow_water"]))

    # 水循环说明框
    water_info_box = FancyBboxPatch(
        (36, 14), 28, 5,
        boxstyle="round,pad=0.25,rounding_size=0.8",
        facecolor=C["badge_green"], edgecolor=C["badge_green_edge"],
        linewidth=1.0, zorder=3
    )
    ax.add_patch(water_info_box)
    ax.text(50, 17.5, "政策锚点 B（Task 3）",
            fontsize=8.5, fontweight="bold", ha="center", va="center",
            color="#1B5E20", zorder=4)
    ax.text(50, 15.5, "f_green = 100%  ·  r_purge = 2.16%\n"
            "独立优化模型参数；不等于 Task 1 实物流量分流率",
            fontsize=7.5, ha="center", va="center",
            color="#2E7D32", zorder=4)

    # ---- 底部工程指标汇总看板 ----
    summary_y = 1.5
    summary_h = 10.5
    summary_box = FancyBboxPatch(
        (2, summary_y), 96, summary_h,
        boxstyle="round,pad=0.3,rounding_size=0.8",
        facecolor=C["summary_bg"], edgecolor=C["summary_edge"],
        linewidth=1.2, zorder=2
    )
    ax.add_patch(summary_box)

    # 看板标题
    ax.text(50, summary_y + summary_h - 1.5,
            "关键指标对照  (Task 1 工程流量基准；Task 3 政策情景单独列示)",
            fontsize=10, fontweight="bold", color=C["title_text"], zorder=3,
            ha="center")

    # 分隔线
    ax.plot([5, 95], [summary_y + summary_h - 2.8, summary_y + summary_h - 2.8],
            color=C["grid_line"], linewidth=0.8, zorder=3)

    col_data = [
        ("原料与产品", f"CO2 捕集: {annual_co2_wan:.2f} 万吨/年\n"
                   f"绿 H2: {annual_h2_wan:.2f} 万吨/年\n"
                   f"精甲醇: {annual_meoh_wan:.2f} 万吨/年"),
        ("物料与政策口径", f"Task 1 碳利用率: {balance['carbon_utilization_system'] * 100:.1f}%\n"
                        f"实物流分流: {recycle_pct:.2f}% / {purge_pct:.2f}%\n"
                        "Task 3 B: r_purge = 2.16%"),
        ("能量平衡", f"全厂电耗: {annual['electricity']:.3f} 亿 kWh/年\n"
                  "电解制氢占 95.1%；精馏占 1.1%\n"
                  "电解槽单耗: 52.0 kWh/kg H2"),
        ("水与副产", f"回用水: {annual['water_recycled']:.2f} 万吨/年\n"
                   f"副产 O2: {annual['o2_byproduct']:.2f} 万吨/年\n"
                   f"净新鲜水: {annual['water_consumption']:.2f} 万吨/年"),
    ]
    col_x = [6, 29, 53, 77]
    for cx, (col_title, col_body) in zip(col_x, col_data):
        ax.text(cx, summary_y + summary_h - 4.2, col_title,
                fontsize=8.5, fontweight="bold", color=C["title_text"],
                va="center", zorder=3,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="#E3F2FD",
                          edgecolor="#90CAF9", linewidth=0.5))
        ax.text(cx, summary_y + 2.0, col_body,
                fontsize=7.3, va="center", color="#37474F", zorder=3,
                linespacing=1.6)

    # ---- 保存输出 ----
    plt.tight_layout(pad=0.5)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight",
                facecolor=C["bg"], edgecolor="none")
    plt.close(fig)
    print(f"[完成] 工艺物质流-能量流拓扑图已保存: {output_path}")


if __name__ == "__main__":
    print("=" * 80)
    print("《环境规划与管理》任务 4: 工艺流程 MFA-EFA 拓扑图绘制")
    print("学生: 帕娜尔·阿克木 | Group 02")
    print("=" * 80)
    draw_process_flow_diagram()
