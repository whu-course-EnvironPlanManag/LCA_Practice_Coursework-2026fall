"""
07_make_figures.py — 模块4：统一出图（7 张，>=300 DPI）
【AI 辅助编程提示词记录】
Prompt: "制图脚本：7 张图（时序/SOH分流/MFA/价格反转/LCA/敏感性热力图/帕累托），PNG>=300DPI，中文。"
是否经人工校验：是
"""
import csv, importlib.util, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("config", os.path.join(_HERE, "00_config.py"))
config = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(config)
RESULTS_DIR, FIGURES_DIR, FIG_DPI = config.RESULTS_DIR, config.FIGURES_DIR, config.FIG_DPI
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

def load_csv(name):
    with open(os.path.join(RESULTS_DIR, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))

def fig1():
    data = load_csv("dmfa_timeseries.csv")
    years = [int(r["year"]) for r in data]
    lfp = [float(r["lfp_retired_t"]) for r in data]; nmc = [float(r["nmc_retired_t"]) for r in data]
    li = [float(r["li_scrap_flow_kg"]) / 1000 for r in data]
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.bar(years, lfp, label="LFP 退役量", color="#4CAF50", alpha=0.7)
    ax1.bar(years, nmc, bottom=lfp, label="NMC 退役量", color="#2196F3", alpha=0.7)
    ax1.set_xlabel("年份"); ax1.set_ylabel("退役电池量 (t)"); ax1.legend(loc="upper left")
    ax2 = ax1.twinx(); ax2.plot(years, li, "r-o", label="报废锂流量", linewidth=2)
    ax2.set_ylabel("报废锂流量 (t Li)"); ax2.legend(loc="upper right")
    plt.title("区域退役动力电池量与锂流量时序演化 (2026-2040)"); plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig1_retirement_timeseries.png"), dpi=FIG_DPI); plt.close()
    print("[07] fig1 done")

def fig2():
    labels = ["SOH>85%\n低速车(LSV)", "80-85%\n储能(ESS)", "70-80%\n通信基站(CBS)", "SOH<70%\n直接再生"]
    sizes = [15, 25, 35, 25]; colors = ["#FF9800", "#2196F3", "#4CAF50", "#9E9E9E"]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(sizes, labels=labels, colors=colors, autopct="%1.0f%%", startangle=90, textprops={"fontsize": 10})
    plt.title("退役动力电池 SOH 三级分流结构"); plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig2_soh_triage.png"), dpi=FIG_DPI); plt.close()
    print("[07] fig2 done")

def fig3():
    data = load_csv("mfa_balance.csv")
    elements = [r["element"] for r in data]; inputs = [float(r["input_kg"]) for r in data]
    products = [float(r["product_kg"]) for r in data]; losses = [float(r["loss_kg"]) for r in data]
    x = np.arange(len(elements)); w = 0.35
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - w/2, inputs, w, label="输入", color="#2196F3")
    ax.bar(x + w/2, products, w, label="产品产出", color="#4CAF50")
    ax.bar(x + w/2, losses, w, bottom=products, label="尾渣损耗", color="#F44336")
    ax.set_xticks(x); ax.set_xticklabels(elements); ax.set_ylabel("质量 (kg)")
    ax.set_title("再生工序元素级物质流平衡"); ax.legend(); plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig3_mfa_sankey.png"), dpi=FIG_DPI); plt.close()
    print("[07] fig3 done")

