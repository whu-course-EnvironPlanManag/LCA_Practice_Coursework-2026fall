# -*- coding: utf-8 -*-
"""
《环境规划与管理》第十讲实训任务
作者：帕娜尔·阿克木 (Group 02)
任务：工艺流程物质流与能量流拓扑图绘制

功能说明：
  基于任务 3 帕累托拐点 (锚点 B: f_green=100%, r_purge=2.16%) 的工程通量数据，
  绘制工业园区 10 万吨/年绿色甲醇系统的 MFA-EFA 全流程拓扑图。

图表内容：
  1. 六大核心工艺单元 (碳捕集、制氢、预热、合成、分离、精馏)
  2. 物质流向与质量通量 (万吨/年)
  3. 未反应气闭环内循环流 (46.40 万吨/年)
  4. 精馏副产水回用流 (5.75 万吨/年)
  5. 各工段电耗分布标注
  6. 底部关键工程指标汇总看板
"""

import sys
import io
import os

# Windows 环境 UTF-8 编码处理
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 中文字体配置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def ensure_output_directory():
    """确保图表输出目录存在"""
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


# =============================================================================
# 配色方案 (科学工程风格)
# =============================================================================
COLORS = {
    "background": "#f7f9fa",
    "border": "#2c3e50",
    "co2": "#e67e22",       # 橙褐: 碳源
    "h2": "#27ae60",        # 绿色: 绿氢
    "water": "#2980b9",     # 蓝色: 水系统
    "methanol": "#8e44ad",  # 紫色: 甲醇产品
    "recycle_gas": "#16a085",  # 青绿: 循环气
    "energy": "#d35400",    # 深橙: 能耗标签
    "text_dark": "#1a252f",
    "text_medium": "#2c3e50",
    "text_light": "#475569",
    "text_gray": "#555555"
}


# =============================================================================
# 辅助绘图函数
# =============================================================================
def render_process_unit(ax, x, y, width, height, title, subtitle="", energy_label=""):
    """绘制工艺单元方框"""
    box = mpatches.FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.8,rounding_size=1.2",
        facecolor=COLORS["background"],
        edgecolor=COLORS["border"],
        linewidth=1.6,
        zorder=2
    )
    ax.add_patch(box)

    # 标题
    ax.text(x + width/2, y + height*0.72, title,
            fontsize=10.5, fontweight="bold", ha="center", va="center",
            color=COLORS["text_medium"], zorder=3)

    # 副标题
    if subtitle:
        ax.text(x + width/2, y + height*0.45, subtitle,
                fontsize=8.5, ha="center", va="center",
                color=COLORS["text_light"], zorder=3)

    # 能耗标签
    if energy_label:
        ax.text(x + width/2, y + height*0.20, energy_label,
                fontsize=8.0, fontweight="bold", ha="center", va="center",
                color=COLORS["energy"], zorder=3)


def render_flow_arrow(ax, x1, y1, x2, y2, label="", color="#333333",
                      width=2.0, curvature=0.0, label_offset=(0, 2.0)):
    """绘制物流箭头与标注"""
    style = f"Simple,tail_width={width},head_width={width*3.2},head_length={width*2.8}"
    arrow_kwargs = dict(arrowstyle=style, color=color, zorder=4)

    if curvature != 0.0:
        arrow = mpatches.FancyArrowPatch(
            (x1, y1), (x2, y2),
            connectionstyle=f"arc3,rad={curvature}",
            **arrow_kwargs
        )
    else:
        arrow = mpatches.FancyArrowPatch((x1, y1), (x2, y2), **arrow_kwargs)

    ax.add_patch(arrow)

    # 标注文字
    if label:
        lx = x1 + (x2 - x1) * 0.5 + label_offset[0]
        ly = y1 + (y2 - y1) * 0.5 + label_offset[1]
        ax.text(lx, ly, label,
                fontsize=8.2, fontweight="bold", ha="center", va="center",
                bbox=dict(boxstyle="square,pad=0.2", facecolor="white",
                          edgecolor="none", alpha=0.85),
                color=color, zorder=5)


