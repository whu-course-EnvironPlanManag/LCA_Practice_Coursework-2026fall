"""
06_pareto_sensitivity.py — 模块3c：多目标寻优 + 敏感性
【AI 辅助编程提示词记录】
Prompt: "多目标寻优：决策变量 SOH阈值/绿电比例/工艺配比，外部情景碳酸锂价格，>=500组，剔除非可行解，Pareto前沿+拐点。"
是否经人工校验：是
"""
import csv, importlib.util, os, sys, random, math
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("config", os.path.join(_HERE, "00_config.py"))
config = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(config)
DATA_DIR, RESULTS_DIR = config.DATA_DIR, config.RESULTS_DIR
_spec3 = importlib.util.spec_from_file_location("policy_engine", os.path.join(_HERE, "03_policy_engine.py"))
pe = importlib.util.module_from_spec(_spec3); _spec3.loader.exec_module(pe)
evaluate_compliance = pe.evaluate_compliance

def load_csv(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))

def evaluate_scenario(soh_threshold, green_ratio, route_mix, price_scenario):
    proc = {r["process"]: r for r in load_csv("process_parameters.csv")}
    chem_lfp = {r["chemistry"]: r for r in load_csv("battery_chemistry.csv")}["LFP"]
    routes = ["hydrometallurgy", "pyrometallurgy", "direct_recycling"]
    weights = route_mix
    li_rec = sum(float(proc[r]["li_recovery_rate"]) * w for r, w in zip(routes, weights))
    gwp_per_kg = sum(float(proc[r]["gwp_kgCO2e_per_kg_material"]) * w for r, w in zip(routes, weights))
    energy_mj = sum(float(proc[r]["energy_MJ_per_kg_material"]) * w for r, w in zip(routes, weights))
    electrode_powder = sum(float(proc[r]["electrode_powder_recovery_rate"]) * w for r, w in zip(routes, weights))
    fluorine = sum(float(proc[r]["fluorine_fixation_rate"]) * w for r, w in zip(routes, weights))
    wastewater = sum(float(proc[r]["wastewater_recycle_rate"]) * w for r, w in zip(routes, weights))
    grid_cf = 0.581 * (1 - green_ratio) + 0.020 * green_ratio
    power_gwp = (energy_mj / 3.6) * grid_cf
    # ---- SOH 阈值耦合（复用 04_echelon_tea.py 的梯次模型公式, 参数源 soh_echelon_parameters.csv / 文献6）----
    soh_init = 0.80          # 退役初始 SOH 均值（文献6: 70/80/90 情景的中位）
    fade = 0.04              # ESS 场景年衰减率（soh_echelon_parameters.csv）
    soh_t = max(0.40, min(soh_threshold, soh_init - 0.02))
    echelon_years = max(0.5, (soh_init - soh_t) / fade)          # 梯次服务年限, 随终止阈值降低而延长
    echelon_share = 0.50     # 经梯次利用后再生的电池比例（文献5 三级分流, 80-90% SOH 段占比）
    cap_kwh_per_kg = float(chem_lfp["specific_energy_Wh_per_kg"]) / 1000 * soh_init  # 每kg电池可用容量kWh(0.16*SOH)
    ech_rev = 0.68           # ESS 度电收益 CNY/kWh（soh_echelon_parameters.csv）
    ech_refurb = 150.0       # 梯次改造一次性成本 CNY/kWh
    ech_throughput = 2500.0  # 年等效循环 kWh/kWh·a
    echelon_net = (echelon_years * ech_throughput * cap_kwh_per_kg * ech_rev
                   - cap_kwh_per_kg * ech_refurb) / max(1.0, echelon_years)  # 年化净收益/每kg梯次电池
    echelon_credit = echelon_share * echelon_net * echelon_years / (1 + echelon_years)  # 折算到再生环节的收益抵扣
    new_batt_gwp_per_kwh = 65.0   # 新电池隐含碳强度 kgCO2e/kWh（文献6, 梯次替代新电池需求）
    gwp_credit = (echelon_share * cap_kwh_per_kg * new_batt_gwp_per_kwh
                  * min(1.0, echelon_years / 5.0))  # 梯次延寿避免的新电池生产排放
    total_gwp = max(0.5, gwp_per_kg + power_gwp - gwp_credit)
    prices = {"low": 70000, "baseline": 154000, "high": 350000}
    li_price = prices[price_scenario]
    li_content = float(chem_lfp["li_content_kg_per_kg"])
    li2co3_per_kg = li_content * li_rec / 0.1878
    hydro_weight = weights[0] + weights[1]; direct_weight = weights[2]
    li_revenue = li2co3_per_kg * li_price * hydro_weight / 1000
    li_cost = li2co3_per_kg * li_price * direct_weight * 0.3 / 1000
    opex = sum(float(proc[r]["opex_CNY_per_kg_battery"]) * w for r, w in zip(routes, weights))
    lcor = opex + li_cost - li_revenue - echelon_credit
    scenario = {"li_recovery_rate": li_rec, "ni_recovery_rate": 0.98, "co_recovery_rate": 0.98,
        "mn_recovery_rate": 0.98, "electrode_powder_recovery": electrode_powder,
        "fluorine_fixation_rate": fluorine, "energy_kgce_per_t": energy_mj / 29.3 * 1000,
        "wastewater_recycle_rate": wastewater, "recycled_li_content": 0.10, "eu_year": 2031}
    result = evaluate_compliance(scenario)
    return {"gwp": round(total_gwp, 4), "lcor": round(lcor, 4), "soh_threshold": soh_threshold,
        "green_ratio": green_ratio, "route_mix": f"{weights[0]:.2f},{weights[1]:.2f},{weights[2]:.2f}",
        "li_recovery": round(li_rec, 4), "feasible": result.is_compliant}

