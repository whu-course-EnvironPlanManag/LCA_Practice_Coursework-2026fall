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
    2. 未反应气内循环闭环回路 (46.40 万吨/年)；
    3. 精馏冷凝生成水闭环循环至制氢进水池 (5.75 万吨/年)；
    4. 各工段综合电耗分布 (亿 kWh/年)；
    5. 出版级 300 DPI 矢量渲染输出。
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
import numpy as np
import pandas as pd

try:
    from task3_pareto_frontier_decision import (
        extract_pareto_frontier_and_anchors,
        simulate_park_methanol_system,
    )
except ImportError:
    from code_implementation.task3_pareto_frontier_decision import (
        extract_pareto_frontier_and_anchors,
        simulate_park_methanol_system,
    )

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
#   1. 提取满足总碳利用率不低于 96% 约束的帕累托拐点 B，并绘制 10 万吨/年工程规划通量；
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

    # TODO: [学生可视化实训任务 4] 园区级工艺物质与能量流动拓扑图绘制
    # 由任务 3 的同一网格和归一化目标距离准则提取锚点 B，避免图表参数与优化结果脱节。
    candidates = [
        simulate_park_methanol_system(f_green, r_purge)
        for f_green in np.linspace(0.0, 1.0, 60)
        for r_purge in np.linspace(0.004, 0.045, 50)
    ]
    _, anchors = extract_pareto_frontier_and_anchors(
        pd.DataFrame(candidates)
    )
    anchor = anchors["Anchor_B_Knee_Point"]
    annual_meoh_ton = 100000.0
    f_green = float(anchor["f_green"])
    r_purge = float(anchor["r_purge"])
    eta_carbon = float(anchor["eta_carbon"]) / 100.0
    feed_scale = 0.960 / eta_carbon

    co2_ton_per_ton = 1423.0 * feed_scale / 1000.0
    h2_ton_per_ton = 198.0 * feed_scale / 1000.0
    recycle_gas_ton_per_ton = 4686.0 * (1.0 - r_purge) / 1000.0
    purge_gas_ton_per_ton = 46.0 * (r_purge / 0.010) / 1000.0
    recycle_water_ton_per_ton = 575.0 * feed_scale / 1000.0
    makeup_water_ton_per_ton = 1385.0 * feed_scale / 1000.0
    electrolyzer_water_ton_per_ton = recycle_water_ton_per_ton + makeup_water_ton_per_ton
    oxygen_ton_per_ton = 1584.0 * feed_scale / 1000.0
    crude_methanol_ton_per_ton = 1575.0 * feed_scale / 1000.0
    reactor_gas_ton_per_ton = 6261.0 * feed_scale / 1000.0

    e_h2_kwh = 198.0 * feed_scale * 52.0
    e_co2_kwh = 255.0 * feed_scale
    e_recycle_kwh = 155.0 * ((0.010 / r_purge) ** 0.65)
    e_distill_kwh = 120.0
    e_total_kwh = e_h2_kwh + e_co2_kwh + e_recycle_kwh + e_distill_kwh

    def annual_100m_kwh(kwh_per_ton):
        return kwh_per_ton * annual_meoh_ton / 1e8

    def energy_share(kwh_per_ton):
        return 100.0 * kwh_per_ton / e_total_kwh

    def annual_wan_ton(ton_per_ton_product):
        return ton_per_ton_product * annual_meoh_ton / 10000.0

    fig, ax = plt.subplots(figsize=(16, 9.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # --------------------------------------------------------------------------
    # 颜色配置规范（科学客观工程配色）
    # --------------------------------------------------------------------------
    c_bg_box     = "#f7f9fa"
    c_edge_box   = "#2c3e50"
    c_co2        = "#e67e22" # 橙褐色代表碳源
    c_h2         = "#27ae60" # 绿色代表绿氢
    c_water      = "#2980b9" # 蓝色代表水系统
    c_meoh       = "#8e44ad" # 紫色代表高纯甲醇
    c_gas_loop   = "#16a085" # 青绿代表未反应循环气
    c_energy     = "#d35400" # 能量消耗标签

    # 标题与元数据说明
    ax.text(50, 96.5, "工业园区 10 万吨/年二氧化碳加氢制绿色甲醇系统物质与能量流向拓扑图 (MFA-EFA)",
            fontsize=15, fontweight="bold", ha="center", va="center", color="#1a252f")
    ax.text(50, 93.5, f"锚点 B：绿电 {f_green:.1%} | 驰放比 {r_purge:.2%} | "
            f"年产能：{annual_meoh_ton:,.0f} t/a | 全厂综合电耗：{annual_100m_kwh(e_total_kwh):.3f} 亿 kWh/a | "
            f"总碳转化利用率：{eta_carbon:.2%}",
            fontsize=10.5, ha="center", va="center", color="#555555")

    # --------------------------------------------------------------------------
    # 辅助绘图函数
    # --------------------------------------------------------------------------
    def draw_unit(x, y, w, h, title, subtitle="", elec_str="", bg_color=c_bg_box, border_color=c_edge_box):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1.2",
                                      facecolor=bg_color, edgecolor=border_color, linewidth=1.6, zorder=2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.72, title, fontsize=10.5, fontweight="bold", ha="center", va="center", color="#2c3e50", zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.45, subtitle, fontsize=8.5, ha="center", va="center", color="#475569", zorder=3)
        if elec_str:
            ax.text(x + w / 2, y + h * 0.20, elec_str, fontsize=8.0, fontweight="bold", ha="center", va="center", color=c_energy, zorder=3)

    def draw_stream_arrow(x_start, y_start, x_end, y_end, label="", color="#333333", width=2.0, rad=0.0, label_pos=0.5, label_offset=(0, 2.0)):
        style = f"Simple,tail_width={width},head_width={width*3.2},head_length={width*2.8}"
        kw = dict(arrowstyle=style, color=color, zorder=4)
        if rad != 0.0:
            arrow = patches.FancyArrowPatch((x_start, y_start), (x_end, y_end),
                                          connectionstyle=f"arc3,rad={rad}", **kw)
        else:
            arrow = patches.FancyArrowPatch((x_start, y_start), (x_end, y_end), **kw)
        ax.add_patch(arrow)

        if label:
            lx = x_start + (x_end - x_start) * label_pos + label_offset[0]
            ly = y_start + (y_end - y_start) * label_pos + label_offset[1]
            ax.text(lx, ly, label, fontsize=8.2, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="square,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85),
                    color=color, zorder=5)

    # --------------------------------------------------------------------------
    # 核心单元位置布局 (学生可根据工艺布局微调坐标)
    # --------------------------------------------------------------------------
    # 1. 碳捕集与压缩单元
    draw_unit(5, 68, 17, 14, "烟气 CO2 捕集与压缩单元", "MEA 化学吸收 + 三级压缩 (5.0 MPa)",
              f"电耗: {annual_100m_kwh(e_co2_kwh):.3f} 亿 kWh/a ({energy_share(e_co2_kwh):.2f}%)")

    # 2. 绿电电解水制氢站
    draw_unit(5, 30, 17, 16, "130 MW PEM 电解水制氢站", "质子交换膜电解槽阵列 (3.0 MPa)",
              f"电耗: {annual_100m_kwh(e_h2_kwh):.3f} 亿 kWh/a ({energy_share(e_h2_kwh):.2f}%)")

    # 3. 反应物料混合与预热器
    draw_unit(30, 52, 13, 13, "反应进料混合预热器", "新进料与循环气深度混合\n230 ℃, 5.0 MPa", "")

    # 4. 甲醇催化合成反应器
    draw_unit(48, 52, 15, 14, "固定床甲醇合成反应器", "Cu/ZnO/Al2O3 催化剂\n250 ℃, 5.0 MPa, 单程转化率 25%", "副产中压蒸汽回供再沸器")

    # 5. 高压气液分离器与循环气分流器
    draw_unit(69, 52, 14, 14, "冷凝分离与循环分流器", f"气液闪蒸冷凝分离器\n驰放比 {r_purge:.2%}",
              f"循环压缩电耗: {annual_100m_kwh(e_recycle_kwh):.3f} 亿 kWh/a "
              f"({energy_share(e_recycle_kwh):.2f}%)")

    # 6. 双塔精馏提纯系统
    draw_unit(69, 16, 14, 14, "双塔精馏分离系统", "常压脱轻塔 + 加压脱水精馏塔\n甲醇纯度 >= 99.85 wt%",
              f"脱水精馏电耗: {annual_100m_kwh(e_distill_kwh):.3f} 亿 kWh/a "
              f"({energy_share(e_distill_kwh):.2f}%)")

    # --------------------------------------------------------------------------
    # 物质流连线与通量标注 (基于 10 万吨/年甲醇基准通量)
    # --------------------------------------------------------------------------
    # 输入流 1：电厂烟气 CO2 原料
    draw_stream_arrow(0, 75, 5, 75, f"原料烟气 CO2 捕集\n{annual_wan_ton(co2_ton_per_ton):.2f} 万吨/a",
                      c_co2, width=2.4, label_offset=(-0.5, 3.5))

    # 输入流 2：园区新鲜除盐纯水外购
    draw_stream_arrow(0, 36, 5, 36, f"新鲜脱盐纯水补水\n{annual_wan_ton(makeup_water_ton_per_ton):.2f} 万吨/a",
                      c_water, width=2.2, label_offset=(-0.5, 3.2))

    # 捕集 CO2 输送至混合器
    draw_stream_arrow(22, 75, 30, 62, f"高纯 CO2 气体: {annual_wan_ton(co2_ton_per_ton):.2f} 万吨/a",
                      c_co2, width=2.2, label_offset=(0, 2.5))

    # 绿氢输送至混合器
    draw_stream_arrow(22, 38, 30, 56, f"电解高纯绿氢: {annual_wan_ton(h2_ton_per_ton):.2f} 万吨/a",
                      c_h2, width=2.2, label_offset=(0, -2.5))

    # 电解制氢副产纯氧外售
    draw_stream_arrow(13.5, 30, 13.5, 8, f"阳极副产高纯氧气 (外售)\n{annual_wan_ton(oxygen_ton_per_ton):.2f} 万吨/a",
                      "#16a085", width=2.2, label_offset=(0, 0))

    # 混合器到反应器
    draw_stream_arrow(43, 58.5, 48, 58.5, f"反应器入口混合气\n{annual_wan_ton(reactor_gas_ton_per_ton):.2f} 万吨/a",
                      "#2c3e50", width=3.2, label_offset=(0, 2.6))

    # 反应器到分离器
    draw_stream_arrow(63, 58.5, 69, 58.5, f"反应出口生成物\n{annual_wan_ton(reactor_gas_ton_per_ton):.2f} 万吨/a",
                      "#2c3e50", width=3.2, label_offset=(0, 2.6))

    # 分离器顶部循环气回路 (闭环内循环)
    draw_stream_arrow(76, 66, 36.5, 65,
                      f"分离器顶部未反应气循环流 ({1.0-r_purge:.1%} 回流)\n"
                      f"{annual_wan_ton(recycle_gas_ton_per_ton):.2f} 万吨/a",
                      c_gas_loop, width=2.8, rad=0.35, label_offset=(0, 5.5))

    # 分离器顶部驰放废气
    draw_stream_arrow(76, 66, 89, 78,
                      f"驰放废气 ({r_purge:.2%}，送供热锅炉)\n"
                      f"{annual_wan_ton(purge_gas_ton_per_ton):.2f} 万吨/a",
                      "#c0392b", width=1.4, label_offset=(0, 2.8))

    # 分离器底部粗甲醇液相到精馏塔
    draw_stream_arrow(76, 52, 76, 30, f"粗甲醇液体\n{annual_wan_ton(crude_methanol_ton_per_ton):.2f} 万吨/a",
                      c_meoh, width=2.6, label_offset=(6.0, 0))

    # 精馏塔产品输出：聚合级精甲醇
    draw_stream_arrow(83, 23, 98, 23, "目标产品：聚合级精甲醇\n10.00 万吨/a (纯度 >= 99.85%)", c_meoh, width=3.0, label_offset=(0, 3.2))

    # 精馏塔副产水闭环循环至制氢站 (闭环水循环)
    recycled_water_share = recycle_water_ton_per_ton / electrolyzer_water_ton_per_ton
    draw_stream_arrow(69, 21, 22, 33,
                      f"精馏塔釜副产水 (回流至制氢池)\n"
                      f"{annual_wan_ton(recycle_water_ton_per_ton):.2f} 万吨/a "
                      f"(总进水 {recycled_water_share:.1%})",
                      c_water, width=2.0, rad=-0.22, label_offset=(0, -4.5))

    # 电解槽总进水汇总标记
    ax.text(13.5, 47.5,
            f"PEM 电解槽总进水\n{annual_wan_ton(electrolyzer_water_ton_per_ton):.2f} 万吨/a "
            f"(净补水 {makeup_water_ton_per_ton/electrolyzer_water_ton_per_ton:.1%} + "
            f"回用水 {recycled_water_share:.1%})",
            fontsize=8.0, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#ebf5fb", edgecolor="#2980b9", linewidth=1.0),
            color="#2980b9", zorder=6)

    # --------------------------------------------------------------------------
    # 底部图例与工程核心指标看板
    # --------------------------------------------------------------------------
    board_rect = patches.FancyBboxPatch((4, 2), 92, 10, boxstyle="round,pad=0.6,rounding_size=1.0",
                                        facecolor="#ffffff", edgecolor="#bdc3c7", linewidth=1.2, zorder=2)
    ax.add_patch(board_rect)

    ax.text(6, 9.5, f"【锚点 B 工程指标 ({annual_meoh_ton/1000:.0f} 万吨/年规模)】",
            fontsize=9.5, fontweight="bold", color="#2c3e50")
    col1 = (f"- CO2 捕集：{annual_wan_ton(co2_ton_per_ton):.2f} 万吨/a "
            f"({co2_ton_per_ton:.3f} t/t)\n"
            f"- 绿氢需求：{annual_wan_ton(h2_ton_per_ton):.2f} 万吨/a "
            f"({h2_ton_per_ton:.3f} t/t)")
    col2 = (f"- 精馏水回用：{annual_wan_ton(recycle_water_ton_per_ton):.2f} 万吨/a "
            f"({recycled_water_share:.1%})\n"
            f"- 净除盐水：{annual_wan_ton(makeup_water_ton_per_ton):.2f} 万吨/a")
    col3 = (f"- 总碳利用率：{eta_carbon:.2%} (锚点 B)\n"
            f"- 副产氧外售：{annual_wan_ton(oxygen_ton_per_ton):.2f} 万吨/a")
    col4 = (f"- 全厂用电：{annual_100m_kwh(e_total_kwh):.3f} 亿 kWh/a\n"
            f"- PEM 制氢占比：{energy_share(e_h2_kwh):.1f}%")

    ax.text(7, 5.5, col1, fontsize=8.2, va="center", color="#34495e")
    ax.text(30, 5.5, col2, fontsize=8.2, va="center", color="#34495e")
    ax.text(54, 5.5, col3, fontsize=8.2, va="center", color="#34495e")
    ax.text(77, 5.5, col4, fontsize=8.2, va="center", color="#34495e")

    plt.tight_layout()

    # 确保输出目录存在并保存图表
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[成功] 工艺物质能量流向拓扑图已保存至: {output_path}")


if __name__ == "__main__":
    draw_mfa_process_flow()
