# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 4（学生随堂实训版）
脚本名称：task4_process_sankey_flow.py
功能描述：
  基于任务 3 求解出的帕累托拐点（锚点 B）工程通量基准数据，绘制工业园区
  10 万吨/年绿色甲醇系统物质流（MFA）与能量流（EFA）全流程拓扑图 (figures_output/fig1_mfa_process_flow.png)。
  包含：
    1. 物质流向与质量通量 (万吨/年)；
    2. 未反应气内循环闭环回路 (48.53 万吨/年)；
    3. 精馏冷凝生成水闭环循环至制氢进水池 (6.01 万吨/年)；
    4. 各工段综合电耗分布 (亿 kWh/年)；
    5. 出版级 300 DPI 矢量渲染输出。
  排版原则：所有通量标签均置于流线侧向空白区，并以白底细边框承托，
            避免标签之间、标签与箭头、标签与工艺单元框发生重叠。
"""

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

# 统一中文字体：优先选用具备粗体字重文件的中文字体，规避 findfont 告警
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'DejaVu Sans', 'Arial']
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
    """
    绘制园区级 10 万吨/年绿色甲醇工程物质与能量流动拓扑图。

    参数：
        output_filename (str): 图表输出文件名
    """
    out_dir = get_figures_output_dir()
    output_path = os.path.join(out_dir, output_filename)

    fig, ax = plt.subplots(figsize=(16, 10), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # --------------------------------------------------------------------------
    # 颜色配置规范（科学客观工程配色）
    # --------------------------------------------------------------------------
    c_bg_box     = "#f7f9fa"
    c_edge_box   = "#2c3e50"
    c_co2        = "#e67e22"  # 橙褐色代表碳源
    c_h2         = "#27ae60"  # 绿色代表绿氢
    c_water      = "#2980b9"  # 蓝色代表水系统
    c_meoh       = "#8e44ad"  # 紫色代表高纯甲醇
    c_gas_loop   = "#16a085"  # 青绿代表未反应循环气
    c_energy     = "#d35400"  # 能量消耗标签
    c_purge      = "#c0392b"  # 驰放废气

    # 标题与元数据说明
    ax.text(50, 96.5, "工业园区 10 万吨/年二氧化碳加氢制绿色甲醇系统物质与能量流向拓扑图（MFA-EFA）",
            fontsize=15, fontweight="bold", ha="center", va="center", color="#1a252f")
    ax.text(50, 93.8, "锚点 B 工况：绿电比例 100% | 驰放分流比 2.16% | 总碳利用率 91.8% | 年产 100,000 t 精甲醇 | 全厂综合电耗 11.25 亿 kWh/a",
            fontsize=10.5, ha="center", va="center", color="#555555")

    # --------------------------------------------------------------------------
    # 辅助绘图函数
    # --------------------------------------------------------------------------
    def draw_unit(x, y, w, h, title, subtitle="", elec_str="", bg_color=c_bg_box, border_color=c_edge_box):
        """绘制工艺单元框；标题、说明与电耗分三层排布，互不侵占"""
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1.2",
                                      facecolor=bg_color, edgecolor=border_color, linewidth=1.6, zorder=2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.78, title, fontsize=9.8, fontweight="bold",
                ha="center", va="center", color="#2c3e50", zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.50, subtitle, fontsize=8.0, ha="center", va="center",
                    color="#475569", zorder=3, linespacing=1.35)
        if elec_str:
            ax.text(x + w / 2, y + h * 0.17, elec_str, fontsize=7.8, fontweight="bold",
                    ha="center", va="center", color=c_energy, zorder=3)

    def draw_stream_arrow(x_start, y_start, x_end, y_end, color="#333333", width=2.0, rad=0.0):
        """仅绘制流线箭头；通量文字统一由 flow_label 在侧向空白区标注"""
        style = f"Simple,tail_width={width},head_width={width*3.2},head_length={width*2.8}"
        kw = dict(arrowstyle=style, color=color, zorder=4, shrinkA=0, shrinkB=0)
        if rad != 0.0:
            arrow = patches.FancyArrowPatch((x_start, y_start), (x_end, y_end),
                                            connectionstyle=f"arc3,rad={rad}", **kw)
        else:
            arrow = patches.FancyArrowPatch((x_start, y_start), (x_end, y_end), **kw)
        ax.add_patch(arrow)

    def flow_label(x, y, text, color="#333333", ha="center", va="center", fontsize=8.2):
        """流线通量标签：白底 + 与流线同色细边框，确保文字不与流线混叠"""
        ax.text(x, y, text, fontsize=fontsize, fontweight="bold", ha=ha, va=va, color=color,
                linespacing=1.30, zorder=6,
                bbox=dict(boxstyle="round,pad=0.32", facecolor="white",
                          edgecolor=color, linewidth=0.8, alpha=0.96))

    # --------------------------------------------------------------------------
    # 核心单元位置布局（横向五段式，预留标签走廊）
    # --------------------------------------------------------------------------
    draw_unit(6, 68, 17, 11, "烟气 CO2 捕集与压缩",
              "MEA 吸收 + 三级压缩\n5.0 MPa",
              "电耗 0.267 亿 kWh/a（2.37%）")

    draw_unit(6, 32, 17, 13, "130 MW PEM 电解制氢",
              "PEM 电解槽阵列（3.0 MPa）\n总进水 20.50 万吨/a",
              "电耗 10.769 亿 kWh/a（95.72%）")

    draw_unit(29, 55, 14, 10, "进料混合预热器",
              "新进料与循环气混合\n230 ℃，5.0 MPa")

    draw_unit(47, 55, 15, 10, "固定床甲醇合成器",
              "Cu/ZnO/Al2O3 催化\n250 ℃，5.0 MPa，单程 25%",
              "副产蒸汽回供再沸器")

    draw_unit(67, 55, 15, 10, "冷凝分离与循环分流",
              "气液闪蒸冷凝分离\n循环比 3.8:1，驰放 2.16%",
              "循环压缩 0.094 亿 kWh/a")

    draw_unit(67, 14, 15, 11, "双塔精馏分离系统",
              "脱轻塔 + 加压脱水塔\n纯度 ≥ 99.85 wt%",
              "精馏电耗 0.120 亿 kWh/a")

    # --------------------------------------------------------------------------
    # 物质流连线与通量标注（基于锚点 B 的 10 万吨/年工程通量）
    # --------------------------------------------------------------------------
    # 输入流 1：电厂烟气 CO2
    draw_stream_arrow(0, 73.5, 6, 73.5, c_co2, width=2.4)
    flow_label(1.5, 82.5, "烟气 CO2 捕集输入\n14.88 万吨/a", c_co2, ha="left")

    # 输入流 2：园区新鲜除盐纯水
    draw_stream_arrow(0, 38.5, 6, 38.5, c_water, width=2.2)
    flow_label(1.5, 28.5, "新鲜脱盐纯水补水\n14.49 万吨/a", c_water, ha="left")

    # 捕集 CO2 输送至混合预热器
    draw_stream_arrow(23, 73, 29, 61, c_co2, width=2.2)
    flow_label(27.5, 70, "高纯 CO2\n14.88 万吨/a", c_co2)

    # 绿氢输送至混合预热器
    draw_stream_arrow(23, 39, 29, 58, c_h2, width=2.2)
    flow_label(27, 43.5, "电解绿氢\n2.07 万吨/a", c_h2)

    # 电解制氢副产纯氧外售
    draw_stream_arrow(14, 32, 14, 11, "#16a085", width=2.2)
    flow_label(15.5, 22, "副产纯氧 16.57 万吨/a", "#16a085", ha="left")

    # 混合预热器至合成反应器
    draw_stream_arrow(43, 60, 47, 60, "#2c3e50", width=3.2)
    flow_label(45, 68, "混合气 65.49 万吨/a", "#2c3e50")

    # 合成反应器至冷凝分离器
    draw_stream_arrow(62, 60, 67, 60, "#2c3e50", width=3.2)
    flow_label(64.5, 68, "反应出口气 65.49 万吨/a", "#2c3e50")

    # 分离器顶部未反应气闭环内循环流
    draw_stream_arrow(74, 66, 41, 66, c_gas_loop, width=2.8, rad=0.42)
    flow_label(56, 78.5, "未反应气循环 48.53 万吨/a\n循环比 3.8:1（97.84% 回流）", c_gas_loop)

    # 分离器顶部驰放废气
    draw_stream_arrow(74, 66, 88, 74, c_purge, width=1.4)
    flow_label(87, 79.5, "驰放气 0.99 万吨/a\n碳损耗 8.2% 送锅炉掺烧", c_purge)

    # 分离器底部粗甲醇液相去精馏
    draw_stream_arrow(70, 55, 70, 25, c_meoh, width=2.6)
    flow_label(72.5, 40, "粗甲醇液\n16.47 万吨/a", c_meoh, ha="left")

    # 精馏产品输出
    draw_stream_arrow(82, 20, 97, 20, c_meoh, width=3.0)
    flow_label(83, 16, "精甲醇 10.00 万吨/a\n纯度 ≥ 99.85 wt%", c_meoh, ha="left")

    # 精馏副产水闭环回用至制氢进水池
    draw_stream_arrow(66, 18, 20, 36, c_water, width=2.0, rad=-0.22)
    flow_label(43, 30.5, "精馏副产水回用 6.01 万吨/a\n闭环回用率 29.3%（100% 回流）", c_water)

    # --------------------------------------------------------------------------
    # 底部图例与工程核心指标看板（2 × 2 网格，避免四列文字相互挤压）
    # --------------------------------------------------------------------------
    board_rect = patches.FancyBboxPatch((4, 1.5), 92, 10.5, boxstyle="round,pad=0.6,rounding_size=1.0",
                                        facecolor="#ffffff", edgecolor="#bdc3c7", linewidth=1.2, zorder=2)
    ax.add_patch(board_rect)

    ax.text(6, 11, "【关键规划工程指标对齐汇总（10 万吨/年规模）】",
            fontsize=9.2, fontweight="bold", color="#2c3e50", va="center")

    col1 = "- 原料：CO2 14.88 万吨/a（1.488 t/t）\n- 绿氢：2.07 万吨/a（0.207 t/t）"
    col2 = "- 净补水：14.49 万吨/a（1.449 t/t）\n- 回用水：6.01 万吨/a（29.3%）"
    col3 = "- 总碳利用率：91.8%（驰放损耗 8.2%）\n- 精甲醇：10.00 万吨/a（纯度 ≥ 99.85%）"
    col4 = "- 用电：11.25 亿 kWh/a（制氢占 95.7%）\n- 副产纯氧：16.57 万吨/a（1.657 t/t）"

    ax.text(8, 7.8, col1, fontsize=8.0, va="center", color="#34495e", linespacing=1.45)
    ax.text(52, 7.8, col2, fontsize=8.0, va="center", color="#34495e", linespacing=1.45)
    ax.text(8, 4.0, col3, fontsize=8.0, va="center", color="#34495e", linespacing=1.45)
    ax.text(52, 4.0, col4, fontsize=8.0, va="center", color="#34495e", linespacing=1.45)

    plt.tight_layout()

    # 确保输出目录存在并保存图表
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[成功] 工艺物质能量流向拓扑图已保存至: {output_path}")


if __name__ == "__main__":
    draw_mfa_process_flow()
