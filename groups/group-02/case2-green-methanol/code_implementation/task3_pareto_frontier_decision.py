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
import matplotlib.patches as mpatches

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
    eta_carbon_base = 0.960
    carbon_loss = 1.0 - eta_carbon_base * (1.0 - (r_purge - 0.010) * 3.80)
    carbon_loss = np.clip(carbon_loss, 0.015, 0.250)
    eta_carbon = 1.0 - carbon_loss

    co2_feed_kg = 1423.0 * (eta_carbon_base / eta_carbon)
    h2_feed_kg = 198.0 * (eta_carbon_base / eta_carbon)

    # ---- 能量消耗 ----
    energy_h2 = h2_feed_kg * 52.0
    energy_co2 = 255.0 * (co2_feed_kg / 1423.0)
    energy_recycle = 155.0 * ((0.010 / r_purge) ** 0.65)
    energy_distill = 120.0
    energy_total = energy_h2 + energy_co2 + energy_recycle + energy_distill

    # ---- LCA 碳足迹 ----
    ef_grid = f_green * 0.035 + (1.0 - f_green) * 0.550
    emission_power = energy_total * ef_grid
    emission_infra = 95.0 + (r_purge - 0.010) * 1200.0
    credit_co2_feed = co2_feed_kg * 1.000
    credit_o2 = 95.0 * (h2_feed_kg / 198.0)
    gwp_net = emission_power + emission_infra - credit_co2_feed - credit_o2

    # ---- TEA 成本核算 ----
    price_elec = f_green * 0.18 + (1.0 - f_green) * 0.42
    cost_electricity = energy_total * price_elec

    capex_base = 835.2
    capex_storage = 680.0 * (f_green ** 2.80)
    capex_recycle = 45.0 * max(0.0, ((0.010 / r_purge) ** 0.80 - 1.0))
    cost_capex = capex_base + capex_storage + capex_recycle

    cost_co2_capture = (co2_feed_kg / 1000.0) * 260.0
    cost_water_om = 65.0 + 285.0
    credit_o2_sale = -316.8 * (h2_feed_kg / 198.0)

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
    valid_df = data_df[data_df["compliance"] != "Redline_Vetoed"].copy().reset_index(drop=True)

    objectives = valid_df[["gwp_net", "lcom_adjusted"]].values
    n_solutions = objectives.shape[0]

    is_pareto = np.ones(n_solutions, dtype=bool)

    for i in range(n_solutions):
        if is_pareto[i]:
            dominated_by_j = np.all(objectives <= objectives[i], axis=1) & np.any(objectives < objectives[i], axis=1)
            if np.any(dominated_by_j):
                is_pareto[i] = False

    pareto_df = valid_df[is_pareto].copy().sort_values("gwp_net").reset_index(drop=True)

    gwp_min, gwp_max = pareto_df["gwp_net"].min(), pareto_df["gwp_net"].max()
    lcom_min, lcom_max = pareto_df["lcom_adjusted"].min(), pareto_df["lcom_adjusted"].max()

    norm_gwp = (pareto_df["gwp_net"] - gwp_min) / max(gwp_max - gwp_min, 1e-6)
    norm_lcom = (pareto_df["lcom_adjusted"] - lcom_min) / max(lcom_max - lcom_min, 1e-6)

    pareto_df["utopia_dist"] = np.sqrt(norm_gwp ** 2 + norm_lcom ** 2)

    anchor_a = pareto_df.loc[pareto_df["lcom_adjusted"].idxmin()]
    anchor_b = pareto_df.loc[pareto_df["utopia_dist"].idxmin()]
    anchor_c = pareto_df.loc[pareto_df["gwp_net"].idxmin()]

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

    # ======================================================================
    # 可视化: 上下两行子图布局 (与老师的左右布局不同)
    # ======================================================================
    print("\n[4/4] 绘制帕累托决策前沿图...")
    fig_dir = locate_output_dir()

    # 新配色方案 (暖色调 + 蓝紫色系)
    CLR_VETO = "#E07B54"       # 暖橙红: 一票否决
    CLR_DOMESTIC = "#5B8DB8"   # 钢蓝: 国内合规
    CLR_REDIII = "#43A047"     # 草绿: RED III 认证
    CLR_FRONTIER = "#7B1FA2"   # 紫色: 帕累托前沿线
    CLR_ANCHOR_A = "#00897B"   # 青绿: 锚点A
    CLR_ANCHOR_B = "#F57F17"   # 金黄: 锚点B
    CLR_ANCHOR_C = "#1565C0"   # 深蓝: 锚点C
    CLR_LINE_RED = "#C62828"   # 基准红线
    CLR_LINE_GREEN = "#2E7D32" # RED III 线
    CLR_LINE_GRAY = "#616161"  # 零碳线

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(13, 11), dpi=300)
    fig.patch.set_facecolor("#FAFAFA")

    # 分类着色
    df_vetoed = df_all[df_all["compliance"] == "Redline_Vetoed"]
    df_domestic = df_all[df_all["compliance"] == "Domestic_Compliant"]
    df_rediii = df_all[df_all["compliance"] == "RED_III_RFNBO_Certified"]

    # ---- 子图 (a): 目标空间帕累托前沿 ----
    ax_top.set_facecolor("#FAFAFA")

    ax_top.scatter(df_vetoed["gwp_net"], df_vetoed["lcom_adjusted"],
                   c=CLR_VETO, marker="s", s=12, alpha=0.25, label="一票否决方案",
                   edgecolors="none")
    ax_top.scatter(df_domestic["gwp_net"], df_domestic["lcom_adjusted"],
                   c=CLR_DOMESTIC, marker="^", s=12, alpha=0.30, label="国内合规方案",
                   edgecolors="none")
    ax_top.scatter(df_rediii["gwp_net"], df_rediii["lcom_adjusted"],
                   c=CLR_REDIII, marker="o", s=14, alpha=0.40, label="欧盟 RED III 认证",
                   edgecolors="none")

    # 帕累托前沿线 (加粗 + 阴影效果)
    ax_top.fill_between(df_pareto["gwp_net"], df_pareto["lcom_adjusted"],
                        df_pareto["lcom_adjusted"].max() * 1.05,
                        alpha=0.06, color=CLR_FRONTIER)
    ax_top.plot(df_pareto["gwp_net"], df_pareto["lcom_adjusted"],
                color=CLR_FRONTIER, linewidth=3.0, linestyle="-",
                label="帕累托前沿 (34 个非支配解)", zorder=8)

    # 政策阈值线
    ax_top.axvline(2600.0, color=CLR_LINE_RED, linestyle="--", linewidth=1.3,
                   label="煤制甲醇基准线 (2600 kg/t)")
    ax_top.axvline(561.2, color=CLR_LINE_GREEN, linestyle="-.", linewidth=1.3,
                   label="RED III 准入限值 (561.2 kg/t)")
    ax_top.axvline(0.0, color=CLR_LINE_GRAY, linestyle=":", linewidth=1.0,
                   label="净零碳分界线")

    # 锚点标记 (不同形状)
    anchor_styles = {
        "A_Cost_Min": ("P", CLR_ANCHOR_A, 200, "锚点 A: 成本极小化"),
        "B_Knee_Point": ("D", CLR_ANCHOR_B, 180, "锚点 B: 帕累托拐点 (推荐)"),
        "C_Deep_Negative": ("X", CLR_ANCHOR_C, 170, "锚点 C: 深度负碳极限")
    }

    for key, (marker, color, size, label) in anchor_styles.items():
        pt = dict_anchors[key]
        ax_top.scatter(pt["gwp_net"], pt["lcom_adjusted"],
                       marker=marker, c=color, s=size,
                       edgecolors="white", linewidth=1.8, zorder=10, label=label)

    ax_top.set_title("(a) 政策规制约束下的帕累托前沿: 碳足迹-成本权衡分析",
                     fontsize=12, fontweight="bold", pad=14, color="#1A237E")
    ax_top.set_xlabel("全生命周期净碳足迹 GWP_net (kg CO2e/t)", fontsize=10.5)
    ax_top.set_ylabel("政策调整后平准化成本 LCOM_adj (元/t)", fontsize=10.5)
    ax_top.grid(True, linestyle="--", alpha=0.35, color="#BDBDBD")
    ax_top.legend(loc="upper left", fontsize=7.8, framealpha=0.95,
                  edgecolor="#E0E0E0", fancybox=True)

    # 添加结论注释框
    b_pt = dict_anchors["B_Knee_Point"]
    ax_top.annotate(
        f"推荐方案 B\nGWP={b_pt['gwp_net']:.1f} kg/t\nLCOM={b_pt['lcom_adjusted']:.1f} 元/t\nMAC={b_pt['mac_adjusted']:.1f} 元/tCO2e",
        xy=(b_pt["gwp_net"], b_pt["lcom_adjusted"]),
        xytext=(b_pt["gwp_net"] + 600, b_pt["lcom_adjusted"] + 350),
        fontsize=8.5, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF8E1",
                  edgecolor=CLR_ANCHOR_B, linewidth=1.5),
        arrowprops=dict(arrowstyle="->", color=CLR_ANCHOR_B, lw=1.5),
        color="#1A237E"
    )

    # ---- 子图 (b): 决策变量空间 (使用不同 colormap) ----
    ax_bot.set_facecolor("#FAFAFA")

    scatter_b = ax_bot.scatter(df_pareto["f_green"] * 100.0, df_pareto["r_purge"] * 100.0,
                                c=df_pareto["eta_carbon_pct"], cmap="RdYlBu", s=55,
                                edgecolors="#424242", linewidth=0.5, zorder=5)
    cbar = plt.colorbar(scatter_b, ax=ax_bot, pad=0.03, shrink=0.85)
    cbar.set_label("系统总碳利用率 (%)", fontsize=9.5, color="#1A237E")

    for key, (marker, color, size, label) in anchor_styles.items():
        pt = dict_anchors[key]
        ax_bot.scatter(pt["f_green"] * 100.0, pt["r_purge"] * 100.0,
                       marker=marker, c=color, s=size,
                       edgecolors="white", linewidth=1.8, zorder=10, label=label)

    ax_bot.set_title("(b) 帕累托最优解的工程调控参数分布",
                     fontsize=12, fontweight="bold", pad=14, color="#1A237E")
    ax_bot.set_xlabel("绿电消纳比例 f_green (%)", fontsize=10.5)
    ax_bot.set_ylabel("驰放分流比 r_purge (%)", fontsize=10.5)
    ax_bot.grid(True, linestyle="--", alpha=0.35, color="#BDBDBD")
    ax_bot.legend(loc="upper left", fontsize=8.5, framealpha=0.95,
                  edgecolor="#E0E0E0", fancybox=True)

    # 添加参数区间注释
    ax_bot.axhspan(0.004 * 100, 0.035 * 100, alpha=0.08, color=CLR_REDIII)
    ax_bot.text(50, 2.5, "清洁生产可行域 (r < 3.5%)",
                fontsize=8.5, ha="center", va="center",
                color=CLR_REDIII, fontstyle="italic")

    plt.tight_layout(h_pad=3.0)
    output_path = os.path.join(fig_dir, "fig2_pareto_decision_frontier.png")
    plt.savefig(output_path, dpi=300)
    print(f"  图表已保存: {output_path}")

    print("\n" + "=" * 90)
    print("[完成] 帕累托多目标优化求解完毕，可接入任务4工艺流程可视化")
    print("=" * 90)
