# -*- coding: utf-8 -*-
"""
《环境规划与管理》第十讲实训任务
作者：帕娜尔·阿克木 (Group 02)
任务：帕累托多目标优化与决策前沿分析

功能说明：
  耦合 MFA-LCA-TEA-政策引擎，在绿电比例 f_green 和驰放比 r_purge 二维调控空间下，
  遍历 3000 组工况，提取非支配帕累托前沿，并用乌托邦理想点法定位最优决策拐点。

核心算法：
  1. 网格采样：f_green (60 档) × r_purge (50 档) = 3000 工况
  2. 非支配排序：剔除被支配解和法规一票否决解
  3. 乌托邦距离：归一化后到理想点 (0,0) 的欧氏距离最小化
  4. 三大锚点：成本极小 A、帕累托拐点 B、深度负碳 C
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

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 导入任务 2 政策引擎
try:
    from task2_policy_vibe_engine import evaluate_policy_compliance
except ImportError:
    from code_implementation.task2_policy_vibe_engine import evaluate_policy_compliance

# 中文字体配置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def locate_output_dir():
    """定位图表输出目录"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    paths_to_try = [
        os.path.join(script_dir, "..", "figures_output"),
        os.path.join("figures_output"),
        os.path.join("..", "figures_output")
    ]
    for p in paths_to_try:
        try:
            os.makedirs(p, exist_ok=True)
            return p
        except:
            continue
    return "."


# =============================================================================
# 第一部分：MFA-LCA-TEA 耦合仿真模型
# =============================================================================
def simulate_system(f_green, r_purge):
    """
    输入调控参数，输出全套技术经济指标

    参数:
        f_green: 绿电消纳比例 [0, 1]
        r_purge: 驰放分流比 [0.004, 0.045]

    返回:
        dict: 包含 GWP、LCOM、合规标签等关键字段
    """
    # ---- MFA 物料平衡 ----
    # 碳利用率随驰放比变化 (驰放越大，碳损失越多)
    eta_carbon_base = 0.960
    carbon_loss = 1.0 - eta_carbon_base * (1.0 - (r_purge - 0.010) * 3.80)
    carbon_loss = np.clip(carbon_loss, 0.015, 0.250)
    eta_carbon = 1.0 - carbon_loss

    # 原料消耗 (随碳利用率调整)
    co2_feed_kg = 1423.0 * (eta_carbon_base / eta_carbon)
    h2_feed_kg = 198.0 * (eta_carbon_base / eta_carbon)

    # ---- 能量消耗 ----
    # 电解制氢: 52 kWh/kg H2
    energy_h2 = h2_feed_kg * 52.0
    # CO2 捕集压缩: 255 kWh/t CO2 (按基准比例缩放)
    energy_co2 = 255.0 * (co2_feed_kg / 1423.0)
    # 循环压缩: 驰放比越小，循环量越大，能耗越高
    energy_recycle = 155.0 * ((0.010 / r_purge) ** 0.65)
    # 精馏分离: 固定 120 kWh/t
    energy_distill = 120.0
    energy_total = energy_h2 + energy_co2 + energy_recycle + energy_distill

    # ---- LCA 碳足迹 ----
    # 电网排放因子 (绿电 + 火电混合)
    ef_grid = f_green * 0.035 + (1.0 - f_green) * 0.550
    emission_power = energy_total * ef_grid
    # 基础设施与驰放气逸散
    emission_infra = 95.0 + (r_purge - 0.010) * 1200.0
    # CO2 原料固定信用 (负排放)
    credit_co2_feed = co2_feed_kg * 1.000
    # 副产氧信用
    credit_o2 = 95.0 * (h2_feed_kg / 198.0)
    # 净碳足迹
    gwp_net = emission_power + emission_infra - credit_co2_feed - credit_o2

    # ---- TEA 成本核算 ----
    # 电价 (绿电 + 火电混合)
    price_elec = f_green * 0.18 + (1.0 - f_green) * 0.42
    cost_electricity = energy_total * price_elec

    # CAPEX 年金摊销 (基础 + 储能缓冲 + 循环压缩增量)
    capex_base = 835.2
    capex_storage = 680.0 * (f_green ** 2.80)
    capex_recycle = 45.0 * max(0.0, ((0.010 / r_purge) ** 0.80 - 1.0))
    cost_capex = capex_base + capex_storage + capex_recycle

    # CO2 捕集费
    cost_co2_capture = (co2_feed_kg / 1000.0) * 260.0
    # 水耗与运维
    cost_water_om = 65.0 + 285.0
    # 氧气外售抵扣 (负成本)
    credit_o2_sale = -316.8 * (h2_feed_kg / 198.0)

    # 基础 LCOM
    lcom_base = cost_electricity + cost_capex + cost_co2_capture + cost_water_om + credit_o2_sale

    # ---- 政策规制引擎 ----
    policy_result = evaluate_policy_compliance(
        gwp_net=gwp_net,
        base_lcom=lcom_base,
        e_total_kwh=energy_total,
        f_green=f_green,
        r_purge=r_purge
    )

    return {
        "f_green": f_green,
        "r_purge": r_purge,
        "eta_carbon_pct": eta_carbon * 100.0,
        "energy_total_kwh": energy_total,
        "gwp_net": gwp_net,
        "lcom_base": lcom_base,
        "lcom_adjusted": policy_result["lcom_adjusted"],
        "mac_adjusted": policy_result["mac_adjusted"],
        "compliance": policy_result["compliance"]
    }


