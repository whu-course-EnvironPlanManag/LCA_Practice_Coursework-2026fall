# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 4（学生随堂实训版）
脚本名称：task4_process_sankey_flow.py
功能描述：
  基于任务 3 求解出的帕累托拐点（锚点 B）工程通量基准数据，绘制工业园区
    10 万吨/年绿色甲醇系统物质流（MFA）与能量流（EFA）全流程拓扑图。
  包含：
    1. 物质流向与质量通量 (万吨/年)；
        2. 采用 ELK 布局的左至右工艺流程及 PEM 制氢分支；
        3. 未反应气循环与精馏产水回用闭环；
    4. 各工段综合电耗分布 (亿 kWh/年)；
        5. Mermaid 源码及可选 PNG 渲染输出。
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

import shutil
import subprocess


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
#   2. 使用 Mermaid ELK 布局，清晰表达碳捕集、预热、合成、分离、精馏主流程与 PEM 制氢分支；
#   3. 明确标识未反应气闭环内循环流与精馏副产生成水回用流；
#   4. 输出 Mermaid 源码；检测到 mmdc 时渲染 figures_output/fig1_mfa_process_flow.png。
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
    def wan_ton(flow_t_a):
        return flow_t_a / 10000.0

    def energy_label(component):
        value = annual_energy_100m_kwh[component]
        share = value / total_energy_100m_kwh * 100.0
        return f"电耗: {value:.3f} 亿 kWh/a ({share:.1f}%)"

    water_fresh_share = mass_flows_t_a["fresh_water"] / mass_flows_t_a["electrolyzer_water"] * 100.0
    water_reuse_share = mass_flows_t_a["recycle_water"] / mass_flows_t_a["electrolyzer_water"] * 100.0
    recycle_mass_ratio = mfa["recycle_ratio_mass"]
    output_root, output_ext = os.path.splitext(output_path)
    mermaid_path = output_root + ".mmd"
    mermaid = f'''---
config:
  layout: elk
  flowchart:
    defaultRenderer: elk
    curve: linear
        diagramPadding: 64
    nodeSpacing: 90
    rankSpacing: 120
  theme: base
  themeVariables:
    fontFamily: "Microsoft YaHei, Noto Sans CJK SC, sans-serif"
    primaryColor: "#f4f7f8"
    primaryTextColor: "#19313a"
    primaryBorderColor: "#45616b"
    lineColor: "#536a73"
    clusterBkg: "#ffffff"
    clusterBorder: "#b8c8ce"
---
flowchart LR
    subgraph main["工业园区 10 万吨/年 CCU-PtM 主工艺流程<br/>锚点 B：绿电 {f_green:.2%} | 驰放比 {r_purge:.2%} | 碳利用率 {scenario['eta_carbon']:.2f}% | 全厂电耗 {total_energy_100m_kwh:.3f} 亿 kWh/a"]
        direction LR
        capture["CO₂ 捕集与压缩<br/>MEA 吸收；出口 5.0 MPa<br/>电耗 {annual_energy_100m_kwh['capture']:.3f} 亿 kWh/a"]
        preheat["进料混合预热器<br/>新鲜进料 + 循环气<br/>230 ℃；5.0 MPa"]
        reactor["甲醇合成反应器<br/>Cu/ZnO/Al₂O₃ 固定床<br/>单程转化率 25%"]
        separator["冷凝与气液分离<br/>质量循环比 {recycle_mass_ratio:.2f}:1<br/>驰放比 {r_purge:.2%}<br/>循环压缩电耗 {annual_energy_100m_kwh['recycle_compression']:.3f} 亿 kWh/a"]
        distill["双塔精馏系统<br/>常压脱轻 + 加压脱水<br/>产品纯度 ≥99.85 wt%<br/>电耗 {annual_energy_100m_kwh['distillation']:.3f} 亿 kWh/a"]
        product["聚合级精甲醇<br/>{wan_ton(mass_flows_t_a['methanol_product']):.2f} 万吨/a"]
        capture -->|"捕集 CO₂ {wan_ton(mass_flows_t_a['fresh_co2']):.2f} 万吨/a"| preheat
        preheat -->|"反应器入口 {wan_ton(mass_flows_t_a['reactor_inlet']):.2f} 万吨/a"| reactor
        reactor -->|"反应器出口 {wan_ton(mass_flows_t_a['reactor_outlet']):.2f} 万吨/a"| separator
        separator -->|"粗甲醇液相 {wan_ton(mass_flows_t_a['crude_methanol']):.2f} 万吨/a"| distill
        distill -->|"{wan_ton(mass_flows_t_a['methanol_product']):.2f} 万吨/a；纯度 ≥99.85%"| product
    end

    subgraph hydrogen["PEM 电解水制氢分支"]
        direction TB
        freshwater["新鲜脱盐水<br/>{wan_ton(mass_flows_t_a['fresh_water']):.2f} 万吨/a ({water_fresh_share:.1f}%)"]
        pem["PEM 电解槽<br/>电解绿氢 {wan_ton(mass_flows_t_a['fresh_h2']):.2f} 万吨/a<br/>总进水 {wan_ton(mass_flows_t_a['electrolyzer_water']):.2f} 万吨/a<br/>电耗 {annual_energy_100m_kwh['electrolysis']:.3f} 亿 kWh/a"]
        oxygen["阳极副产纯氧（外售）<br/>{wan_ton(mass_flows_t_a['oxygen']):.2f} 万吨/a"]
        freshwater -->|"补水"| pem
        pem -->|"副产氧"| oxygen
    end

    fluegas["工业点源烟气<br/>CO₂ 原料"] --> capture
    pem -->|"电解绿氢 {wan_ton(mass_flows_t_a['fresh_h2']):.2f} 万吨/a"| preheat
    separator -.->|"循环气回流 {1.0-r_purge:.2%}<br/>{wan_ton(mass_flows_t_a['recycle_gas']):.2f} 万吨/a"| preheat
    separator -->|"驰放尾气 {r_purge:.2%}<br/>{wan_ton(mass_flows_t_a['purge_gas']):.3f} 万吨/a；送末端处置"| purge["驰放气处理"]
    distill -.->|"精馏产水回用 {water_reuse_share:.1f}%<br/>{wan_ton(mass_flows_t_a['recycle_water']):.2f} 万吨/a"| pem

    classDef co2 fill:#fff3e8,stroke:#d97706,color:#713f12,stroke-width:1.5px
    classDef hydrogen fill:#eaf7ef,stroke:#25834b,color:#174b2d,stroke-width:1.5px
    classDef water fill:#eaf4fb,stroke:#2879a5,color:#174d69,stroke-width:1.5px
    classDef process fill:#f3f6f7,stroke:#45616b,color:#19313a,stroke-width:1.5px
    classDef product fill:#f6eff8,stroke:#8a4c9e,color:#542b64,stroke-width:1.5px
    classDef purge fill:#fff0ef,stroke:#c43d3d,color:#742626,stroke-width:1.5px
    class capture co2
    class freshwater water
    class pem,oxygen hydrogen
    class preheat,reactor,separator,fluegas process
    class distill,product product
    class purge purge
    linkStyle 0 stroke:#d97706,stroke-width:2px
    linkStyle 1,2,3 stroke:#536a73,stroke-width:2px
    linkStyle 4 stroke:#8a4c9e,stroke-width:2px
    linkStyle 5 stroke:#2879a5,stroke-width:2px
    linkStyle 6,8 stroke:#25834b,stroke-width:2px
    linkStyle 7 stroke:#d97706,stroke-width:2px
    linkStyle 9 stroke:#148a78,stroke-width:2px,stroke-dasharray:6 4
    linkStyle 10 stroke:#c43d3d,stroke-width:2px
    linkStyle 11 stroke:#2879a5,stroke-width:2px,stroke-dasharray:6 4
'''
    os.makedirs(os.path.dirname(os.path.abspath(mermaid_path)), exist_ok=True)
    with open(mermaid_path, "w", encoding="utf-8") as mermaid_file:
        mermaid_file.write(mermaid)

    mmdc = shutil.which("mmdc")
    if mmdc:
        from PIL import Image

        rendered_path = output_root + ".mmdc" + output_ext
        try:
            subprocess.run(
                [mmdc, "-i", mermaid_path, "-o", rendered_path, "-b", "white", "-s", "2"],
                check=True,
            )
            with Image.open(rendered_path) as rendered_image:
                rendered_image.save(output_path, dpi=(300, 300))
        finally:
            if os.path.exists(rendered_path):
                os.remove(rendered_path)
    else:
        print("[提示] Mermaid 源码已生成；未检测到 mmdc，PNG 未重新渲染。")
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
    print(f"[成功] Mermaid ELK 工艺图源码已保存至: {mermaid_path}")
    if mmdc:
        print(f"[成功] 工艺物质能量流向图已渲染至: {output_path}")


if __name__ == "__main__":
    draw_mfa_process_flow()
