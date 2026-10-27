# -*- coding: utf-8 -*-
"""
《环境规划与管理》第十讲实训任务
作者：帕娜尔·阿克木 (Group 02)
任务：工艺流程物质流与能量流拓扑图绘制

功能说明：
  基于任务 3 帕累托拐点 (锚点 B: f_green=100%, r_purge=2.16%) 的工程通量数据，
  绘制工业园区 10 万吨/年绿色甲醇系统的 MFA-EFA 全流程拓扑图。

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

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

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
            "工业园区 10 万吨/年 CO2 加氢制绿色甲醇系统",
            fontsize=17, fontweight="bold", ha="center", va="center",
            color="white", zorder=3)
    ax.text(50, 95.4,
            "物质流 - 能量流拓扑图 (MFA-EFA)   |   锚点B工况: f_green=100%, r_purge=2.16%   |   年运行 8000 h",
            fontsize=9.0, ha="center", va="center", color="#B0BEC5", zorder=3)

    # ---- 六大工艺单元卡片 ----
    # 第一行：碳捕集 + 电解制氢
    draw_process_card(ax, 4, 77, 30, 13,
                      "CO2 捕集压缩单元",
                      ["MEA化学吸收 + 三级压缩至5.0MPa",
                       "进料: 烟气CO2 14.23万吨/a"],
                      card_type="input",
                      energy_text="0.255亿kWh/a (2.4%)",
                      icon_text="1")

    draw_process_card(ax, 66, 77, 30, 13,
                      "130 MW PEM 电解水制氢站",
                      ["质子交换膜电解槽阵列 (3.0MPa)",
                       "净脱盐纯水 13.85万吨/a + 回用水 5.75万吨/a"],
                      card_type="input",
                      energy_text="10.296亿kWh/a (95.1%)",
                      icon_text="2")

    # 第二行：混合预热 + 合成反应器
    draw_process_card(ax, 4, 55, 30, 13,
                      "反应进料混合预热器",
                      ["新鲜CO2/H2 + 循环气深度混合",
                       "预热至230C, 5.0MPa进料"],
                      card_type="core",
                      icon_text="3")

    draw_process_card(ax, 66, 55, 30, 13,
                      "固定床甲醇合成反应器",
                      ["Cu/ZnO/Al2O3催化剂, 250C",
                       "单程转化率25%, 放热反应"],
                      card_type="core",
                      energy_text="副产中压蒸汽 (回用)",
                      icon_text="4")

    # 第三行：冷凝分离 + 双塔精馏
    draw_process_card(ax, 4, 33, 30, 13,
                      "冷凝分离与循环分流器",
                      ["高压气液闪蒸冷凝分离器",
                       "循环比3.8:1, 驰放比2.16%"],
                      card_type="sep",
                      energy_text="0.155亿kWh/a (1.4%)",
                      icon_text="5")

    draw_process_card(ax, 66, 33, 30, 13,
                      "双塔精馏分离系统",
                      ["常压脱轻塔 + 加压脱水精馏塔",
                       "产出纯度>=99.85%聚合级甲醇"],
                      card_type="product",
                      energy_text="0.120亿kWh/a (1.1%)",
                      icon_text="6")

    # ---- 外部输入物流 ----
    draw_flow_arrow(ax, -2, 86, 4, 86,
                    label="烟气CO2\n14.23万吨/a\n(1.423 t/t产品)",
                    color=C["flow_co2"], width=2.5, label_offset=(0, 3.0), fontsize=7.5)

    draw_flow_arrow(ax, -2, 63, 4, 63,
                    label="新鲜脱盐纯水\n13.85万吨/a\n(1.385 t/t产品)",
                    color=C["flow_water"], width=2.2, label_offset=(0, 3.0), fontsize=7.5)

    draw_flow_arrow(ax, -2, 40, 4, 40,
                    label="绿电供给\n10.826亿kWh/a\n(100%可再生)",
                    color=C["flow_h2"], width=2.0, label_offset=(0, 3.0), fontsize=7.5)

    # ---- 单元间主物流连接 ----
    # CO2捕集 -> 混合预热器
    draw_flow_arrow(ax, 19, 77, 19, 68,
                    label="高纯CO2\n14.23万吨/a",
                    color=C["flow_co2"], width=2.2, label_offset=(-7.5, 0))

    # 电解制氢 -> 混合预热器 (跨越)
    draw_flow_arrow(ax, 66, 83, 34, 63,
                    label="电解绿H2: 1.98万吨/a",
                    color=C["flow_h2"], width=2.2, curve=0.22, label_offset=(2, 3.5))

    # 混合预热器 -> 合成反应器
    draw_flow_arrow(ax, 34, 61.5, 66, 61.5,
                    label="反应器入口混合气: 62.61万吨/a\n(CO2 75.4% + H2 21.8% + 惰性气)",
                    color=C["flow_main"], width=3.0, label_offset=(0, 2.8))

    # 合成反应器 -> 冷凝分离器
    draw_flow_arrow(ax, 81, 55, 81, 46,
                    label="反应出口生成物\n62.61万吨/a\n(粗甲醇16% + 未反应气84%)",
                    color=C["flow_main"], width=3.0, label_offset=(7.5, 0), fontsize=7.2)

    # 冷凝分离器 -> 精馏塔
    draw_flow_arrow(ax, 19, 33, 19, 22,
                    label="粗甲醇液体\n15.75万吨/a",
                    color=C["flow_meoh"], width=2.5, label_offset=(-7.5, 0))

    # ---- 循环与副产物流 ----
    # 未反应气闭环循环
    draw_flow_arrow(ax, 4, 42, 4, 55,
                    label="未反应气闭环循环 (97.84%回流)\n46.40万吨/a, 循环比3.8:1\n(CO2/H2在系统内多次通过反应器)",
                    color=C["flow_recycle"], width=2.8, curve=-0.30,
                    label_offset=(-4.5, 0), fontsize=7.0)

    # 驰放废气
    draw_flow_arrow(ax, 34, 39, 50, 39,
                    label="驰放废气 (2.16%分流)\n0.46万吨/a\n送废热锅炉掺烧",
                    color=C["flow_waste"], width=1.5, label_offset=(0, 2.8), fontsize=7.2)

    # 精馏塔 -> 产品输出
    draw_flow_arrow(ax, 81, 33, 81, 22,
                    label="聚合级精甲醇产品\n10.00万吨/a\n纯度>=99.85wt%",
                    color=C["flow_meoh"], width=3.0, label_offset=(7.5, 0))

    # 产品高亮框
    product_box = FancyBboxPatch(
        (68, 16), 26, 7,
        boxstyle="round,pad=0.3,rounding_size=1.0",
        facecolor="#F3E5F5", edgecolor="#6A1B9A",
        linewidth=2.0, linestyle="--", zorder=3
    )
    ax.add_patch(product_box)
    ax.text(81, 19.5, "TARGET PRODUCT\n绿色甲醇 (RFNBO)",
            fontsize=8.5, fontweight="bold", ha="center", va="center",
            color="#4A148C", zorder=4)

    # 电解副产 O2 外售
    draw_flow_arrow(ax, 96, 77, 96, 68,
                    label="副产高纯O2\n15.84万吨/a\n(外售工业用氧)",
                    color=C["flow_o2"], width=1.8, label_offset=(0, 3.0), fontsize=7.2)

    # 精馏釜水回用
    draw_flow_arrow(ax, 66, 38, 66, 22,
                    label="精馏釜产生水\n5.75万吨/a\n(闭环回用至电解槽)",
                    color=C["flow_water"], width=1.8, curve=-0.25,
                    label_offset=(-5.5, 0), fontsize=7.2)

    # 水循环说明框
    water_info_box = FancyBboxPatch(
        (36, 14), 28, 5,
        boxstyle="round,pad=0.25,rounding_size=0.8",
        facecolor=C["badge_green"], edgecolor=C["badge_green_edge"],
        linewidth=1.0, zorder=3
    )
    ax.add_patch(water_info_box)
    ax.text(50, 17.5, "水循环闭环",
            fontsize=8.5, fontweight="bold", ha="center", va="center",
            color="#1B5E20", zorder=4)
    ax.text(50, 15.5, "精馏回用水 5.75万吨/a (29.3%)\n净新鲜水耗降至 1.385 t/t产品",
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
            "关键工程指标汇总  (10万吨/年规模, 锚点B工况)",
            fontsize=10, fontweight="bold", color=C["title_text"], zorder=3,
            ha="center")

    # 分隔线
    ax.plot([5, 95], [summary_y + summary_h - 2.8, summary_y + summary_h - 2.8],
            color=C["grid_line"], linewidth=0.8, zorder=3)

    col_data = [
        ("原料与产品", "CO2捕集: 14.23万t/a (1.423 t/t)\n绿H2: 1.98万t/a (0.198 t/t)\n精甲醇: 10.00万t/a"),
        ("碳平衡", "系统碳利用率: 96.0%\n驰放碳损耗: 4.0%\n净固碳: -1,085 kgCO2e/t"),
        ("能量平衡", "全厂电耗: 10.826亿kWh/a\n制氢占95.1%, 精馏1.1%\n综合能耗: 52.0 kWh/kgH2"),
        ("水与副产", "水循环率: 29.3% (5.75万t/a)\n副产O2外售: 15.84万t/a\n新鲜水: 1.385 t/t产品"),
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