# =============================================================================
# 第二部分：非支配排序与锚点提取
# =============================================================================
def find_pareto_frontier(data_df):
    """
    从合规方案中提取帕累托前沿，并标定三大决策锚点

    参数:
        data_df: 包含所有工况模拟结果的 DataFrame

    返回:
        pareto_df: 帕累托前沿 DataFrame
        anchors: 三大锚点字典 {A: 成本极小, B: 拐点, C: 深度负碳}
    """
    # 过滤掉一票否决方案
    valid_df = data_df[data_df["compliance"] != "Redline_Vetoed"].copy().reset_index(drop=True)

    # 提取目标空间 (GWP, LCOM)
    objectives = valid_df[["gwp_net", "lcom_adjusted"]].values
    n_solutions = objectives.shape[0]

    # 非支配排序: 标记每个解是否被支配
    is_pareto = np.ones(n_solutions, dtype=bool)

    for i in range(n_solutions):
        if is_pareto[i]:
            # 检查是否存在其他解 j 支配解 i
            # 支配条件: j 的所有目标 <= i 的对应目标，且至少一个严格小于
            dominated_by_j = np.all(objectives <= objectives[i], axis=1) & np.any(objectives < objectives[i], axis=1)
            if np.any(dominated_by_j):
                is_pareto[i] = False

    # 提取帕累托前沿
    pareto_df = valid_df[is_pareto].copy().sort_values("gwp_net").reset_index(drop=True)

    # 归一化到 [0, 1] 区间
    gwp_min, gwp_max = pareto_df["gwp_net"].min(), pareto_df["gwp_net"].max()
    lcom_min, lcom_max = pareto_df["lcom_adjusted"].min(), pareto_df["lcom_adjusted"].max()

    norm_gwp = (pareto_df["gwp_net"] - gwp_min) / max(gwp_max - gwp_min, 1e-6)
    norm_lcom = (pareto_df["lcom_adjusted"] - lcom_min) / max(lcom_max - lcom_min, 1e-6)

    # 乌托邦理想点距离 (到 (0,0) 的欧氏距离)
    pareto_df["utopia_dist"] = np.sqrt(norm_gwp ** 2 + norm_lcom ** 2)

    # 提取三大锚点
    anchor_a = pareto_df.loc[pareto_df["lcom_adjusted"].idxmin()]  # 成本极小
    anchor_b = pareto_df.loc[pareto_df["utopia_dist"].idxmin()]    # 帕累托拐点 (Knee Point)
    anchor_c = pareto_df.loc[pareto_df["gwp_net"].idxmin()]        # 深度负碳极限

    anchors = {
        "A_Cost_Min": anchor_a,
        "B_Knee_Point": anchor_b,
        "C_Deep_Negative": anchor_c
    }

    return pareto_df, anchors