def find_pareto_front(points):
    front = []
    for p in points:
        dominated = False
        for q in points:
            if p is q: continue
            if q["gwp"] <= p["gwp"] and q["lcor"] <= p["lcor"] and (q["gwp"] < p["gwp"] or q["lcor"] < p["lcor"]):
                dominated = True; break
        if not dominated: front.append(p)
    return front

def find_knee_point(front):
    if not front: return None
    gwp_vals = [p["gwp"] for p in front]; lcor_vals = [p["lcor"] for p in front]
    gwp_min, gwp_max = min(gwp_vals), max(gwp_vals)
    lcor_min, lcor_max = min(lcor_vals), max(lcor_vals)
    best_dist = float("inf"); knee = None
    for p in front:
        gwp_norm = (p["gwp"] - gwp_min) / (gwp_max - gwp_min) if gwp_max > gwp_min else 0
        lcor_norm = (p["lcor"] - lcor_min) / (lcor_max - lcor_min) if lcor_max > lcor_min else 0
        dist = math.sqrt(gwp_norm ** 2 + lcor_norm ** 2)
        if dist < best_dist: best_dist = dist; knee = p
    return knee

def run_pareto(n=1200):
    random.seed(42); all_points = []
    for _ in range(n):
        soh_t = round(random.uniform(0.40, 0.90), 2)
        green = round(random.uniform(0.0, 1.0), 2)
        w = [random.random() for _ in range(3)]; s = sum(w)
        weights = [round(x / s, 2) for x in w]; weights[2] = round(1 - weights[0] - weights[1], 2)
        price = random.choice(["low", "baseline", "high"])
        all_points.append(evaluate_scenario(soh_t, green, weights, price))
    feasible = [p for p in all_points if p["feasible"]]
    print(f"[06] 总工况: {len(all_points)}, 可行解: {len(feasible)}")
    front = find_pareto_front(feasible); knee = find_knee_point(front)
    for p in front:
        p["is_knee"] = (p is knee); p["is_anchor"] = False
    if front:
        min(front, key=lambda x: x["gwp"])["is_anchor"] = True
        min(front, key=lambda x: x["lcor"])["is_anchor"] = True
    out = os.path.join(RESULTS_DIR, "pareto_front.csv")
    fieldnames = list(feasible[0].keys()) + ["is_knee", "is_anchor"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(feasible)
    print(f"[06] Pareto 前沿: {len(front)} 点")
    if knee: print(f"[06] 拐点: SOH={knee['soh_threshold']:.0%}, 绿电={knee['green_ratio']:.0%}, GWP={knee['gwp']:.4f}, LCOR={knee['lcor']:.4f}")
    print(f"[06] 输出: {out}")
    sens = []
    for soh in [0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
        for pn, pv in [("low", 70000), ("baseline", 154000), ("high", 350000)]:
            p = evaluate_scenario(soh, 0.5, [0.4, 0.1, 0.5], pn)
            sens.append({"soh_threshold": soh, "price_scenario": pn, "li2co3_price": pv,
                "gwp": p["gwp"], "lcor": p["lcor"]})
    out2 = os.path.join(RESULTS_DIR, "sensitivity.csv")
    with open(out2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sens[0].keys()); w.writeheader(); w.writerows(sens)
    print(f"[06] 敏感性: {len(sens)} 行 -> {out2}")
    return front, knee

if __name__ == "__main__":
    run_pareto()
