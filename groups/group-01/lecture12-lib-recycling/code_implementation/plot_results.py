"""仅绘制正式计算CSV，300 DPI；没有数据时不生成示意湖北曲线。"""
from pathlib import Path
from collections import defaultdict
import csv
import json
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import DATA, InputError


def read(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def save(fig, output, name, rect=None):
    fig.tight_layout(rect=rect)
    fig.canvas.draw()
    qa = Path(os.environ["LECTURE12_QA_DIR"]) if os.environ.get("LECTURE12_QA_DIR") else None
    if qa:
        qa.mkdir(parents=True, exist_ok=True)
    helper = Path.home() / ".codex/skills/nature-figure/scripts"
    if (helper / "audit_panel_alignment.py").is_file():
        sys.path.insert(0, str(helper))
        from audit_panel_alignment import require_matplotlib_panel_alignment
        require_matplotlib_panel_alignment(fig, json_out=qa / (name+"_alignment.json") if qa else None, axes=[ax for ax in fig.axes if ax.get_label() != "<colorbar>"], strict=True)
    else:
        boxes = [list(ax.get_position().bounds) for ax in fig.axes]
        # 简单同行双图检查；外部skill不是模型运行的必要依赖。
        if len(boxes) == 2:
            assert abs(boxes[0][1]-boxes[1][1])*fig.get_figheight()*72 <= 1.5
            assert abs(boxes[0][3]-boxes[1][3])*fig.get_figheight()*72 <= 1.5
    fig.savefig(output / (name+".png"), dpi=300)
    if qa:
        fig.savefig(qa / (name+".pdf"))
        fig.savefig(qa / (name+".svg"))
    plt.close(fig)


def render_results(output, figure_output=None):
    output = Path(output)
    figures = Path(figure_output) if figure_output is not None else output
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
                         "font.size": 10, "pdf.fonttype": 42, "svg.fonttype": "none", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.unicode_minus": False})
    mfa = read(output / "dmfa_annual.csv")
    by_year = defaultdict(lambda: np.zeros(2))
    chem = defaultdict(lambda: defaultdict(float))
    for row in mfa:
        y = int(row["year"])
        by_year[y] += np.array([float(row["Li_stock_kg"]), float(row["Li_retired_kg"])])/1000
        chem[row["chemistry"]][y] += float(row["Li_retired_kg"])/1000
    years = sorted(by_year)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].plot(years, [by_year[y][0] for y in years], color="#236f77")
    axes[0].set(xlabel="年份", ylabel="在用锂存量（吨）", title="电池在用锂存量")
    axes[1].stackplot(years, *[[values.get(y, 0) for y in years] for values in chem.values()], labels=list(chem), alpha=0.8)
    axes[1].set(xlabel="年份", ylabel="首次退役锂流量（吨/年）", title="按正极化学体系分解首次退役量")
    axes[1].legend(frameon=False, fontsize=8)
    save(fig, figures, "fig1_stock_and_retirement")
    scenarios = [r for r in read(output / "scenario_results.csv") if r["status"] == "Feasible"]
    anchors = read(output / "anchors.csv")
    for primary in ("brine",):  # 两基准不改变绝对GWP/LCOR；共同图只画一次，差异在表中列示。
        rows = [r for r in scenarios if r["primary_route"] == primary]
        if not rows:
            continue
        chosen = [r for r in anchors if r["primary_route"] == primary]
        b = next(r for r in chosen if r["anchor"] == "B_Utopia_Distance_Min")
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        bases = read(DATA / "primary_lce_baselines.csv")
        for ax, field, title, unit in ((axes[0], "gwp_kg_per_t_lce", "同功能单位碳影响筛查", "kg CO2e/吨LCE"),
                                      (axes[1], "water_l_per_t_lce", "同功能单位水耗筛查", "L/吨LCE")):
            ax.bar(["盐湖基准", "锂辉石基准", "再生B情景"], [float(r[field]) for r in bases]+[float(b[field])], color=["#9ca7ab", "#bdc6c9", "#26747c"])
            ax.set(ylabel=unit, title=title)
        save(fig, figures, f"fig7_primary_comparison_{primary}")
        price_rows = [r for r in rows if r["pathway"] == b["pathway"]
                      and r["green_share"] == b["green_share"] and r["collection_fraction"] == b["collection_fraction"]]
        price_rows.sort(key=lambda r: float(r["lce_price_cny_t"]))
        if len({r["lce_price_cny_t"] for r in price_rows}) >= 2:
            fig, ax = plt.subplots(figsize=(7, 4.5))
            ax.plot([float(r["lce_price_cny_t"]) for r in price_rows], [-float(r["net_cost_cny_per_t_battery"]) for r in price_rows], marker="o", color="#26747c")
            ax.axhline(0, color="#969696", linewidth=0.8)
            ax.set(xlabel="碳酸锂价格（元/吨LCE）", ylabel="净收益（元/吨精炼进料）", title="固定工艺、收集率与绿电份额的价格敏感性")
            save(fig, figures, f"fig8_price_profit_{primary}")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter([float(r["gwp_kg_per_t_lce"]) for r in rows], [float(r["lcor_cny_per_t_lce"]) for r in rows], s=12, alpha=0.35, color="#6e9ba6", label="通过筛选的情景")
        frontier = read(output / f"pareto_{primary}.csv")
        ax.scatter([float(r["gwp_kg_per_t_lce"]) for r in frontier], [float(r["lcor_cny_per_t_lce"]) for r in frontier], s=30, color="#1b6069", label="非支配集合")
        grouped = defaultdict(list)
        for r in chosen:
            grouped[(float(r["gwp_kg_per_t_lce"]), float(r["lcor_cny_per_t_lce"]))].append(r["anchor"][0])
        for point, labels in grouped.items():
            ax.scatter(*point, marker="*", s=110, color="#b17a26", zorder=4)
            ax.annotate("=".join(labels), point, xytext=(5, 8), textcoords="offset points", fontsize=9)
        ax.set(xlabel="碳影响筛查值（kg CO2e/吨LCE）", ylabel="已计费用LCOR（元/吨LCE）", title="条件帕累托前沿：两种原生参考共用")
        ax.legend(frameon=False)
        save(fig, figures, f"fig2_pareto_{primary}")
        fig, ax = plt.subplots(figsize=(7, 5))
        points = ax.scatter([float(r["gwp_kg_per_t_lce"]) for r in rows], [float(r["water_l_per_t_lce"]) for r in rows],
                            c=[float(r["green_share"]) for r in rows], cmap="viridis", s=14)
        fig.colorbar(points, ax=ax, label="绿电份额")
        ax.set(xlabel="碳影响筛查值（kg CO2e/吨LCE）", ylabel="水耗筛查值（L/吨LCE）", title="条件情景：水耗—碳影响关系")
        save(fig, figures, f"fig3_water_carbon_{primary}")
        # 固定推荐工艺与价格，仅比较两个明确的外部情景变量。
        subset = [r for r in rows if r["pathway"] == b["pathway"] and r["lce_price_cny_t"] == b["lce_price_cny_t"]]
        x = sorted({float(r["green_share"]) for r in subset})
        y = sorted({float(r["collection_fraction"]) for r in subset})
        matrix = np.full((len(y), len(x)), np.nan)
        for r in subset:
            matrix[y.index(float(r["collection_fraction"])), x.index(float(r["green_share"]))] = float(r["lcor_cny_per_t_lce"])
        fig, ax = plt.subplots(figsize=(8, 5))
        image = ax.imshow(matrix, origin="lower", aspect="auto", cmap="viridis", interpolation="nearest")
        xt = np.unique(np.linspace(0, len(x)-1, min(5, len(x))).astype(int))
        yt = np.unique(np.linspace(0, len(y)-1, min(5, len(y))).astype(int))
        ax.set_xticks(xt, [f"{x[i]:.0%}" for i in xt]); ax.set_yticks(yt, [f"{y[i]:.0%}" for i in yt])
        ax.set(xlabel="绿电份额", ylabel="规划期正规收集率情景", title="LCOR二维敏感性；空白为不可用工况")
        fig.colorbar(image, ax=ax, label="LCOR（元/吨LCE）")
        save(fig, figures, f"fig4_sensitivity_{primary}")
        contribution = read(output / f"recommended_lci_{primary}.csv")
        sums = defaultdict(lambda: np.zeros(3))
        for r in contribution:
            sums[r["component"]] += float(r["mix_weight"])*np.array([float(r["gwp_kg_per_t_battery"]), float(r["water_l_per_t_battery"]), float(r["cost_cny_per_t_battery"])])
        for dimension, ylabel, label in ((0, "kg CO2e/吨精炼进料", "碳排放"), (1, "L/吨精炼进料", "耗水"), (2, "元/吨精炼进料", "清单与网络费用")):
            fig, ax = plt.subplots(figsize=(9, 5))
            ax.barh(list(sums), [v[dimension] for v in sums.values()], color="#357f86")
            ax.set(xlabel=ylabel, title=f"推荐方案{label}分项；费用图不含采购与销售")
            save(fig, figures, f"fig5_breakdown_{dimension}_{primary}")
        network = json.loads((output / f"recommended_network_{primary}.json").read_text("utf-8"))
        nodes = {r["node_id"]: r for r in read(DATA / "network_nodes.csv")}
        used = {r[k] for r in network["flows"] for k in ("from_node", "to_node")}
        if any(nodes[key][coordinate] == "" for key in used for coordinate in ("longitude", "latitude")):
            raise InputError("网络图需要有出处的经纬度；不生成虚构地理位置")
        fig, ax = plt.subplots(figsize=(9, 6))
        for r in network["flows"]:
            a, z = nodes[r["from_node"]], nodes[r["to_node"]]
            ax.plot([float(a["longitude"]), float(z["longitude"])], [float(a["latitude"]), float(z["latitude"])], color="#7ea8ad", alpha=0.5)
        for i, key in enumerate(sorted(k for k in used if nodes[k]["role"] != "collection")):
            n = nodes[key]
            point = (float(n["longitude"]), float(n["latitude"]))
            ax.scatter(*point, s=35, color="#24636b")
            offset = (-14, -15) if n["role"] == "origin" and n["city"] == "荆门" else (4, 7)
            # 同一版城市驻地的密集路段标签单独避让，不移动真实节点坐标。
            if n["role"] == "origin":
                offset = {2: (8, -12), 3: (8, 12), 11: (0, 25), 17: (-15, -16)}.get(i+1, offset)
            else:
                offset = (-40, -40)
            ax.annotate(str(i+1) if n["role"] == "origin" else "精炼", point, xytext=offset, textcoords="offset points", fontsize=8)
        ax.margins(x=.08, y=.12)
        ax.set(xlabel="经度（度）", ylabel="纬度（度）", title="固定荆门处理点的物流情景；连线为示意，不是全省最优选址")
        save(fig, figures, f"fig6_network_{primary}")
