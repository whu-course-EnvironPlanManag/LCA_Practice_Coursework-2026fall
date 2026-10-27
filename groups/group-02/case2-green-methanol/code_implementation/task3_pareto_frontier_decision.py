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
import matplotlib

matplotlib.use("Agg")

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

    # 专业配色方案
    CLR_BG = "#FAFBFC"
    CLR_VETO = "#E57373"
    CLR_DOMESTIC = "#64B5F6"
    CLR_REDIII = "#81C784"
    CLR_FRONTIER = "#5C6BC0"
    CLR_FRONTIER_FILL = "#C5CAE9"
    CLR_ANCHOR_A = "#00897B"
    CLR_ANCHOR_B = "#FF8F00"
    CLR_ANCHOR_C = "#1565C0"
    CLR_LINE_RED = "#C62828"
    CLR_LINE_GREEN = "#2E7D32"
    CLR_LINE_GRAY = "#78909C"
    CLR_TEXT = "#263238"
    CLR_GRID = "#ECEFF1"

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(15, 13), dpi=300, gridspec_kw={"height_ratios": [1.1, 0.9]}
    )
    fig.patch.set_facecolor(CLR_BG)

    df_vetoed = df_all[df_all["compliance"] == "Redline_Vetoed"]
    df_domestic = df_all[df_all["compliance"] == "Domestic_Compliant"]
    df_rediii = df_all[df_all["compliance"] == "RED_III_RFNBO_Certified"]

    # ---- 子图 (a): 目标空间帕累托前沿 ----
    ax_top.set_facecolor("white")

    # 散点: 一票否决
    ax_top.scatter(df_vetoed["gwp_net"], df_vetoed["lcom_adjusted"],
                   c=CLR_VETO, marker="x", s=18, alpha=0.30,
                   label=f"一票否决方案 (n={len(df_vetoed)})",
                   linewidths=0.8, zorder=3)

    # 散点: 国内合规
    ax_top.scatter(df_domestic["gwp_net"], df_domestic["lcom_adjusted"],
                   c=CLR_DOMESTIC, marker="^", s=20, alpha=0.35,
                   label=f"国内合规方案 (n={len(df_domestic)})",
                   edgecolors="white", linewidths=0.3, zorder=3)

    # 散点: RED III 认证
    ax_top.scatter(df_rediii["gwp_net"], df_rediii["lcom_adjusted"],
                   c=CLR_REDIII, marker="o", s=22, alpha=0.45,
                   label=f"欧盟 RED III 认证 (n={len(df_rediii)})",
                   edgecolors="white", linewidths=0.3, zorder=3)

    # 帕累托前沿线 (加粗 + 发光效果)
    ax_top.fill_between(df_pareto["gwp_net"], df_pareto["lcom_adjusted"],
                        df_pareto["lcom_adjusted"].max() * 1.08,
                        alpha=0.08, color=CLR_FRONTIER, zorder=5)
    ax_top.fill_between(df_pareto["gwp_net"], df_pareto["lcom_adjusted"],
                        df_pareto["lcom_adjusted"].min() * 0.95,
                        alpha=0.05, color=CLR_FRONTIER, zorder=5)
    ax_top.plot(df_pareto["gwp_net"], df_pareto["lcom_adjusted"],
                color=CLR_FRONTIER, linewidth=3.5, linestyle="-",
                label=f"帕累托前沿 ({len(df_pareto)} 个非支配解)",
                zorder=8, solid_capstyle="round")

    # 前沿线发光效果
    ax_top.plot(df_pareto["gwp_net"], df_pareto["lcom_adjusted"],
                color=CLR_FRONTIER, linewidth=8.0, alpha=0.12,
                linestyle="-", zorder=7, solid_capstyle="round")

    # 分区背景色带 (在数据绘制后设置ylim)
    y_lo, y_hi = ax_top.get_ylim()
    ax_top.axvspan(-1500, 0, alpha=0.04, color="#4CAF50", zorder=0)
    ax_top.axvspan(0, 561.2, alpha=0.03, color="#2196F3", zorder=0)
    ax_top.axvspan(561.2, 2600, alpha=0.03, color="#FF9800", zorder=0)
    ax_top.axvspan(2600, 6000, alpha=0.04, color="#F44336", zorder=0)

    # 分区标签
    ax_top.text(-750, y_hi * 0.97, "深度负碳区",
                fontsize=7.5, ha="center", va="top", color="#2E7D32",
                fontstyle="italic", alpha=0.7, zorder=1)
    ax_top.text(280, y_hi * 0.97, "RED III\n达标区",
                fontsize=7.0, ha="center", va="top", color="#1565C0",
                fontstyle="italic", alpha=0.7, zorder=1)

    # 政策阈值线 (带标注)
    ax_top.axvline(2600.0, color=CLR_LINE_RED, linestyle="--", linewidth=1.5,
                   alpha=0.8, zorder=6)
    ax_top.text(2620, ax_top.get_ylim()[0] + 50,
                "煤制甲醇基准\n2600 kgCO2e/t",
                fontsize=7.0, color=CLR_LINE_RED, fontweight="bold",
                va="bottom", ha="left", alpha=0.8)

    ax_top.axvline(561.2, color=CLR_LINE_GREEN, linestyle="-.", linewidth=1.5,
                   alpha=0.8, zorder=6)
    ax_top.text(580, ax_top.get_ylim()[0] + 50,
                "RED III 准入限值\n561.2 kgCO2e/t",
                fontsize=7.0, color=CLR_LINE_GREEN, fontweight="bold",
                va="bottom", ha="left", alpha=0.8)

    ax_top.axvline(0.0, color=CLR_LINE_GRAY, linestyle=":", linewidth=1.2,
                   alpha=0.6, zorder=6)
    ax_top.text(15, ax_top.get_ylim()[0] + 50,
                "净零碳线",
                fontsize=7.0, color=CLR_LINE_GRAY, fontweight="bold",
                va="bottom", ha="left", alpha=0.7)

    # 锚点标记 (不同形状 + 光晕)
    anchor_styles = {
        "A_Cost_Min": ("P", CLR_ANCHOR_A, 240, "锚点 A: 成本极小化 (保守型)"),
        "B_Knee_Point": ("D", CLR_ANCHOR_B, 220, "锚点 B: 帕累托拐点 (推荐方案)"),
        "C_Deep_Negative": ("X", CLR_ANCHOR_C, 200, "锚点 C: 深度负碳极限 (国际航运)")
    }

    for key, (marker, color, size, label) in anchor_styles.items():
        pt = dict_anchors[key]
        # 光晕
        ax_top.scatter(pt["gwp_net"], pt["lcom_adjusted"],
                       marker=marker, c=color, s=size * 2.5,
                       alpha=0.20, edgecolors="none", zorder=9)
        # 主标记
        ax_top.scatter(pt["gwp_net"], pt["lcom_adjusted"],
                       marker=marker, c=color, s=size,
                       edgecolors="white", linewidth=2.0, zorder=10, label=label)

    ax_top.set_title("(a) 政策规制约束下的帕累托前沿: 碳足迹-成本权衡分析",
                     fontsize=13, fontweight="bold", pad=16, color=CLR_TEXT)
    ax_top.set_xlabel("全生命周期净碳足迹 GWP_net (kg CO2e/t 甲醇)",
                      fontsize=11, color=CLR_TEXT)
    ax_top.set_ylabel("政策调整后平准化成本 LCOM_adj (元/t 甲醇)",
                      fontsize=11, color=CLR_TEXT)
    ax_top.grid(True, linestyle="--", alpha=0.4, color=CLR_GRID, zorder=1)
    ax_top.tick_params(labelsize=9, colors=CLR_TEXT)
    ax_top.legend(loc="upper left", fontsize=8.0, framealpha=0.96,
                  edgecolor="#CFD8DC", fancybox=True, shadow=True)

    # 推荐方案注释框 (锚点B)
    b_pt = dict_anchors["B_Knee_Point"]
    ax_top.text(
        0.47,
        0.95,
        f"★ 推荐方案 B (帕累托拐点)\n"
        f"GWP = {b_pt['gwp_net']:.1f} kg CO2e/t\n"
        f"LCOM = {b_pt['lcom_adjusted']:.1f} 元/t\n"
        f"MAC = {b_pt['mac_adjusted']:.1f} 元/t CO2e\n"
        f"f_green = {b_pt['f_green']*100:.1f}%, r_purge = {b_pt['r_purge']*100:.2f}%",
        transform=ax_top.transAxes,
        ha="center",
        va="top",
        fontsize=8.8, fontweight="bold", linespacing=1.5,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF8E1",
                  edgecolor=CLR_ANCHOR_B, linewidth=2.0, alpha=0.95),
        color=CLR_TEXT, zorder=11
    )

    # 锚点A注释
    a_pt = dict_anchors["A_Cost_Min"]
    ax_top.annotate(
        f"A: GWP {a_pt['gwp_net']:.1f}, LCOM {a_pt['lcom_adjusted']:.1f}",
        xy=(a_pt["gwp_net"], a_pt["lcom_adjusted"]),
        xytext=(8, -18),
        textcoords="offset points",
        fontsize=7.2, fontweight="bold",
        ha="left",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#E0F2F1",
                  edgecolor=CLR_ANCHOR_A, linewidth=1.2, alpha=0.9),
        arrowprops=dict(arrowstyle="->", color=CLR_ANCHOR_A, lw=1.2),
        color=CLR_TEXT, zorder=11
    )

    # 锚点C注释
    c_pt = dict_anchors["C_Deep_Negative"]
    ax_top.annotate(
        f"C: GWP {c_pt['gwp_net']:.1f}, LCOM {c_pt['lcom_adjusted']:.1f}",
        xy=(c_pt["gwp_net"], c_pt["lcom_adjusted"]),
        xytext=(8, 12),
        textcoords="offset points",
        fontsize=7.2, fontweight="bold",
        ha="left",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#E3F2FD",
                  edgecolor=CLR_ANCHOR_C, linewidth=1.2, alpha=0.9),
        arrowprops=dict(arrowstyle="->", color=CLR_ANCHOR_C, lw=1.2),
        color=CLR_TEXT, zorder=11
    )

    # ---- 子图 (b): 决策变量空间 ----
    ax_bot.set_facecolor("white")

    # 帕累托前沿散点 (碳利用率色标)
    scatter_b = ax_bot.scatter(
        df_pareto["f_green"] * 100.0, df_pareto["r_purge"] * 100.0,
        c=df_pareto["eta_carbon_pct"], cmap="RdYlBu", s=70,
        edgecolors="#455A64", linewidth=0.6, zorder=5,
        vmin=df_pareto["eta_carbon_pct"].min(), vmax=df_pareto["eta_carbon_pct"].max()
    )
    cbar = plt.colorbar(scatter_b, ax=ax_bot, pad=0.03, shrink=0.85)
    cbar.set_label("系统总碳利用率 η_carbon (%)", fontsize=10,
                   color=CLR_TEXT, fontweight="bold")
    cbar.ax.tick_params(labelsize=9)

    # 可行域背景 (数据绘制后设置)
    ax_bot.axhspan(0.004 * 100, 0.035 * 100, alpha=0.06, color="#4CAF50", zorder=0)
    ax_bot.axhspan(0.035 * 100, 0.045 * 100, alpha=0.06, color="#F44336", zorder=0)

    # 锚点标记
    for key, (marker, color, size, label) in anchor_styles.items():
        pt = dict_anchors[key]
        # 光晕
        ax_bot.scatter(pt["f_green"] * 100.0, pt["r_purge"] * 100.0,
                       marker=marker, c=color, s=size * 2.5,
                       alpha=0.20, edgecolors="none", zorder=9)
        # 主标记
        ax_bot.scatter(pt["f_green"] * 100.0, pt["r_purge"] * 100.0,
                       marker=marker, c=color, s=size,
                       edgecolors="white", linewidth=2.0, zorder=10, label=label)

    # 锚点标注 (子图b)
    for key, (color, label_x) in {
        "A_Cost_Min": (CLR_ANCHOR_A, 76),
        "B_Knee_Point": (CLR_ANCHOR_B, 76),
        "C_Deep_Negative": (CLR_ANCHOR_C, 76)
    }.items():
        pt = dict_anchors[key]
        short_label = key.split("_")[0]
        ax_bot.annotate(
            f"{short_label}: f={pt['f_green']*100:.0f}%, r={pt['r_purge']*100:.2f}%",
            xy=(pt["f_green"] * 100.0, pt["r_purge"] * 100.0),
            xytext=(label_x, pt["r_purge"] * 100.0),
            fontsize=7.4, fontweight="bold",
            ha="right",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor=color, linewidth=1.0, alpha=0.9),
            arrowprops=dict(arrowstyle="->", color=color, lw=1.0),
            color=CLR_TEXT, zorder=11
        )

    ax_bot.set_title("(b) 帕累托最优解的工程调控参数分布",
                     fontsize=13, fontweight="bold", pad=16, color=CLR_TEXT)
    ax_bot.set_xlabel("绿电消纳比例 f_green (%)", fontsize=11, color=CLR_TEXT)
    ax_bot.set_ylabel("驰放分流比 r_purge (%)", fontsize=11, color=CLR_TEXT)
    ax_bot.set_xlim(0, 100)
    ax_bot.set_ylim(0.35, 4.65)
    ax_bot.grid(True, linestyle="--", alpha=0.4, color=CLR_GRID, zorder=1)
    ax_bot.tick_params(labelsize=9, colors=CLR_TEXT)
    ax_bot.legend(loc="upper right", fontsize=8.5, framealpha=0.96,
                  edgecolor="#CFD8DC", fancybox=True, shadow=True)

    # 可行域标注
    ax_bot.text(36, 1.75, "清洁生产可行域 (r < 3.5%)",
                fontsize=9.0, ha="center", va="center",
                color="#2E7D32", fontweight="bold", fontstyle="italic",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F5E9",
                          edgecolor="#4CAF50", linewidth=0.8, alpha=0.8))
    ax_bot.text(36, 4.0, "碳利用率 < 88% 一票否决区",
                fontsize=8.0, ha="center", va="center",
                color="#C62828", fontweight="bold", fontstyle="italic",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFEBEE",
                          edgecolor="#EF5350", linewidth=0.8, alpha=0.8))

    # 底部说明文字
    fig.text(0.5, 0.01,
             f"数据来源: MFA-LCA-TEA-Policy 耦合仿真  |  网格采样: 60×50={len(df_all)} 工况  |  "
             f"帕累托最优解: {len(df_pareto)} 个  |  "
             f"推荐方案: 锚点B (f_green={dict_anchors['B_Knee_Point']['f_green']*100:.0f}%, "
             f"r_purge={dict_anchors['B_Knee_Point']['r_purge']*100:.2f}%)",
             ha="center", fontsize=8.5, color="#546E7A", fontstyle="italic")

    ax_bot.text(
        48,
        2.05,
        f"全部 {len(df_pareto)} 个非支配解均选择 100% 绿电",
        fontsize=8.0,
        color=CLR_TEXT,
        ha="center",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#CFD8DC"),
        zorder=6,
    )

    fig.subplots_adjust(left=0.10, right=0.91, top=0.96, bottom=0.07, hspace=0.32)
    output_path = os.path.join(fig_dir, "fig2_pareto_decision_frontier.png")
    plt.savefig(output_path, dpi=300,
                facecolor=CLR_BG, edgecolor="none")
    plt.close(fig)
    print(f"  图表已保存: {output_path}")

    print("\n" + "=" * 90)
    print("[完成] 帕累托多目标优化求解完毕，可接入任务4工艺流程可视化")
    print("=" * 90)