# =============================================================================
# 主绘图函数
# =============================================================================
def draw_process_flow_diagram(output_filename="fig1_mfa_process_flow.png"):
    """
    绘制 10 万吨/年绿色甲醇系统物质流与能量流拓扑图
    """
    out_dir = ensure_output_directory()
    output_path = os.path.join(out_dir, output_filename)

    fig, ax = plt.subplots(figsize=(16, 9.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # ---- 标题区 ----
    ax.text(50, 96.5,
            "工业园区 10 万吨/年 CO2 加氢制绿色甲醇系统 物质流-能量流拓扑图 (MFA-EFA)",
            fontsize=15, fontweight="bold", ha="center", va="center",
            color=COLORS["text_dark"])

    ax.text(50, 93.5,
            "运行基准: 8000 h/a | 产能: 100,000 t/a 精甲醇 | 综合电耗: 10.826 亿 kWh/a | 碳利用率: 96.0%",
            fontsize=10.5, ha="center", va="center", color=COLORS["text_gray"])

    # ---- 六大工艺单元布局 ----
    # 1. 碳捕集与压缩
    render_process_unit(ax, 5, 68, 17, 14,
                        "烟气 CO2 捕集压缩单元",
                        "MEA 化学吸收 + 三级压缩 (5.0 MPa)",
                        "电耗: 0.255 亿 kWh/a (2.36%)")

    # 2. PEM 电解制氢
    render_process_unit(ax, 5, 30, 17, 16,
                        "130 MW PEM 电解水制氢站",
                        "质子交换膜电解槽阵列 (3.0 MPa)",
                        "电耗: 10.296 亿 kWh/a (95.10%)")

    # 3. 进料混合预热
    render_process_unit(ax, 30, 52, 13, 13,
                        "反应进料混合预热器",
                        "新进料+循环气深度混合\n230°C, 5.0 MPa",
                        "")

    # 4. 甲醇合成反应器
    render_process_unit(ax, 48, 52, 15, 14,
                        "固定床甲醇合成反应器",
                        "Cu/ZnO/Al2O3 催化剂\n250°C, 5.0 MPa, 单程转化率 25%",
                        "副产中压蒸汽回供再沸器")

    # 5. 气液分离与循环
    render_process_unit(ax, 69, 52, 14, 14,
                        "冷凝分离与循环分流器",
                        "气液闪蒸冷凝分离器\n循环比 3.8:1, 驰放比 1.0%",
                        "循环压缩电耗: 0.155 亿 kWh/a")

    # 6. 双塔精馏提纯
    render_process_unit(ax, 69, 16, 14, 14,
                        "双塔精馏分离系统",
                        "常压脱轻塔 + 加压脱水精馏塔\n甲醇纯度 >= 99.85 wt%",
                        "脱水精馏电耗: 0.120 亿 kWh/a")

    # ---- 外部输入物流 ----
    # 烟气 CO2 原料
    render_flow_arrow(ax, 0, 75, 5, 75,
                      "原料烟气 CO2 捕集\n14.23 万吨/a (100%)",
                      COLORS["co2"], width=2.4, label_offset=(-0.5, 3.5))

    # 新鲜除盐水
    render_flow_arrow(ax, 0, 36, 5, 36,
                      "新鲜脱盐纯水补水\n13.85 万吨/a (70.7%)",
                      COLORS["water"], width=2.2, label_offset=(-0.5, 3.2))

    # ---- 单元间物流连接 ----
    # CO2 -> 混合器
    render_flow_arrow(ax, 22, 75, 30, 62,
                      "高纯 CO2: 14.23 万吨/a",
                      COLORS["co2"], width=2.2, label_offset=(0, 2.5))

    # H2 -> 混合器
    render_flow_arrow(ax, 22, 38, 30, 56,
                      "电解绿氢: 1.98 万吨/a",
                      COLORS["h2"], width=2.2, label_offset=(0, -2.5))

    # 电解副产 O2 外售
    render_flow_arrow(ax, 13.5, 30, 13.5, 8,
                      "阳极副产高纯氧气 (外售)\n15.84 万吨/a",
                      COLORS["recycle_gas"], width=2.2, label_offset=(0, 0))

    # 混合器 -> 反应器
    render_flow_arrow(ax, 43, 58.5, 48, 58.5,
                      "反应器入口混合气\n62.61 万吨/a",
                      COLORS["border"], width=3.2, label_offset=(0, 2.6))

    # 反应器 -> 分离器
    render_flow_arrow(ax, 63, 58.5, 69, 58.5,
                      "反应出口生成物\n62.61 万吨/a",
                      COLORS["border"], width=3.2, label_offset=(0, 2.6))

    # 循环气闭环回路
    render_flow_arrow(ax, 76, 66, 36.5, 65,
                      "未反应气循环流 (99.0% 回流)\n46.40 万吨/a (循环比 3.8:1)",
                      COLORS["recycle_gas"], width=2.8, curvature=0.35, label_offset=(0, 5.5))

    # 驰放废气排放
    render_flow_arrow(ax, 76, 66, 89, 78,
                      "驰放废气 (1.0% 排至供热锅炉)\n0.46 万吨/a (碳损耗 4.0%)",
                      "#c0392b", width=1.4, label_offset=(0, 2.8))

    # 分离器 -> 精馏塔
    render_flow_arrow(ax, 76, 52, 76, 30,
                      "粗甲醇液体\n15.75 万吨/a",
                      COLORS["methanol"], width=2.6, label_offset=(6.0, 0))

    # 精馏塔 -> 产品输出
    render_flow_arrow(ax, 83, 23, 98, 23,
                      "产品: 聚合级精甲醇\n10.00 万吨/a (纯度>=99.85%)",
                      COLORS["methanol"], width=3.0, label_offset=(0, 3.2))

    # 精馏副产水回用
    render_flow_arrow(ax, 69, 21, 22, 33,
                      "精馏釜副产生成水 (闭环回用至制氢池)\n5.75 万吨/a (削减新鲜水耗 29.3%)",
                      COLORS["water"], width=2.0, curvature=-0.22, label_offset=(0, -4.5))

    # ---- 电解槽进水标注 ----
    ax.text(13.5, 47.5,
            "PEM 电解槽总进水\n19.60 万吨/a (100%)\n[净补水 70.7% + 回用水 29.3%]",
            fontsize=8.0, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#ebf5fb",
                      edgecolor=COLORS["water"], linewidth=1.0),
            color=COLORS["water"], zorder=6)

    # ---- 底部工程指标看板 ----
    board = mpatches.FancyBboxPatch(
        (4, 2), 92, 10,
        boxstyle="round,pad=0.6,rounding_size=1.0",
        facecolor="#ffffff", edgecolor="#bdc3c7", linewidth=1.2, zorder=2
    )
    ax.add_patch(board)

    ax.text(6, 9.5, "【关键工程指标汇总 (10 万吨/年规模)】",
            fontsize=9.5, fontweight="bold", color=COLORS["text_medium"])

    col1 = "- 原料捕集需求: 高纯 CO2 14.23 万吨/a (1.423 t/t)\n- 绿氢原料需求: 高纯绿氢 1.98 万吨/a (0.198 t/t)"
    col2 = "- 水资源循环率: 精馏水回用 5.75 万吨/a (22.9%)\n- 净除盐水消耗: 13.85 万吨/a (吨水指标 1.385 t/t)"
    col3 = "- 全系统碳利用率: 96.0% (驰放碳损耗 4.0%)\n- 副产工业纯氧: 外售量 15.84 万吨/a (1.584 t/t)"
    col4 = "- 全厂年用电负荷: 10.826 亿 kWh/a (制氢占 95.1%)\n- 热力学耦合: 反应副产蒸汽回用碳捕集再沸器"

    ax.text(7, 5.5, col1, fontsize=8.2, va="center", color="#34495e")
    ax.text(30, 5.5, col2, fontsize=8.2, va="center", color="#34495e")
    ax.text(54, 5.5, col3, fontsize=8.2, va="center", color="#34495e")
    ax.text(77, 5.5, col4, fontsize=8.2, va="center", color="#34495e")

    # ---- 保存输出 ----
    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    print(f"[完成] 工艺物质流-能量流拓扑图已保存: {output_path}")


# =============================================================================
# 主程序入口
# =============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("《环境规划与管理》任务 4: 工艺流程 MFA-EFA 拓扑图绘制")
    print("学生: 帕娜尔·阿克木 | Group 02")
    print("=" * 80)
    draw_process_flow_diagram()
