"""汇总报告所需数值和显式资本成本敏感性；不更改基础物质流或推荐方案。

AI提示词：从可复算CSV汇总报告数据，资本/固定费用与运输费用各计一次；
项目代理投资和OPEX率必须标明情景，不冒充荆门工程批复。已自动核查，待成员复核。
"""
from collections import Counter, defaultdict
import json
from common import DATA, RESULTS, OUTPUT, write_csv, write_json, number, read_csv
from lca_tea import capital_recovery_factor
from plot_results import save
import matplotlib.pyplot as plt


def rows(name):
    return read_csv(name, directory=RESULTS)


def build_summary():
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
                         "font.size": 10, "pdf.fonttype": 42, "svg.fonttype": "none",
                         "axes.spines.top": False, "axes.spines.right": False, "axes.unicode_minus": False})
    scenarios = rows("scenario_results.csv")
    anchors = rows("anchors.csv")
    b = next(r for r in anchors if r["primary_route"] == "brine" and r["anchor"] == "B_Utopia_Distance_Min")
    b = {k: float(v) if v and k not in {"anchor", "status", "pathway", "primary_route", "environment_allocation_method", "result_scope"} else v for k, v in b.items()}
    baseline = rows("dmfa_annual.csv")
    rec = rows("recommended_dmfa_brine.csv")
    annual = []
    for year in sorted({int(r["year"]) for r in baseline}):
        base = [r for r in baseline if int(r["year"]) == year]
        chosen = [r for r in rec if int(r["year"]) == year]
        annual.append({"year": year,
            "installed_gwh": sum(float(r["installed_kwh"]) for r in base)/1e6,
            "li_stock_t": sum(float(r["Li_stock_kg"]) for r in base)/1000,
            "retired_battery_t": sum(float(r["retired_battery_t"]) for r in base),
            "retired_li_t": sum(float(r["Li_retired_kg"]) for r in base)/1000,
            "baseline_collected_battery_t": sum(float(r["collected_battery_t"]) for r in base),
            "baseline_secondary_li_t": sum(float(r["Li_secondary_kg"]) for r in base)/1000,
            "b_collected_battery_t": sum(float(r["collected_battery_t"]) for r in chosen),
            "b_secondary_li_t": sum(float(r["Li_secondary_kg"]) for r in chosen)/1000})
    write_csv(RESULTS/"annual_summary.csv", annual)
    balance = rows("element_balance.csv")
    errors = {e: max(float(r["relative_error"]) for r in balance if r["element"] == e) for e in ("Li", "Ni", "Co", "Mn")}
    assert all(v < .0005 for v in errors.values())
    network = json.loads((RESULTS/"recommended_network_brine.json").read_text("utf-8"))
    nodes = {r["node_id"]: r for r in read_csv("network_nodes.csv")}
    distances = {(r["from_node"], r["to_node"]): float(r["road_distance_km"]) for r in read_csv("road_distances.csv")}
    routes = []
    origins = sorted(k for k, n in nodes.items() if n["role"] == "origin")
    for index, origin in enumerate(origins, 1):
        city = nodes[origin]["city"]
        flows = [f for f in network["flows"] if nodes[f["from_node"]]["city"] == city and nodes[f["from_node"]]["role"] == "collection"]
        q = sum(float(f["flow_t"]) for f in flows)
        routes.append({"index": index, "city": city, "flow_t": q,
            "road_distance_km": sum(float(f["flow_t"])*distances[(f["from_node"],f["to_node"])] for f in flows)/q if q else 0})
    write_csv(RESULTS/"network_routes.csv", routes)
    tonnes = b["refining_input_t"]
    lce = b["annual_lce_t"]
    sensitivity = []
    for bench in read_csv("tea_cost_benchmarks.csv"):
        if bench["item"] != "capex_unit":
            continue
        unit = number(bench["value"], "单位投资", 0)
        for capacity in (tonnes, 50000, 100000):
            if capacity < tonnes:
                continue
            for fixed_rate in (.03, .06):
                for collection_cost in (0, 250):
                    capex = unit*capacity
                    capital = capex*capital_recovery_factor(.08, 15)/lce
                    fixed = capex*fixed_rate/lce
                    collection = collection_cost*b["collected_t"]/lce
                    sensitivity.append({"benchmark_id": bench["benchmark_id"], "capacity_t_y": capacity,
                        "capex_cny": capex, "wacc": .08, "life_years": 15, "fixed_opex_rate": fixed_rate,
                        "collection_storage_cny_t": collection_cost, "lcor_cny_per_t_lce": b["lcor_cny_per_t_lce"]+capital+fixed+collection,
                        "capital_component_cny_per_t_lce": capital, "fixed_component_cny_per_t_lce": fixed,
                        "collection_component_cny_per_t_lce": collection,
                        "scope": "异地项目投资代理；与B同一工况叠加敏感性，不是工程概算"})
    write_csv(RESULTS/"tea_sensitivity.csv", sensitivity)
    cost = {"电池采购": b["purchase_cny_per_t_battery"], "过程变动费用": b["process_cost_cny_per_t_battery"],
            "运输与节点已计费用": b["network_cost_cny"]/tonnes,
            "已计政策修正": b["policy_adjustment_cny_per_t_battery"],
            "产品销售收入抵扣": -b["revenue_cny_per_t_battery"]}
    assert abs(sum(cost.values())-b["net_cost_cny_per_t_battery"]) < 1e-6
    fig, ax = plt.subplots(figsize=(10,5))
    ax.barh(list(cost), list(cost.values()), color=["#357f86"]*4+["#ad7b28"])
    ax.axvline(0, color="#777777", linewidth=.7)
    ax.set(xlabel="元/吨精炼进料", title="B方案已计成本与收入；未计固定成本、未知税费及副产品收入")
    save(fig, OUTPUT, "fig9_cost_revenue")
    fig, ax = plt.subplots(figsize=(9,5))
    for key, label in [("CAPEX_HUIZHOU_5WT","惠州代理"),("CAPEX_XIANGYANG_5WT","襄阳代理"),("CAPEX_FUJIAN_5WT","福建代理")]:
        selected = sorted([r for r in sensitivity if r["benchmark_id"] == key and r["fixed_opex_rate"] == .03 and r["collection_storage_cny_t"] == 250], key=lambda r:r["capacity_t_y"])
        ax.plot([r["capacity_t_y"]/10000 for r in selected], [r["lcor_cny_per_t_lce"]/10000 for r in selected], "o-", label=label)
    ax.axhline(b["lcor_cny_per_t_lce"]/10000, color="#777777", linestyle="--", label="未计固定成本的B")
    ax.set(xlabel="假设设计规模（万吨/年）", ylabel="情景LCOR（万元/吨LCE）", title="投资与利用率敏感性；固定OPEX率3%、收集费250元/吨为假设")
    ax.legend(frameon=False, fontsize=9)
    save(fig, OUTPUT, "fig10_capital_sensitivity")
    max_year = next(r for r in annual if r["year"] == 2040)
    frontier = rows("pareto_brine.csv")
    min_distance = min(float(r["utopia_distance"]) for r in frontier)
    summary = {"result_scope": "条件情景，非湖北观测拟合预测或完整LCA/财务可研",
        "scenario_count": len(scenarios), "status_counts": dict(Counter(r["status"] for r in scenarios)),
        "balance_max_relative_error": errors, "b": b, "year2040": max_year,
        "distance_weighted_km": sum(r["flow_t"]*r["road_distance_km"] for r in routes)/tonnes,
        "b_equal_distance_count": sum(abs(float(r["utopia_distance"])-min_distance) < 1e-10 for r in frontier),
        "sensitivity_min_lcor": min(r["lcor_cny_per_t_lce"] for r in sensitivity),
        "sensitivity_max_lcor": max(r["lcor_cny_per_t_lce"] for r in sensitivity),
        "images": sorted(p.name for p in OUTPUT.glob("*.png"))}
    write_json(RESULTS/"report_metrics.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    build_summary()
