# -*- coding: utf-8 -*-
"""
C_finance_supplement.py —— P20 财务可行性（全园 20,000 t/a 全量口径）

  · 20,000 t/a 全量进料（含 4,000 t 梯次，按同单吨毛利简化）、CAPEX 7.20 亿元、
    固定人工环保 2,500 万元/a、WACC 8%、20 年、税前无杠杆
  · 利用率 22% / 46%（盈亏平衡）/ 60% / 80% / 100% → NPV −5.06 / 0.00 / 2.88 / 7.06 / 11.24 亿元
  · 静态回收期 33.0 / 9.8 / 7.0 / 5.0 / 3.8 年；IRR −4.4% / 8.0% / 13.0% / 19.6% / 25.8%
  · 锂价 10k/22k/50k → NPV 8.26 / 11.24 / 18.21 亿元
  · 所得税 25% 后：NPV 7.52 亿元、回收 4.8 年、IRR 20.3%
  · CAPEX +20% → NPV 9.81 亿元；收料 +10% → LCOR −4,122 元/t、NPV 8.09 亿元
  · 再生链 16,000 t 严格口径：NPV 9.00 亿元（regen_basis_16000 备查）

输出 data_cohort/finance.json、finance_utilization.csv

【AI 辅助编程说明】Prompt："年度财务按 20,000 t/a 全量口径（含梯次，按同单吨毛利简化），
算五个利用率档的 NPV/回收期/IRR，再做锂价、税率、CAPEX 与收料价扰动，并保留再生链 16,000 t 口径备查。"
人工校验：满负荷年现金流 1.88 亿元 = 10,643×20,000 − 2,500 万；NPV = −7.20 + 1.88×9.8181 = 11.24 亿元；
          再生链口径 1.50 亿元 / 9.00 亿元 = 全量口径 ÷ 1.25。
"""
from C_env_econ_core import *

be = break_even_util(capex=FULL_CAPEX, q_cap=FULL_Q, fixed=FULL_FIXED)
utils = [0.22, be, 0.60, 0.80, 1.00]
rows = [financial(u, capex=FULL_CAPEX, q_cap=FULL_Q, fixed=FULL_FIXED) for u in utils]
for r in rows:
    r["util_pct"] = r["util"] * 100

li_rows = {str(p): financial(1.0, price_usd=p, capex=FULL_CAPEX, q_cap=FULL_Q, fixed=FULL_FIXED)
           for p in (TEA["li2co3_price_usd_per_t"]["low"], TEA["li2co3_price_usd_per_t"]["base"],
                     TEA["li2co3_price_usd_per_t"]["high"])}
tax = after_tax_financial(1.0, capex=FULL_CAPEX, q_cap=FULL_Q, fixed=FULL_FIXED)

capex_up = financial(1.0, capex=FULL_CAPEX * 1.2, q_cap=FULL_Q, fixed=FULL_FIXED)

f = simulate(KNEE_D)
ec = tea(f, 22000, KNEE_G)
var = ec["purchase"] + ec["collection"] + ec["electricity"] + ec["heat"] + ec["reagent"] + ec["water_cost"]
purchase_up = 0.10 * ec["purchase"]
cf_up = (ec["revenue"] - var - purchase_up) * FULL_Q - FULL_FIXED
lcor_up = (FULL_CAPEX * CRF + FULL_FIXED) / FULL_Q + var + purchase_up - ec["revenue"]

regen = financial(1.0)          # 再生链 16,000 t 严格口径（备查）

out = {
    "unit": "全园 20,000 t/a 全量进料（含 4,000 t 梯次，按同单吨毛利简化）；CAPEX 7.20 亿元；WACC 8%；20 年；税前无杠杆",
    "cascade": cascade_note(),
    "fixed_labor_env_yi_per_a": FULL_FIXED / 1e8,
    "variable_cost_yuan_per_t": var,
    "contribution_yuan_per_t": ec["revenue"] - var,
    "break_even_util": be,
    "utilization_rows": rows,
    "lithium_price_scenarios": li_rows,
    "after_tax_25pct": tax,
    "capex_plus_20pct": capex_up,
    "purchase_plus_10pct": {"lcor_yuan_per_t": lcor_up, "npv_yi": (-FULL_CAPEX + cf_up * AF) / 1e8},
    "regen_basis_16000": regen,
    "sensitivity_notes": {
        "capex_up_20": "CAPEX 7.20 → 8.64 亿元，现金流不变",
        "purchase_up_10": "来料 16,041 → 17,645 元/t，LCOR 上升 1,604 元/t",
        "regen_basis": "梯次线 4,000 t 按同单吨毛利并入；严格口径（再生链 16,000 t、CAPEX 5.76 亿元、固定费 2,000 万元/a）NPV 9.00 亿元",
    },
}

print("=" * 88)
print("P20 财务可行性（全园 20,000 t/a 全量口径、CAPEX 7.20 亿元、WACC 8%、20 年、税前）")
print(f"  盈亏平衡利用率 {be*100:.1f}%；单吨贡献 {ec['revenue']-var:.0f} 元/t；固定费 {FULL_FIXED/1e8:.2f} 亿元/a")
print(f"  {'利用率':>6}{'年处理 t':>10}{'LCOR':>10}{'现金流 亿':>11}{'NPV 亿':>9}{'回收期 a':>10}{'IRR':>8}")
for r in rows:
    print(f"  {r['util_pct']:>5.0f}%{r['q_t']:>10,.0f}{r['lcor']:>10,.0f}{r['cashflow_yi']:>11.2f}"
          f"{r['npv_yi']:>9.2f}{r['payback_a']:>10.1f}{r['irr']*100:>7.1f}%")
print(f"  锂价 10k/22k/50k → NPV " + " / ".join(f"{v['npv_yi']:.2f}" for v in li_rows.values()) + " 亿元")
print(f"  所得税 25%：NPV {tax['npv_yi']:.2f} 亿元、回收 {tax['payback_a']:.1f} 年、IRR {tax['irr']*100:.1f}%")
print(f"  CAPEX +20% → NPV {capex_up['npv_yi']:.2f} 亿元；收料 +10% → LCOR {lcor_up:.0f} 元/t、"
      f"NPV {(-FULL_CAPEX + cf_up * AF)/1e8:.2f} 亿元")
print(f"  再生链 16,000 t 口径（备查）：NPV {regen['npv_yi']:.2f} 亿元、回收 {regen['payback_a']:.1f} 年")
save_json("finance.json", out)
save_csv("finance_utilization.csv",
         ["util_pct", "q_t", "lcor_yuan_per_t", "cashflow_yi", "npv_yi", "payback_a", "irr"],
         [[r["util_pct"], r["q_t"], r["lcor"], r["cashflow_yi"], r["npv_yi"], r["payback_a"], r["irr"]] for r in rows])