# =============================================================================
# 第三部分：主程序与可视化
# =============================================================================
if __name__ == "__main__":
    print("=" * 90)
    print("《环境规划与管理》任务 3: MFA-LCA-TEA-Policy 多目标帕累托寻优")
    print("学生: 帕娜尔·阿克木 | Group 02")
    print("=" * 90)

    # ---- 网格采样 ----
    print("\n[1/4] 网格采样遍历...")
    f_green_array = np.linspace(0.0, 1.0, 60)
    r_purge_array = np.linspace(0.004, 0.045, 50)

    all_records = []
    total_scenarios = len(f_green_array) * len(r_purge_array)

    for fg in f_green_array:
        for rp in r_purge_array:
            record = simulate_system(fg, rp)
            all_records.append(record)

    df_all = pd.DataFrame(all_records)
    print(f"  完成 {len(df_all)} 组工况模拟 (共 {total_scenarios} 组)")

    # ---- 帕累托前沿提取 ----
    print("\n[2/4] 提取帕累托前沿与决策锚点...")
    df_pareto, dict_anchors = find_pareto_frontier(df_all)
    print(f"  识别出 {len(df_pareto)} 个非支配帕累托最优解")

    # ---- 结果输出 ----
    print("\n[3/4] 三大决策锚点比选表 (请填入报告第 5.3 节)")
    print("-" * 90)

    anchor_labels = {
        "A_Cost_Min": "锚点 A (成本极小化 - 保守型)",
        "B_Knee_Point": "锚点 B (帕累托拐点 - 主推基准)",
        "C_Deep_Negative": "锚点 C (深度负碳 - 国际航运)"
    }

    summary_rows = []
    for key, row in dict_anchors.items():
        summary_rows.append({
            "方案": anchor_labels[key],
            "绿电比例": f"{row['f_green']*100:.1f}%",
            "驰放比": f"{row['r_purge']*100:.2f}%",
            "碳利用率": f"{row['eta_carbon_pct']:.2f}%",
            "GWP净碳足迹": f"{row['gwp_net']:.1f} kg/t",
            "基础LCOM": f"{row['lcom_base']:.1f} 元/t",
            "调整后LCOM": f"{row['lcom_adjusted']:.1f} 元/t",
            "MAC": f"{row['mac_adjusted']:.1f} 元/tCO2e" if not np.isnan(row['mac_adjusted']) else "NaN",
            "合规标签": row["compliance"]
        })

    print(pd.DataFrame(summary_rows).to_string(index=False))
    print("-" * 90)

    # ---- 可视化 ----
    print("\n[4/4] 绘制帕累托决策前沿图...")
    fig_dir = locate_output_dir()
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(15, 6.2), dpi=300)

    # 分类着色
    df_vetoed = df_all[df_all["compliance"] == "Redline_Vetoed"]
    df_domestic = df_all[df_all["compliance"] == "Domestic_Compliant"]
    df_rediii = df_all[df_all["compliance"] == "RED_III_RFNBO_Certified"]

    # 子图 (a): 目标空间
    ax_left.scatter(df_vetoed["gwp_net"], df_vetoed["lcom_adjusted"],
                    c="#d95f02", marker="x", s=14, alpha=0.30, label="一票否决方案")
    ax_left.scatter(df_domestic["gwp_net"], df_domestic["lcom_adjusted"],
                    c="#7570b3", marker="o", s=14, alpha=0.35, label="国内合规方案")
    ax_left.scatter(df_rediii["gwp_net"], df_rediii["lcom_adjusted"],
                    c="#66a61e", marker="o", s=16, alpha=0.45, label="欧盟RED III认证")

    # 帕累托前沿线
    ax_left.plot(df_pareto["gwp_net"], df_pareto["lcom_adjusted"],
                 color="#e7298a", linewidth=2.8, linestyle="-", label="帕累托前沿")

    # 政策红线
    ax_left.axvline(2600.0, color="#b2182b", linestyle="--", linewidth=1.2, label="煤制甲醇基准红线 (2600)")
    ax_left.axvline(561.2, color="#1b7837", linestyle="-.", linewidth=1.2, label="RED III准入限值 (561.2)")
    ax_left.axvline(0.0, color="#525252", linestyle=":", linewidth=1.0, label="零碳分界线")

    # 锚点标记
    marker_styles = {
        "A_Cost_Min": ("*", "#1b9e77", 180, "锚点A: 成本极小"),
        "B_Knee_Point": ("D", "#000000", 140, "锚点B: 帕累托拐点"),
        "C_Deep_Negative": ("^", "#08519c", 150, "锚点C: 深度负碳")
    }

    for key, (marker, color, size, label) in marker_styles.items():
        pt = dict_anchors[key]
        ax_left.scatter(pt["gwp_net"], pt["lcom_adjusted"],
                        marker=marker, c=color, s=size, edgecolors="white", linewidth=1.5, zorder=10, label=label)

    ax_left.set_title("(a) 帕累托前沿: 碳足迹-成本权衡", fontsize=11.5, fontweight="bold", pad=12)
    ax_left.set_xlabel("全生命周期净碳足迹 GWP_net (kg CO2e/t)", fontsize=10.5)
    ax_left.set_ylabel("政策调整后成本 LCOM_adjusted (元/t)", fontsize=10.5)
    ax_left.grid(True, linestyle=":", alpha=0.6)
    ax_left.legend(loc="upper left", fontsize=8.0, framealpha=0.92)

    # 子图 (b): 决策变量空间
    scatter_b = ax_right.scatter(df_pareto["f_green"] * 100.0, df_pareto["r_purge"] * 100.0,
                                  c=df_pareto["lcom_adjusted"], cmap="viridis_r", s=50, edgecolors="black", linewidth=0.5)
    cbar = plt.colorbar(scatter_b, ax=ax_right, pad=0.02)
    cbar.set_label("调整后成本 LCOM (元/t)", fontsize=9.5)

    for key, (marker, color, size, label) in marker_styles.items():
        pt = dict_anchors[key]
        ax_right.scatter(pt["f_green"] * 100.0, pt["r_purge"] * 100.0,
                         marker=marker, c=color, s=size, edgecolors="white", linewidth=1.5, zorder=10, label=label)

    ax_right.set_title("(b) 帕累托解的工程调控参数分布", fontsize=11.5, fontweight="bold", pad=12)
    ax_right.set_xlabel("绿电消纳比例 f_green (%)", fontsize=10.5)
    ax_right.set_ylabel("驰放分流比 r_purge (%)", fontsize=10.5)
    ax_right.grid(True, linestyle=":", alpha=0.6)
    ax_right.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    plt.tight_layout()
    output_path = os.path.join(fig_dir, "fig2_pareto_decision_frontier.png")
    plt.savefig(output_path, dpi=300)
    print(f"  图表已保存: {output_path}")

    print("\n" + "=" * 90)
    print("[完成] 帕累托多目标优化求解完毕，可接入任务4工艺流程可视化")
    print("=" * 90)
