"""
04_echelon_tea.py — 模块3a：梯次利用收益折现 + 末端回收 TEA（LCOR/NPV）+ 价格反转
【AI 辅助编程提示词记录】
Prompt: "TEA 脚本：梯次利用非线性容量配置+收益折现；末端回收三工艺×两电池 TEA；复现碳酸锂价格反转机制。"
是否经人工校验：是
"""
import csv, importlib.util, os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("config", os.path.join(_HERE, "00_config.py"))
config = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(config)
DATA_DIR, RESULTS_DIR = config.DATA_DIR, config.RESULTS_DIR
WACC, CRF = config.WACC, config.capital_recovery_factor()

def load_csv(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))

def echelon_tea(soh_init=0.80, scenario="ESS", soh_end=0.50, mass_t=10000.0, chemistry="LFP"):
    soh_scen = {r["echelon_scenario"]: r for r in load_csv("soh_echelon_parameters.csv")}
    chem = {r["chemistry"]: r for r in load_csv("battery_chemistry.csv")}[chemistry]
    sp = float(chem["specific_energy_Wh_per_kg"])
    cap_init = mass_t * 1000 * sp / 1000 * soh_init
    fade = float(soh_scen[scenario]["capacity_fade_rate_per_year"])
    life_years = max(1, (soh_init - soh_end) / fade)
    annual_throughput = float(soh_scen[scenario]["annual_energy_throughput_kWh_per_kWh"])
    rev_per_kwh = float(soh_scen[scenario]["revenue_CNY_per_kWh"])
    refurb = float(soh_scen[scenario]["refurb_cost_CNY_per_kWh"])
    npv = -cap_init * refurb; annual_revenue = 0
    for y in range(1, int(life_years) + 1):
        avg_cap = cap_init * (1 - fade * (y - 0.5))
        energy = max(0, avg_cap) * annual_throughput
        rev = energy * rev_per_kwh; annual_revenue += rev
        npv += rev / (1 + WACC) ** y
    levelized_rev = npv / (cap_init * life_years) if cap_init > 0 else 0
    return {"soh_init": soh_init, "scenario": scenario, "soh_end_threshold": soh_end,
        "echelon_capacity_kWh": round(cap_init, 0), "life_years": round(life_years, 1),
        "revenue_CNY": round(annual_revenue, 0), "refurb_cost_CNY": round(cap_init * refurb, 0),
        "npv_CNY": round(npv, 0), "levelized_revenue_CNY_per_kWh": round(levelized_rev, 2)}

