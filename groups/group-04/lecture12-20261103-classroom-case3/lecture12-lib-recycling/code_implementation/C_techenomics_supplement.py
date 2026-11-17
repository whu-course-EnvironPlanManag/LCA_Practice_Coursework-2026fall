# -*- coding: utf-8 -*-
"""
C_techenomics_supplement.py —— P21 技术经济：成本 8 项、收入 4 项、LCOR 与 MAC

  · 成本合计 25,298 元/t（8 项全计，含热能 182、水耗 26）
  · 收入合计 31,024 元/t（碳酸锂 10,137 / 再生粉 4,288 / 镍钴锰盐 9,035 / 磷酸铁+铜+铝 7,563）
  · LCOR −5,726 元/t（负值=净收益）；MAC −2,934 元/t CO₂e（减碳同时盈利）
  · 锂价 10,000—50,000 USD/t → LCOR −4,207 ~ −9,271 元/t

输出 data_cohort/techenomics.json、cost_revenue.csv

【AI 辅助编程说明】Prompt："按 parameters.json 的 TEA 口径把 8 项成本与 4 项收入拆开，
算 LCOR、MAC 与锂价区间，并标注未计入的成本。" 人工校验：分项之和 = 25,298 / 31,024。
"""
from C_env_econ_core import *

f = simulate(KNEE_D)
ec = tea(f, TEA["li2co3_price_usd_per_t"]["base"], KNEE_G)

costs = [
    ("来料采购", ec["purchase"], "锂 0.0952 t LCE × 158,400 × 0.72 + 镍钴 × 0.35 + 1,500"),
    ("资本年金化", ec["capex_ann"], "5.76 亿元 × 0.10185 / 16,000 t（再生线 CAPEX）"),
    ("电力", ec["electricity"], "2,972 kWh × 0.684 元/kWh（含绿电溢价）"),
    ("热能 / 天然气", ec["heat"], "2.80 GJ × 65 元/GJ"),
    ("收集运输与拆解", ec["collection"], "200 km 排放核算半径"),
    ("试剂", ec["reagent"], "H₂SO₄ / NaOH / Na₂CO₃ / H₂O₂ + 萃取剂等辅料"),
    ("新水与废水处理", ec["water_cost"], "工艺水 6.37 m³ × 3.6 + 废水 0.51 m³ × 6.0"),
    ("人工运维 + 环保税费", ec["labor"] + ec["env"], "800 + 450 元/t"),
]
cost_total = sum(v for _, v, _ in costs)

revenues = [
    ("碳酸锂（电池级）", ec["revenue_items"]["lithium_carbonate"], "0.064 t LCE × 158,400 元/t"),
    ("再生 LFP 正极粉", ec["revenue_items"]["regen_powder"], "0.105 t × 40,934 元/t（新粉 88 折）"),
    ("镍钴锰盐", ec["revenue_items"]["nicomn_salts"], "Ni/Co/Mn 盐按 85% 折价"),
    ("磷酸铁 + 铜 + 铝", ec["revenue_items"]["fepo4_cu_al"], "FePO₄ 4,000；Cu 70,000；Al 18,000"),
]
rev_total = sum(v for _, v, _ in revenues)

lcor = cost_total + 0 - rev_total
mac = marginal_cost(lcor, lca(f, KNEE_G)["gwp_kg_per_t"])

price_range = {}
for k in ("low", "base", "high"):
    p = TEA["li2co3_price_usd_per_t"][k]
    price_range[str(p)] = tea(f, p, KNEE_G)["lcor_yuan_per_t"]

out = {
    "unit": "元/t 再生链来料（满负荷 16,000 t/a、税前、无杠杆）",
    "costs": [{"item": n, "yuan_per_t": v, "formula": d, "share_pct": v / cost_total * 100} for n, v, d in costs],
    "cost_total": cost_total,
    "revenues": [{"item": n, "yuan_per_t": v, "basis": d, "share_pct": v / rev_total * 100} for n, v, d in revenues],
    "revenue_total": rev_total,
    "lcor_yuan_per_t": lcor,
    "mac_yuan_per_t_co2e": mac,
    "lithium_price_scenarios": price_range,
    "not_counted": {
        "rd_pct_revenue": 3, "rd_yuan_per_t": rev_total * 0.03,
        "sga_yuan_per_t": 930, "finance_working_capital_yuan_per_t": 620,
        "land_and_idc": "未计土地与建设期利息",
        "note": "上表为税前、无杠杆、满负荷口径；所得税 25% 后见 P20 财务可行性",
    },
    "cascade": cascade_note(),
}

print("=" * 78)
print("P21 技术经济（拐点方案：直再 60%、绿电 55%、锂价 22,000 USD/t）")
print(f"  {'成本项':<12}{'元/t':>10}{'占比':>9}")
for n, v, _ in costs:
    print(f"  {n:<12}{v:>10.0f}{v/cost_total*100:>8.1f}%")
print(f"  {'合计':<12}{cost_total:>10.0f}")
print(f"  {'收入项':<12}{'元/t':>10}")
for n, v, _ in revenues:
    print(f"  {n:<12}{v:>10.0f}")
print(f"  {'合计':<12}{rev_total:>10.0f}")
print(f"  LCOR {lcor:.0f} 元/t（负值=净收益）；MAC {mac:.0f} 元/t CO₂e")
print(f"  锂价 10k/22k/50k → LCOR " + "".join(f"{v:.0f}  " for v in price_range.values()))
save_json("techenomics.json", out)
save_csv("cost_revenue.csv", ["type", "item", "yuan_per_t", "share_pct"],
         [["cost", n, v, v / cost_total * 100] for n, v, _ in costs] +
         [["revenue", n, v, v / rev_total * 100] for n, v, _ in revenues])