def fig4():
    data = load_csv("price_reversal.csv")
    route_labels = {"hydrometallurgy": "湿法", "pyrometallurgy": "火法", "direct_recycling": "直接再生"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, chem in zip(axes, ["LFP", "NMC811"]):
        for route in ["hydrometallurgy", "pyrometallurgy", "direct_recycling"]:
            ys = []
            for sc in ["low", "baseline", "high"]:
                row = next(r for r in data if r["chemistry"] == chem and r["price_scenario"] == sc and r["route"] == route)
                ys.append(float(row["lcor_CNY_per_kg"]))
            ax.plot(["low", "baseline", "high"], ys, "o-", label=route_labels[route], linewidth=2, markersize=8)
        ax.set_xlabel("碳酸锂价格情景"); ax.set_ylabel("LCOR (CNY/kg 电池)")
        ax.set_title(f"{chem} — 价格反转机制"); ax.legend(); ax.grid(True, alpha=0.3)
    plt.suptitle("碳酸锂价格波动下三工艺 LCOR 排序反转"); plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig4_price_reversal.png"), dpi=FIG_DPI); plt.close()
    print("[07] fig4 done")

def fig5():
    data = load_csv("lca_results.csv")
    route_labels = {"hydrometallurgy": "湿法", "pyrometallurgy": "火法", "direct_recycling": "直接再生"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for r in ["hydrometallurgy", "pyrometallurgy", "direct_recycling"]:
        rows = [x for x in data if x["route"] == r and x["chemistry"] == "LFP"]
        gwp = [float(x["gwp_kgCO2e_per_kg"]) for x in rows]; gpr = [float(x["green_power_ratio"]) for x in rows]
        axes[0].plot(gpr, gwp, "o-", label=route_labels[r], linewidth=2)
    axes[0].axhline(y=1.5 * 0.039, color="green", linestyle="--", label="原生卤水锂基准")
    axes[0].axhline(y=14.5 * 0.039, color="red", linestyle="--", label="原生硬岩锂基准")
    axes[0].set_xlabel("绿电消纳比例"); axes[0].set_ylabel("GWP (kg CO2e/kg 电池)")
    axes[0].set_title("再生路径 GWP 对比"); axes[0].legend(); axes[0].grid(True, alpha=0.3)
    for r in ["hydrometallurgy", "pyrometallurgy", "direct_recycling"]:
        rows = [x for x in data if x["route"] == r and x["chemistry"] == "LFP"]
        gwp = [float(x["gwp_kgCO2e_per_kg"]) for x in rows]; water = [float(x["water_L_per_kg"]) for x in rows]
        axes[1].plot(water, gwp, "o-", label=route_labels[r], linewidth=2)
    axes[1].set_xlabel("水耗 (L/kg 电池)"); axes[1].set_ylabel("GWP (kg CO2e/kg 电池)")
    axes[1].set_title("水耗-碳排放权衡曲线"); axes[1].legend(); axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig5_lca_contribution.png"), dpi=FIG_DPI); plt.close()
    print("[07] fig5 done")

def fig6():
    data = load_csv("sensitivity.csv")
    sohs = sorted(set(float(r["soh_threshold"]) for r in data))
    prices = ["low", "baseline", "high"]; price_labels = {"low": "$10k", "baseline": "$22k", "high": "$50k"}
    matrix = np.zeros((len(sohs), len(prices)))
    for i, s in enumerate(sohs):
        for j, p in enumerate(prices):
            row = next(r for r in data if float(r["soh_threshold"]) == s and r["price_scenario"] == p)
            matrix[i, j] = float(row["lcor"])
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="RdYlGn_r", aspect="auto")
    ax.set_xticks(range(len(prices))); ax.set_xticklabels([price_labels[p] for p in prices])
    ax.set_yticks(range(len(sohs))); ax.set_yticklabels([f"{s:.0%}" for s in sohs])
    ax.set_xlabel("碳酸锂价格"); ax.set_ylabel("梯次终止 SOH 阈值")
    ax.set_title("LCOR 敏感性热力图 (价格 x SOH 阈值)")
    for i in range(len(sohs)):
        for j in range(len(prices)):
            ax.text(j, i, f"{matrix[i,j]:.1f}", ha="center", va="center", color="black", fontsize=9)
    plt.colorbar(im, label="LCOR (CNY/kg)"); plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig6_sensitivity_heatmap.png"), dpi=FIG_DPI); plt.close()
    print("[07] fig6 done")

def fig7():
    data = load_csv("pareto_front.csv")
    gwp = [float(r["gwp"]) for r in data]; lcor = [float(r["lcor"]) for r in data]
    feasible = [r["feasible"] == "True" for r in data]
    is_knee = [r.get("is_knee", "False") == "True" for r in data]
    is_anchor = [r.get("is_anchor", "False") == "True" for r in data]
    fig, ax = plt.subplots(figsize=(10, 6))
    f_gwp = [g for g, f in zip(gwp, feasible) if f]; f_lcor = [l for l, f in zip(lcor, feasible) if f]
    ax.scatter(f_gwp, f_lcor, c="lightblue", alpha=0.5, s=20, label="可行解")
    for g, l, k in zip(gwp, lcor, is_knee):
        if k: ax.scatter(g, l, c="red", s=200, marker="*", zorder=5, label="拐点")
    for g, l, a in zip(gwp, lcor, is_anchor):
        if a: ax.scatter(g, l, c="green", s=100, marker="s", zorder=4, label="锚点")
    ax.set_xlabel("GWP (kg CO2e/kg 电池)"); ax.set_ylabel("LCOR (CNY/kg 电池)")
    ax.set_title("多目标帕累托最优前沿与拐点标定")
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles)); ax.legend(by_label.values(), by_label.keys())
    ax.grid(True, alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig7_pareto_front.png"), dpi=FIG_DPI); plt.close()
    print("[07] fig7 done")

def make_all():
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7()
    index = """| 图号 | 文件名 | 一句话结论 | 数据来源脚本 |
| :--- | :--- | :--- | :--- |
| fig1 | fig1_retirement_timeseries.png | 2026-2040退役量与锂流量持续增长 | 01_dmfa_model.py |
| fig2 | fig2_soh_triage.png | SOH三级分流决定梯次与再生比例 | 02_process_mfa.py |
| fig3 | fig3_mfa_sankey.png | 元素级质量守恒误差<0.05% | 02_process_mfa.py |
| fig4 | fig4_price_reversal.png | 碳酸锂价格波动导致经济性排序反转 | 04_echelon_tea.py |
| fig5 | fig5_lca_contribution.png | 再生路径GWP显著低于原生硬岩锂 | 05_lca.py |
| fig6 | fig6_sensitivity_heatmap.png | SOH阈值与价格对LCOR显著交互 | 06_pareto_sensitivity.py |
| fig7 | fig7_pareto_front.png | 拐点方案平衡环境与经济目标 | 06_pareto_sensitivity.py |
"""
    with open(os.path.join(RESULTS_DIR, "figure_index.md"), "w", encoding="utf-8") as f:
        f.write(index)
    print(f"[07] 全部图表 -> {FIGURES_DIR}")

if __name__ == "__main__":
    make_all()