def recycling_tea(route, chemistry, li2co3_price_CNY_per_t, mass_t=50000.0):
    proc = {r["process"]: r for r in load_csv("process_parameters.csv")}[route]
    chem = {r["chemistry"]: r for r in load_csv("battery_chemistry.csv")}[chemistry]
    tea = {r["parameter"]: r["value"] for r in load_csv("tea_parameters.csv")}
    li_content = float(chem["li_content_kg_per_kg"])
    li_rec = float(proc["li_recovery_rate"])
    li2co3_t = mass_t * 1000 * li_content * li_rec / 0.1878 / 1000
    capex = float(proc["capex_CNY_per_t_capacity"]) * mass_t
    annual_capex = capex * CRF
    opex = float(proc["opex_CNY_per_kg_battery"]) * mass_t * 1000
    labor = float(tea["labor_cost_CNY_per_kg"]) * mass_t * 1000
    transport = float(tea["transport_cost_CNY_per_tkm"]) * mass_t * 100
    if route == "direct_recycling":
        li_revenue = 0; li_cost = li2co3_t * li2co3_price_CNY_per_t * 0.3
    else:
        li_revenue = li2co3_t * li2co3_price_CNY_per_t; li_cost = 0
    metal_revenue = 0
    if chemistry == "NMC811":
        ni_t = mass_t * 1000 * float(chem["ni_content_kg_per_kg"]) * float(proc["ni_recovery_rate"]) / 1000
        co_t = mass_t * 1000 * float(chem["co_content_kg_per_kg"]) * float(proc["co_recovery_rate"]) / 1000
        metal_revenue = ni_t * float(tea["ni_sulfate_price_CNY_per_t"]) + co_t * float(tea["co_sulfate_price_CNY_per_t"])
    cu_t = mass_t * 1000 * float(chem["cu_content_kg_per_kg"]) * 0.98 / 1000
    al_t = mass_t * 1000 * float(chem["al_content_kg_per_kg"]) * 0.98 / 1000
    cu_al_revenue = cu_t * float(tea["copper_price_CNY_per_t"]) + al_t * float(tea["aluminum_price_CNY_per_t"])
    total_cost = annual_capex + opex + labor + transport + li_cost
    total_revenue = li_revenue + metal_revenue + cu_al_revenue
    net_cost = total_cost - total_revenue
    lcor = net_cost / mass_t
    gwp_recycling = float(proc["gwp_kgCO2e_per_kg_material"]) * mass_t
    gwp_primary = 14.5 * mass_t * 1000 * li_content / 1000
    gwp_reduction = max(0, gwp_primary - gwp_recycling)
    mac = net_cost / gwp_reduction if gwp_reduction > 0 else 0
    return {"scenario_id": f"{route}_{chemistry}_{li2co3_price_CNY_per_t}", "chemistry": chemistry,
        "route": route, "li2co3_price_CNY_per_t": li2co3_price_CNY_per_t,
        "lcor_CNY_per_kg": round(lcor, 4), "npv_CNY": round(-net_cost, 0),
        "mac_CNY_per_tCO2e": round(mac, 2), "gwp_reduction_tCO2e": round(gwp_reduction, 1), "feasible": True}

def run_echelon_tea():
    results = []
    for soh in [0.70, 0.80, 0.90]:
        for scen in ["ESS", "CBS", "LSV"]:
            for end in [0.40, 0.50, 0.60, 0.70]:
                results.append(echelon_tea(soh, scen, end))
    out = os.path.join(RESULTS_DIR, "echelon_tea.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    print(f"[04] 梯次 TEA: {len(results)} 组 -> {out}")
    return results

def run_recycling_tea():
    results = []; price_reversal = []
    for route in ["hydrometallurgy", "pyrometallurgy", "direct_recycling"]:
        for chem in ["LFP", "NMC811"]:
            for pn, pv in [("low", 70000), ("baseline", 154000), ("high", 350000)]:
                r = recycling_tea(route, chem, pv); r["price_scenario"] = pn; results.append(r)
    out = os.path.join(RESULTS_DIR, "lca_tea.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    for chem in ["LFP", "NMC811"]:
        for pn in ["low", "baseline", "high"]:
            rows = sorted([r for r in results if r["chemistry"] == chem and r["price_scenario"] == pn], key=lambda x: x["lcor_CNY_per_kg"])
            for i, r in enumerate(rows):
                price_reversal.append({"chemistry": chem, "price_scenario": pn,
                    "li2co3_price_CNY_per_t": r["li2co3_price_CNY_per_t"], "rank": i + 1,
                    "route": r["route"], "lcor_CNY_per_kg": r["lcor_CNY_per_kg"]})
    out2 = os.path.join(RESULTS_DIR, "price_reversal.csv")
    with open(out2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=price_reversal[0].keys()); w.writeheader(); w.writerows(price_reversal)
    print(f"[04] 回收 TEA: {len(results)} 组 -> {out}")
    print(f"[04] 价格反转: {len(price_reversal)} 行 -> {out2}")
    for chem in ["LFP", "NMC811"]:
        print(f"--- {chem} 价格反转 ---")
        for pn in ["low", "baseline", "high"]:
            ranks = sorted([pr for pr in price_reversal if pr["chemistry"] == chem and pr["price_scenario"] == pn], key=lambda x: x["rank"])
            order = " > ".join(f"{r['route'][:4]}({r['lcor_CNY_per_kg']:.2f})" for r in ranks)
            print(f"  {pn:>9}: {order}")
    return results

if __name__ == "__main__":
    run_echelon_tea(); run_recycling_tea()
