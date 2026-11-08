# -*- coding: utf-8 -*-
"""
C_water_carbon_supplement.py —— P17 水—碳权衡：同等绿电比例下，低排放电网反而更耗水

三情景只改电网结构（直再 60%、绿电 55% 不变）：
  低排放电网（水核为主）  EF 0.3140、耗水 2.5 L/kWh
  中排放电网（全国平均基线）  EF 0.5366、耗水 1.2 L/kWh
  高排放电网（煤电为主）  EF 0.7488、耗水 1.0 L/kWh

输出 data_cohort/water_carbon_three.json + water_carbon_curve.csv（3 电网 × 21 绿电比例）

【AI 辅助编程说明】Prompt："固定直再 60%，只切换三种电网结构，算 55% 绿电时的 GWP 与水耗，
并扫描 0—100% 绿电形成三条水—碳曲线。" 人工校验：低 843/10.53、高 1,424/8.53、基线 1,141/8.80。
"""
from C_env_econ_core import *

f = simulate(KNEE_D)
LABEL = {
    "low": "低排放电网（水核为主）",
    "base": "中排放电网（全国平均基线）",
    "high": "高排放电网（煤电为主）",
}

three = {}
for key, label in LABEL.items():
    ef = LCA_T["grid_ef"][key]
    gw = LCA_T["grid_water_m3_per_kwh"][key]
    e = lca(f, KNEE_G, grid_ef=ef, grid_water=gw)
    h = lca(f, 1.0, grid_ef=ef, grid_water=gw)
    three[key] = {
        "label": label, "grid_ef": ef, "grid_water_m3_per_kwh": gw,
        "gwp_kg_per_t": e["gwp_kg_per_t"], "water_m3_per_t": e["water_m3_per_t"],
        "gwp_at_100_green": h["gwp_kg_per_t"], "water_at_100_green": h["water_m3_per_t"],
        "water_drop_0_to_100": lca(f, 0.0, grid_ef=ef, grid_water=gw)["water_m3_per_t"] - h["water_m3_per_t"],
    }

rows = []
for key in ("low", "base", "high"):
    ef = LCA_T["grid_ef"][key]
    gw = LCA_T["grid_water_m3_per_kwh"][key]
    for i in range(21):
        g = i / 20
        e = lca(f, g, grid_ef=ef, grid_water=gw)
        rows.append([ef, gw, g, e["gwp_kg_per_t"], e["water_m3_per_t"]])

print("=" * 78)
print("P17 水—碳权衡（直再 60%、绿电 55% 不变，只改电网结构）")
for key in ("low", "base", "high"):
    r = three[key]
    print(f"  {r['label']:<14} GWP {r['gwp_kg_per_t']:7.1f}   水 {r['water_m3_per_t']:6.2f} m³/t"
          f"   （绿电 0→100% 可再节水 {r['water_drop_0_to_100']:.2f} m³/t）")
print("  机理：水电蒸发、核冷耗水高；煤电闭式循环耗水低但碳强度高 → 同绿电比例下两者反向")
save_json("water_carbon_three.json", {"scenarios": three, "green_share": KNEE_G, "direct_share": KNEE_D})
save_csv("water_carbon_curve.csv",
         ["grid_ef", "grid_water_m3_per_kwh", "green_share", "gwp_kg_per_t", "water_m3_per_t"], rows)
