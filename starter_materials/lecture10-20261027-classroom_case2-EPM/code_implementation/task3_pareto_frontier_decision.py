# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 3（学生实训脚本框架）
脚本名称：task3_pareto_frontier_decision.py
实训目标：
  1. 耦合 MFA、LCA、TEA 与任务 2 政策规制引擎；
  2. 建立绿电比例 f_green 与驰放比 r_purge 二维调控下的双目标优化模型；
  3. 编写非支配排序算法剔除劣解与法规一票否决解，提取有效帕累托前沿（Pareto Frontier）；
  4. 运用乌托邦理想点欧氏距离最小化准则，自动定位帕累托拐点（Knee Point）；
  5. 输出三大决策锚点比选数据，并绘制 300 DPI 决策双子图保存至 figures_output/。
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

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 导入任务 2 政策规制引擎
try:
    from task2_policy_vibe_engine import evaluate_policy_compliance
except ImportError:
    from code_implementation.task2_policy_vibe_engine import evaluate_policy_compliance

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False


def get_figures_output_dir():
    """跨层级定位 figures_output 目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(os.path.join(current_dir, "..", "figures_output"))
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


# ==============================================================================
# 模块一：耦合工程调控变量的物理与经济仿真模型
# ==============================================================================
def simulate_park_methanol_system(f_green: float, r_purge: float) -> dict:
    """
    输入决策调控参数：
      f_green : 园区风光绿电直供混供消纳比例 [0.0, 1.0]
      r_purge : 循环回路未反应气驰放分流比 [0.004, 0.045]
    输出全套 MFA 物料、LCA 碳足迹、TEA 成本及政策评价指标。
    """
    if not np.isfinite(f_green) or not np.isfinite(r_purge):
        raise ValueError("Decision variables must be finite.")
    if not 0.0 <= f_green <= 1.0 or not 0.004 <= r_purge <= 0.045:
        raise ValueError("f_green must be in [0, 1] and r_purge in [0.004, 0.045].")

    # 1. MFA 物料与能量
    carbon_loss_frac = 1.0 - 0.960 * (1.0 - (r_purge - 0.010) * 3.80)
    carbon_loss_frac = np.clip(carbon_loss_frac, 0.015, 0.250)
    eta_carbon = 1.0 - carbon_loss_frac

    fresh_co2_kg = 1423.0 * (0.960 / eta_carbon)
    fresh_h2_kg  = 198.0 * (0.960 / eta_carbon)

    e_h2_kwh      = fresh_h2_kg * 52.0
    e_co2_kwh     = 255.0 * (fresh_co2_kg / 1423.0)
    e_recycle_kwh = 155.0 * ((0.010 / r_purge) ** 0.65)
    e_distill_kwh = 120.0
    e_total_kwh   = e_h2_kwh + e_co2_kwh + e_recycle_kwh + e_distill_kwh

    # 2. LCA 净碳足迹
    ef_grid_blended = f_green * 0.035 + (1.0 - f_green) * 0.550
    ghg_power = e_total_kwh * ef_grid_blended
    ghg_infra_purge = 95.0 + (r_purge - 0.010) * 1200.0
    credit_co2 = fresh_co2_kg * 1.000
    credit_o2 = 95.0 * (fresh_h2_kg / 198.0)
    gwp_net = ghg_power + ghg_infra_purge - credit_co2 - credit_o2

    # 3. TEA 基础平准化成本
    p_elec_blended = f_green * 0.18 + (1.0 - f_green) * 0.42
    cost_elec = e_total_kwh * p_elec_blended

    # 绿电波动储能缓冲年金摊销增量与循环压缩机尺寸增量
    storage_capex_amort = 680.0 * (f_green ** 2.80)
    recycle_capex_amort = 45.0 * np.maximum(0.0, ((0.010 / r_purge) ** 0.80 - 1.0))
    cost_capex_amortized = 835.2 + storage_capex_amort + recycle_capex_amort

    cost_co2 = (fresh_co2_kg / 1000.0) * 260.0
    cost_water_om = 65.0 + 285.0
    credit_o2_sale = -316.8 * (fresh_h2_kg / 198.0)

    base_lcom = cost_elec + cost_capex_amortized + cost_co2 + cost_water_om + credit_o2_sale

    # 4. 政策规制引擎调用
    policy_res = evaluate_policy_compliance(
        gwp_net=gwp_net,
        base_lcom=base_lcom,
        e_total_kwh=e_total_kwh,
        f_green=f_green,
        r_purge=r_purge
    )

    return {
        "f_green": f_green,
        "r_purge": r_purge,
        "eta_carbon": eta_carbon * 100.0,
        "fresh_co2_kg": fresh_co2_kg,
        "fresh_h2_kg": fresh_h2_kg,
        "fresh_water_t": 1.385 + 0.008 * (0.010 / r_purge),
        "oxygen_kg": 1584.0 * (fresh_h2_kg / 198.0),
        "e_total_kwh": e_total_kwh,
        "ghg_power": ghg_power,
        "gwp_net": gwp_net,
        "base_lcom": base_lcom,
        "lcom_policy_adjusted": policy_res["lcom_policy_adjusted"],
        "mac_policy_adjusted": policy_res["mac_policy_adjusted"],
        "compliance_status": policy_res["compliance_status"]
    }


# ==============================================================================
# 模块二：非支配排序与三大规划决策锚点提取算法
# ==============================================================================
def extract_pareto_frontier_and_anchors(df: pd.DataFrame):
    """
    在合规方案中提取帕累托前沿，并标定锚点 A、锚点 B 与锚点 C。
    """
    valid_df = df[df["compliance_status"] != "Redline_Vetoed"].copy().reset_index(drop=True)
    if valid_df.empty:
        raise ValueError("No policy-compliant scenarios remain for Pareto analysis.")
    points = valid_df[["gwp_net", "lcom_policy_adjusted"]].values
    if not np.isfinite(points).all():
        raise ValueError("Pareto objectives contain non-finite values.")
    n_pts = points.shape[0]
    is_pareto = np.ones(n_pts, dtype=bool)

    for i in range(n_pts):
        if is_pareto[i]:
            dominated = np.all(points <= points[i], axis=1) & np.any(points < points[i], axis=1)
            if np.any(dominated):
                is_pareto[i] = False

    pareto_df = valid_df[is_pareto].copy().sort_values(by="gwp_net").reset_index(drop=True)

    gwp_min, gwp_max = pareto_df["gwp_net"].min(), pareto_df["gwp_net"].max()
    lcom_min, lcom_max = pareto_df["lcom_policy_adjusted"].min(), pareto_df["lcom_policy_adjusted"].max()

    norm_gwp = (pareto_df["gwp_net"] - gwp_min) / max(gwp_max - gwp_min, 1e-6)
    norm_lcom = (pareto_df["lcom_policy_adjusted"] - lcom_min) / max(lcom_max - lcom_min, 1e-6)
    pareto_df["utopia_distance"] = np.sqrt(norm_gwp ** 2 + norm_lcom ** 2)

    anchor_a = pareto_df.loc[pareto_df["lcom_policy_adjusted"].idxmin()] # 成本极小锚点
    anchor_b = pareto_df.loc[pareto_df["utopia_distance"].idxmin()]      # 帕累托拐点 (规划主推基准)
    anchor_c = pareto_df.loc[pareto_df["gwp_net"].idxmin()]              # 深度负碳极限锚点

    anchors = {
        "Anchor_A_Cost_Min": anchor_a,
        "Anchor_B_Knee_Point": anchor_b,
        "Anchor_C_Deep_Decarb": anchor_c
    }
    return pareto_df, anchors


# ==============================================================================
# 模块三：主程序求解与可视化
# ==============================================================================
if __name__ == "__main__":
    print("=" * 95)
    print("《环境规划与管理》任务 3：MFA-LCA-TEA-Policy 多目标寻优与帕累托前沿求解")
    print("=" * 95)

    # 1. 网格采样遍历 (绿电比例 60 档 x 驰放分流比 50 档 = 3,000 组工况)
    f_green_grid = np.linspace(0.0, 1.0, 60)
    r_purge_grid = np.linspace(0.004, 0.045, 50)

    records = []
    for fg in f_green_grid:
        for rp in r_purge_grid:
            records.append(simulate_park_methanol_system(fg, rp))

    df_all = pd.DataFrame(records)
    print(f"[网格模拟] 共完成 {len(df_all)} 组规划候选工况模拟计算。")

    # 2. 提取帕累托前沿与三大锚点
    pareto_df, anchors = extract_pareto_frontier_and_anchors(df_all)
    print(f"[前沿筛选] 提取出 {len(pareto_df)} 个严格非支配帕累托最优解。")

    # 3. 打印比选结果表
    print("\n" + "=" * 95)
    print("【三大规划决策锚点比选数据表（请填入报告第 5.3 节）】")
    print("=" * 95)
    anchor_names = {
        "Anchor_A_Cost_Min": "锚点 A (成本极小化方案 - 财务保守型)",
        "Anchor_B_Knee_Point": "锚点 B (帕累托拐点 Knee Point - 规划主推基准)",
        "Anchor_C_Deep_Decarb": "锚点 C (深度负碳极限方案 - 国际航运绿色外销)"
    }
    rows = []
    for k, row in anchors.items():
        rows.append({
            "方案名称": anchor_names[k],
            "绿电比例": f"{row['f_green']*100:.1f}%",
            "驰放比": f"{row['r_purge']*100:.2f}%",
            "总碳利用率": f"{row['eta_carbon']:.2f}%",
            "GWP 净碳足迹 (kg/t)": f"{row['gwp_net']:.1f}",
            "基础 LCOM (元/t)": f"{row['base_lcom']:.1f}",
            "净 LCOM (元/t)": f"{row['lcom_policy_adjusted']:.1f}",
            "边际减排成本 MAC (元/t)": f"{row['mac_policy_adjusted']:.1f}",
            "合规标签": row["compliance_status"]
        })
    print(pd.DataFrame(rows).to_string(index=False))
    print("=" * 95)

    # 4. 出版级帕累托双子图绘制
    fig_dir = get_figures_output_dir()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.2), dpi=300)

    df_veto = df_all[df_all["compliance_status"] == "Redline_Vetoed"]
    df_dom  = df_all[df_all["compliance_status"] == "Domestic_Compliant"]
    df_red3 = df_all[df_all["compliance_status"] == "RED_III_RFNBO_Certified"]

    # 子图 (a)：目标空间
    ax1.scatter(df_veto["gwp_net"], df_veto["lcom_policy_adjusted"],
                c="#d95f02", marker="x", s=14, alpha=0.30, label="法规一票否决方案区 (Redline Vetoed)")
    ax1.scatter(df_dom["gwp_net"], df_dom["lcom_policy_adjusted"],
                c="#7570b3", marker="o", s=14, alpha=0.35, label="国内合规被支配方案集 (Domestic Compliant)")
    ax1.scatter(df_red3["gwp_net"], df_red3["lcom_policy_adjusted"],
                c="#66a61e", marker="o", s=16, alpha=0.45, label="欧盟 RED III 认证方案集 (RFNBO Certified)")

    ax1.plot(pareto_df["gwp_net"], pareto_df["lcom_policy_adjusted"],
             color="#e7298a", linewidth=2.8, linestyle="-", label="有效帕累托前沿 (Pareto Frontier)")

    ax1.axvline(2600.0, color="#b2182b", linestyle="--", linewidth=1.2, label="煤制甲醇基准红线 (+2600 kg CO2e/t)")
    ax1.axvline(561.2, color="#1b7837", linestyle="-.", linewidth=1.2, label="欧盟 RED III 准入限值 (+561.2 kg CO2e/t)")
    ax1.axvline(0.0, color="#525252", linestyle=":", linewidth=1.0, label="零碳平衡分界线 (0 kg CO2e/t)")

    styles = {
        "Anchor_A_Cost_Min": ("*", "#1b9e77", 180, "锚点 A: 成本极小化方案 (近期过渡)"),
        "Anchor_B_Knee_Point": ("D", "#000000", 140, "锚点 B: 帕累托拐点 (规划主推基准)"),
        "Anchor_C_Deep_Decarb": ("^", "#08519c", 150, "锚点 C: 深度负碳极限方案 (远期升级)")
    }
    for k, (marker, color, size, lbl) in styles.items():
        pt = anchors[k]
        ax1.scatter(pt["gwp_net"], pt["lcom_policy_adjusted"],
                    marker=marker, c=color, s=size, edgecolors="white", linewidth=1.5, zorder=10, label=lbl)

    ax1.set_title("(a) 工业园区绿色甲醇规划：政策规制约束下的帕累托前沿", fontsize=11.5, fontweight="bold", pad=12)
    ax1.set_xlabel("全生命周期净碳足迹 GWP_net (kg CO2e / t 甲醇)", fontsize=10.5)
    ax1.set_ylabel("政策调整后净平准化成本 LCOM_adjusted (元 / t 甲醇)", fontsize=10.5)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper left", fontsize=8.0, framealpha=0.92)

    # 子图 (b)：决策变量空间
    sc = ax2.scatter(pareto_df["f_green"] * 100.0, pareto_df["r_purge"] * 100.0,
                     c=pareto_df["lcom_policy_adjusted"], cmap="viridis_r", s=50, edgecolors="black", linewidth=0.5)
    cbar = plt.colorbar(sc, ax=ax2, pad=0.02)
    cbar.set_label("调整后净平准化成本 LCOM (元/t)", fontsize=9.5)

    for k, (marker, color, size, lbl) in styles.items():
        pt = anchors[k]
        ax2.scatter(pt["f_green"] * 100.0, pt["r_purge"] * 100.0,
                    marker=marker, c=color, s=size, edgecolors="white", linewidth=1.5, zorder=10, label=lbl)

    ax2.set_title("(b) 帕累托最优解对应的工程调控变量参数组合轨迹", fontsize=11.5, fontweight="bold", pad=12)
    ax2.set_xlabel("园区风光绿电直供混供消纳比例 f_green (%)", fontsize=10.5)
    ax2.set_ylabel("未反应气循环回路驰放分流比 r_purge (%)", fontsize=10.5)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    plt.tight_layout()
    output_png = os.path.join(fig_dir, "fig2_pareto_decision_frontier.png")
    plt.savefig(output_png, dpi=300)
    plt.close(fig)
    print(f"\n[图表输出] 帕累托决策图已成功生成至: {output_png}")
    print("=" * 95)
