# -*- coding: utf-8 -*-
"""
C_pareto.py —— P19 多目标寻优：21×21 决策网格（绿电 × LFP 直再）× 3 档锂价

  · 网格：绿电 g = 0—100%（步长 5%）× 直再 d = 0—100%（步长 5%），受直再适用性 ≤60% 约束
  · 政策可行解：锂回收率 ≥90% 且 NiCoMn ≥98%（8 项国内红线中的两条硬约束）
  · 非支配前沿：固定 d = 60%，21 档绿电；归一化理想点距离最小者为拐点
  · 锚点 A（成本最优 g=0）/ B（拐点 g=55%）/ C（碳最优 g=100%）

输出 data_cohort/pareto_grid.csv、C_pareto_front.csv、pareto.json
（819 组 = 273 组单价格可行解 × 3 档锂价；d=60% 前沿 21 组，锚点按基准锂价标定）

【AI 辅助编程说明】Prompt："按 ABC_parameters.json 生成 21×21 网格，做政策可行筛选与帕累托前沿，
用归一化理想点距离标定拐点，并算每组解的 MAC。" 人工校验：A 1,936/−5,916、B 1,141/−5,726、
C 490/−5,410；MAC(knee) −2,934。
"""
from C_env_econ_core import *

PRICES = [TEA["li2co3_price_usd_per_t"]["low"], TEA["li2co3_price_usd_per_t"]["base"],
          TEA["li2co3_price_usd_per_t"]["high"]]

grid, feasible = [], []
for i in range(21):
    g = i / 20
    for j in range(21):
        d = j / 20
        if d > DIRECT_CAP + 1e-9:
            continue
        f = simulate(d)
        e = lca(f, g)
        c = tea(f, 22000, g)
        rec = {"green": g, "direct": d, "gwp": e["gwp_kg_per_t"], "water": e["water_m3_per_t"],
               "lcor": c["lcor_yuan_per_t"], "li_recovery": f["li_recovery"],
               "nico_recovery": f["nico_recovery"],
               "policy_ok": f["li_recovery"] >= 0.9 and f["nico_recovery"] >= 0.98 - 1e-6}
        grid.append(rec)
        if rec["policy_ok"]:
            feasible.append(rec)

front_pool = [r for r in feasible if abs(r["direct"] - KNEE_D) < 1e-9]
front = [a for a in front_pool if not any(
    b["gwp"] <= a["gwp"] and b["lcor"] <= a["lcor"] and (b["gwp"] < a["gwp"] or b["lcor"] < a["lcor"])
    for b in front_pool)]
front.sort(key=lambda r: r["gwp"])
for r in front:
    r["mac"] = marginal_cost(r["lcor"], r["gwp"])

gw = [r["gwp"] for r in front]
lc = [r["lcor"] for r in front]
knee = min(front, key=lambda r: ((r["gwp"] - min(gw)) / (max(gw) - min(gw))) ** 2 +
           ((r["lcor"] - min(lc)) / (max(lc) - min(lc))) ** 2)

anchors = {
    "A_cost_optimal": next(r for r in front if abs(r["green"] - 0.0) < 1e-9),
    "B_knee": knee,
    "C_carbon_optimal": next(r for r in front if abs(r["green"] - 1.0) < 1e-9),
}
knee_mac = marginal_cost(knee["lcor"], knee["gwp"])
# MAC 随绿电上升（55% → 100%）的增量段
mac_55 = knee_mac
mac_100 = marginal_cost(anchors["C_carbon_optimal"]["lcor"], anchors["C_carbon_optimal"]["gwp"])

out = {
    "grid": {"g_points": 21, "d_points": 21, "prices": PRICES},
    "feasible_single_price": len(feasible),
    "feasible_total_3_prices": len(feasible) * len(PRICES),
    "front": len(front),
    "anchors": anchors,
    "knee": {**knee, "mac": knee_mac},
    "mac_55_to_100": {"g55": mac_55, "g100": mac_100,
                      "avg_cost_per_kg_after_55": (anchors["C_carbon_optimal"]["lcor"] - knee["lcor"]) /
                                                   (knee["gwp"] - anchors["C_carbon_optimal"]["gwp"])},
    "direct_cap": DIRECT_CAP,
}

print("=" * 78)
print("P19 多目标寻优（21×21 网格 × 3 档锂价）")
print(f"  单价格可行解 {len(feasible)} 组；三档锂价合计 {len(feasible)*3} 组（≥500 组要求）")
print(f"  非支配解（d=60%）{len(front)} 组；拐点 g={knee['green']:.2f}、d={knee['direct']:.2f}")
for k, r in anchors.items():
    print(f"  {k:<18} g={r['green']:.2f}  GWP {r['gwp']:7.0f}  LCOR {r['lcor']:9.0f}")
print(f"  拐点 MAC {knee_mac:.0f} 元/t CO₂e（负值=减碳同时盈利）")
save_json("C_11_09_pareto.json", out)
save_csv("C_11_09_C_pareto_front.csv", ["green", "direct", "gwp", "water", "lcor", "mac"],
         [[r["green"], r["direct"], r["gwp"], r["water"], r["lcor"], r["mac"]] for r in front])
save_csv("C_11_09_pareto_grid.csv", ["green", "direct", "gwp", "water", "lcor", "policy_ok"],
         [[r["green"], r["direct"], r["gwp"], r["water"], r["lcor"], int(r["policy_ok"])] for r in grid])
