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
    """
    绘制园区级 10 万吨/年绿色甲醇工程物质与能量流动拓扑图。
    
    参数：
        output_filename (str): 图表输出文件名
    """
    out_dir = get_figures_output_dir()
    output_path = os.path.join(out_dir, output_filename)

    import numpy as np
    import pandas as pd

    try:
        from task3_pareto_frontier_decision import (
            extract_pareto_frontier_and_anchors,
            simulate_park_methanol_system,
        )
        from task1_mfa_recycle_solver import solve_mfa_balance
    except ImportError:
        from code_implementation.task3_pareto_frontier_decision import (
            extract_pareto_frontier_and_anchors,
            simulate_park_methanol_system,
        )
        from code_implementation.task1_mfa_recycle_solver import solve_mfa_balance

    # Recreate task 3's uniform grid and take anchor B from its actual Pareto solution.
    grid_records = [
        simulate_park_methanol_system(float(f_green), float(r_purge))
        for f_green in np.linspace(0.0, 1.0, 60)
        for r_purge in np.linspace(0.004, 0.045, 50)
    ]
    _, anchors = extract_pareto_frontier_and_anchors(pd.DataFrame(grid_records))
    anchor_b = anchors["Anchor_B_Knee_Point"]
    f_green = float(anchor_b["f_green"])
    r_purge = float(anchor_b["r_purge"])

    # Use the same anchor variables to retrieve task 3 energy/LCA and task 1 MFA flows.
    scenario = simulate_park_methanol_system(f_green, r_purge)
    mfa = solve_mfa_balance(single_pass_conv=0.250, purge_ratio=r_purge)
    annual_methanol_t = 100000.0
    annual_scale = annual_methanol_t / 1000.0

    def annual_flow_t(mass_kg_per_t_product):
        return float(mass_kg_per_t_product) * annual_scale

    mass_flows_t_a = {
        "fresh_co2": annual_flow_t(mfa["m_co2_fresh_kg"]),
        "fresh_h2": annual_flow_t(mfa["m_h2_fresh_kg"]),
        "fresh_water": annual_flow_t(mfa["m_makeup_water_kg"]),
        "recycle_water": annual_flow_t(mfa["m_h2o_gen_kg"]),
        "electrolyzer_water": annual_flow_t(mfa["m_makeup_water_kg"] + mfa["m_h2o_gen_kg"]),
        "oxygen": annual_flow_t(mfa["m_oxygen_kg"]),
        "reactor_inlet": annual_flow_t(mfa["m_reactor_inlet_kg"]),
        "reactor_outlet": annual_flow_t(mfa["m_reactor_outlet_kg"]),
        "recycle_gas": annual_flow_t(mfa["m_gas_recycle_kg"]),
        "purge_gas": annual_flow_t(mfa["m_gas_purge_kg"]),
        "crude_methanol": annual_flow_t(mfa["m_meoh_out_kg"] + mfa["m_h2o_gen_kg"]),
        "methanol_product": annual_flow_t(mfa["m_meoh_out_kg"]),
    }

    energy_kwh_per_t = {
        "capture": 255.0 * mfa["m_co2_fresh_kg"] / 1423.0,
        "electrolysis": 52.0 * mfa["m_h2_fresh_kg"],
        "recycle_compression": 155.0 * ((0.010 / r_purge) ** 0.65),
        "distillation": 120.0,
    }
    if not np.isclose(sum(energy_kwh_per_t.values()), scenario["e_total_kwh"], rtol=1e-9):
        raise ValueError("任务4分项电耗与任务3综合电耗不一致")
    annual_energy_100m_kwh = {
        key: value * annual_methanol_t / 1e8
        for key, value in energy_kwh_per_t.items()
    }
    total_energy_100m_kwh = scenario["e_total_kwh"] * annual_methanol_t / 1e8
    max_mass_flow = max(mass_flows_t_a.values())

    def mass_line_width(flow_t_a):
        return 0.8 + 3.0 * flow_t_a / max_mass_flow

    def wan_ton(flow_t_a):
        return flow_t_a / 10000.0

    def energy_label(component):
        value = annual_energy_100m_kwh[component]
        share = value / total_energy_100m_kwh * 100.0
        return f"电耗: {value:.3f} 亿 kWh/a ({share:.1f}%)"

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
    ax.text(50, 96.5, "工业园区 10 万吨/年绿色甲醇系统物质与能量流向拓扑图 (MFA-EFA)",
            fontsize=15, fontweight="bold", ha="center", va="center", color="#1a252f")
    ax.text(50, 93.5,
            f"锚点 B：绿电 {f_green:.2%} | 驰放比 {r_purge:.2%} | 年产 {annual_methanol_t:,.0f} t | 全厂电耗 {total_energy_100m_kwh:.3f} 亿 kWh/a | 碳利用率 {scenario['eta_carbon']:.2f}%",
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
    # 四个工段标签与对应设备节点
    ax.text(13.5, 85.0, "① 碳捕集", fontsize=10, fontweight="bold", ha="center", color=c_co2)
    ax.text(13.5, 48.5, "② 绿电制氢", fontsize=10, fontweight="bold", ha="center", color=c_h2)
    ax.text(55.5, 48.5, "③ 催化合成", fontsize=10, fontweight="bold", ha="center", color=c_edge_box)
    ax.text(76.0, 33.5, "④ 双塔精馏", fontsize=10, fontweight="bold", ha="center", color=c_meoh)
    legend_items = [
        patches.Patch(color=c_co2, label="CO2 质量流"),
        patches.Patch(color=c_h2, label="H2 质量流"),
        patches.Patch(color=c_water, label="水质量流"),
        patches.Patch(color=c_gas_loop, label="未反应气回流"),
        patches.Patch(color=c_meoh, label="甲醇物流"),
        patches.Patch(color=c_energy, label="电耗标签；质量流线宽与通量成正比"),
    ]
    ax.legend(handles=legend_items, loc="upper left", bbox_to_anchor=(0.015, 0.905),
              ncol=3, fontsize=7.4, framealpha=0.92, edgecolor="#d0d7de")

    # 1. 碳捕集与压缩单元
    draw_unit(5, 68, 17, 14, "烟气 CO2 捕集与压缩单元", "MEA 化学吸收 + 三级压缩 (5.0 MPa)", energy_label("capture"))

    # 2. 绿电电解水制氢站
    draw_unit(5, 30, 17, 16, "PEM 电解水制氢站", "质子交换膜电解槽阵列 (3.0 MPa)", energy_label("electrolysis"))

    # 3. 反应物料混合与预热器
    draw_unit(30, 52, 13, 13, "反应进料混合预热器", "新鲜进料与循环气混合\n230 ℃, 5.0 MPa", "")

    # 4. 甲醇催化合成反应器
    draw_unit(48, 52, 15, 14, "固定床甲醇合成反应器", "Cu/ZnO/Al2O3 催化剂\n单程转化率 25%", "")

    # 5. 高压气液分离器与循环气分流器
    recycle_mass_ratio = mfa["recycle_ratio_mass"]
    draw_unit(69, 52, 14, 14, "冷凝分离与循环分流器", f"气液闪蒸分离\n质量循环比 {recycle_mass_ratio:.2f}:1, 驰放 {r_purge:.2%}", energy_label("recycle_compression"))

    # 6. 双塔精馏提纯系统
    draw_unit(69, 16, 14, 14, "双塔精馏分离系统", "常压脱轻塔 + 加压脱水塔\n甲醇纯度 >= 99.85 wt%", energy_label("distillation"))

    # --------------------------------------------------------------------------
    # 物质流连线与通量标注 (基于 10 万吨/年甲醇基准通量)
    # --------------------------------------------------------------------------
    # 输入流 1：电厂烟气 CO2 原料
    draw_stream_arrow(0, 75, 5, 75, f"新鲜 CO2\n{wan_ton(mass_flows_t_a['fresh_co2']):.2f} 万吨/a", c_co2, width=mass_line_width(mass_flows_t_a["fresh_co2"]), label_offset=(-0.5, 3.5))

    # 输入流 2：园区新鲜除盐纯水外购
    water_fresh_share = mass_flows_t_a["fresh_water"] / mass_flows_t_a["electrolyzer_water"] * 100.0
    draw_stream_arrow(0, 36, 5, 36, f"新鲜脱盐水\n{wan_ton(mass_flows_t_a['fresh_water']):.2f} 万吨/a ({water_fresh_share:.1f}%)", c_water, width=mass_line_width(mass_flows_t_a["fresh_water"]), label_offset=(-0.5, 3.2))

    # 捕集 CO2 输送至混合器
    draw_stream_arrow(22, 75, 30, 62, f"捕集 CO2 {wan_ton(mass_flows_t_a['fresh_co2']):.2f} 万吨/a", c_co2, width=mass_line_width(mass_flows_t_a["fresh_co2"]), label_offset=(0, 2.5))

    # 绿氢输送至混合器
    draw_stream_arrow(22, 38, 30, 56, f"电解绿氢 {wan_ton(mass_flows_t_a['fresh_h2']):.2f} 万吨/a", c_h2, width=mass_line_width(mass_flows_t_a["fresh_h2"]), label_offset=(0, -2.5))

    # 电解制氢副产纯氧外售
    draw_stream_arrow(13.5, 30, 13.5, 8, f"阳极副产纯氧 (外售)\n{wan_ton(mass_flows_t_a['oxygen']):.2f} 万吨/a", "#16a085", width=mass_line_width(mass_flows_t_a["oxygen"]), label_offset=(0, 0))

    # 混合器到反应器
    draw_stream_arrow(43, 58.5, 48, 58.5, f"反应器入口\n{wan_ton(mass_flows_t_a['reactor_inlet']):.2f} 万吨/a", "#2c3e50", width=mass_line_width(mass_flows_t_a["reactor_inlet"]), label_offset=(0, 2.6))

    # 反应器到分离器
    draw_stream_arrow(63, 58.5, 69, 58.5, f"反应器出口\n{wan_ton(mass_flows_t_a['reactor_outlet']):.2f} 万吨/a", "#2c3e50", width=mass_line_width(mass_flows_t_a["reactor_outlet"]), label_offset=(0, 2.6))

    # 分离器顶部循环气回路 (闭环内循环)
    draw_stream_arrow(76, 66, 36.5, 65, f"未反应气体循环回流 ({1.0-r_purge:.2%})\n{wan_ton(mass_flows_t_a['recycle_gas']):.2f} 万吨/a", c_gas_loop, width=mass_line_width(mass_flows_t_a["recycle_gas"]), rad=0.35, label_offset=(0, 5.5))

    # 分离器顶部驰放废气
    draw_stream_arrow(76, 66, 89, 78, f"驰放尾气 ({r_purge:.2%})\n{wan_ton(mass_flows_t_a['purge_gas']):.3f} 万吨/a", "#c0392b", width=mass_line_width(mass_flows_t_a["purge_gas"]), label_offset=(0, 2.8))

    # 分离器底部粗甲醇液相到精馏塔
    draw_stream_arrow(76, 52, 76, 30, f"粗甲醇液相\n{wan_ton(mass_flows_t_a['crude_methanol']):.2f} 万吨/a", c_meoh, width=mass_line_width(mass_flows_t_a["crude_methanol"]), label_offset=(6.0, 0))

    # 精馏塔产品输出：聚合级精甲醇
    draw_stream_arrow(83, 23, 98, 23, f"聚合级精甲醇\n{wan_ton(mass_flows_t_a['methanol_product']):.2f} 万吨/a (>=99.85%)", c_meoh, width=mass_line_width(mass_flows_t_a["methanol_product"]), label_offset=(0, 3.2))

    # 精馏塔副产水闭环循环至制氢站 (闭环水循环)
    water_reuse_share = mass_flows_t_a["recycle_water"] / mass_flows_t_a["electrolyzer_water"] * 100.0
    draw_stream_arrow(69, 21, 22, 33, f"精馏产水回用至电解槽 ({water_reuse_share:.1f}%)\n{wan_ton(mass_flows_t_a['recycle_water']):.2f} 万吨/a", c_water, width=mass_line_width(mass_flows_t_a["recycle_water"]), rad=-0.22, label_offset=(0, -4.5))

    # 电解槽总进水汇总标记
    ax.text(13.5, 47.5, f"PEM 电解槽总进水\n{wan_ton(mass_flows_t_a['electrolyzer_water']):.2f} 万吨/a\n[新鲜水 {water_fresh_share:.1f}% + 回用水 {water_reuse_share:.1f}%]",
            fontsize=8.0, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#ebf5fb", edgecolor="#2980b9", linewidth=1.0),
            color="#2980b9", zorder=6)

    # --------------------------------------------------------------------------
    # 底部图例与工程核心指标看板
    # --------------------------------------------------------------------------
    board_rect = patches.FancyBboxPatch((4, 2), 92, 10, boxstyle="round,pad=0.6,rounding_size=1.0",
                                        facecolor="#ffffff", edgecolor="#bdc3c7", linewidth=1.2, zorder=2)
    ax.add_patch(board_rect)

    ax.text(6, 9.5, "【锚点 B：10 万吨/年主物流与能耗】", fontsize=9.5, fontweight="bold", color="#2c3e50")
    col1 = f"CO2 捕集 {wan_ton(mass_flows_t_a['fresh_co2']):.2f} 万吨/a\n绿氢 {wan_ton(mass_flows_t_a['fresh_h2']):.2f} 万吨/a"
    col2 = f"新鲜水 {wan_ton(mass_flows_t_a['fresh_water']):.2f} 万吨/a\n精馏水回用 {wan_ton(mass_flows_t_a['recycle_water']):.2f} 万吨/a"
    col3 = f"循环气 {wan_ton(mass_flows_t_a['recycle_gas']):.2f} 万吨/a\n驰放气 {wan_ton(mass_flows_t_a['purge_gas']):.3f} 万吨/a\n副产氧 {wan_ton(mass_flows_t_a['oxygen']):.2f} 万吨/a"
    col4 = f"总电耗 {total_energy_100m_kwh:.3f} 亿 kWh/a\n捕集 {annual_energy_100m_kwh['capture']:.3f} | 制氢 {annual_energy_100m_kwh['electrolysis']:.3f}\n循环 {annual_energy_100m_kwh['recycle_compression']:.3f} | 精馏 {annual_energy_100m_kwh['distillation']:.3f} 亿 kWh/a"

    ax.text(7, 5.5, col1, fontsize=7.2, va="center", color="#34495e")
    ax.text(29, 5.5, col2, fontsize=7.2, va="center", color="#34495e")
    ax.text(51, 5.5, col3, fontsize=7.2, va="center", color="#34495e")
    ax.text(73, 5.5, col4, fontsize=6.8, va="center", color="#34495e")

    plt.tight_layout()

    # 确保输出目录存在并保存图表
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[锚点B] f_green={f_green:.4f}, r_purge={r_purge:.5f}, GWP={scenario['gwp_net']:.2f} kg CO2e/t, LCOM={scenario['lcom_policy_adjusted']:.2f} 元/t")
    print("[10万吨/年主物流报告]")
    for label, key in (
        ("新鲜 CO2 捕集", "fresh_co2"), ("电解绿氢", "fresh_h2"),
        ("新鲜脱盐水", "fresh_water"), ("精馏产水回用", "recycle_water"),
        ("电解槽总进水", "electrolyzer_water"), ("电解副产纯氧", "oxygen"),
        ("反应器入口", "reactor_inlet"), ("反应器出口", "reactor_outlet"),
        ("未反应气循环回流", "recycle_gas"), ("驰放气", "purge_gas"),
        ("粗甲醇液相", "crude_methanol"), ("精甲醇产品", "methanol_product"),
    ):
        print(f"  {label}: {mass_flows_t_a[key]:,.2f} t/a")
    print(f"[年电耗] 总计 {scenario['e_total_kwh'] * annual_methanol_t:,.0f} kWh/a ({total_energy_100m_kwh:.3f} 亿 kWh/a)")
    for label, key in (("捕集压缩", "capture"), ("电解制氢", "electrolysis"), ("循环压缩", "recycle_compression"), ("精馏", "distillation")):
        print(f"  {label}: {energy_kwh_per_t[key] * annual_methanol_t:,.0f} kWh/a ({annual_energy_100m_kwh[key]:.3f} 亿 kWh/a)")
    print(f"[成功] 工艺物质能量流向拓扑图已保存至: {output_path}")


if __name__ == "__main__":
    draw_mfa_process_flow()
