# -*- coding: utf-8 -*-
"""
B_policy_engine.py —— 政策量化引擎：把法规条文转成可计算断言
覆盖：工信部 2024 年规范条件（国内准入）+ 欧盟 2023/1542（出口合规）+ 再生料含量
运行：python B_policy_engine.py
输出：data_cohort/B_policy_results.json

【AI 辅助编程说明】
  Prompt 摘要："把工信部《规范条件（2024 年本）》与欧盟 2023/1542 条文转成可计算断言，
  对三组典型工况（粗放回收/达标湿法/绿电直接再生）做合规判定，能耗按产品质量分摊到
  碳酸锂并换算 kgce/t。"
  人工校验修正：①百分比指标显示为 0.850→85.0%；②能耗为上限型指标，判定方向单独处理；
  ③质量分摊系数改由 A_mfa_results.json 的碳酸锂质量占比动态计算。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data_cohort")

with open(os.path.join(DATA, "ABC_parameters.json"), encoding="utf-8") as f:
    P = json.load(f)
with open(os.path.join(DATA, "A_mfa_results.json"), encoding="utf-8") as f:
    M = json.load(f)

POL = P["policy"]
CN, EU = POL["cn"], POL["eu"]
MJ_PER_KGCE = 29.307

# 碳酸锂在产品实物总量中的质量占比（按 MFA 产品清单分摊工艺能耗）
prod_mass = (M["per_tonne"]["li2co3_kg"] + M["per_tonne"]["lfp_powder_kg"]
             + M["per_tonne"]["ni_sulfate_kg"] + M["per_tonne"]["co_sulfate_kg"]
             + M["per_tonne"]["mn_sulfate_kg"]
             + M["per_tonne"]["fepo4_kg"] + M["per_tonne"]["cu_kg"] + M["per_tonne"]["al_kg"])
lce_share = M["per_tonne"]["li2co3_kg"] / prod_mass
lce_per_t_cells = M["per_tonne"]["li2co3_kg"] / 1000.0


def energy_per_t_lce(energy_gj_per_t_cells):
    """全厂综合能耗按产品质量分摊到碳酸锂，换算 kgce/t Li2CO3"""
    total_kgce = energy_gj_per_t_cells * 1000 / MJ_PER_KGCE        # kgce/t 电池
    return total_kgce * lce_share / lce_per_t_cells


CONDITIONS = {
    "W1 粗放回收": {
        "li": 0.850, "nico": 0.900, "powder": 0.950, "cual": 0.950,
        "f": 0.990, "ww": 0.700, "energy_gj": 26.0, "recycled": 0.030,
        "capacity": 20000,
    },
    "W2 达标湿法": {
        "li": 0.920, "nico": 0.980, "powder": 0.980, "cual": 0.980,
        "f": 0.995, "ww": 0.920, "energy_gj": 15.3, "recycled": 0.060,
        "capacity": 20000,
    },
    "W3 绿电直接再生": {
        "li": 0.950, "nico": 0.990, "powder": 0.990, "cual": 0.990,
        "f": 0.998, "ww": 0.950, "energy_gj": 11.5, "recycled": 0.080,
        "capacity": 20000,
    },
}

ASSERTIONS = [
    ("CN-1", "锂回收率 ≥ 90%",                 CN["li_recovery"],    "li",       "%"),
    ("CN-2", "镍钴锰综合回收率 ≥ 98%",         CN["nico_mn_recovery"], "nico",   "%"),
    ("CN-3", "电极粉料回收率 ≥ 98%",           CN["powder_recovery"], "powder",  "%"),
    ("CN-4", "铜铝回收率 ≥ 98%",               CN["cu_al_recovery"],  "cual",    "%"),
    ("CN-5", "氟固化率 ≥ 99.5%",               CN["f_fixation"],      "f",       "%"),
    ("CN-6", "碳酸锂单位能耗 < 2200 kgce/t",   CN["lce_energy_kgce_per_t"], "energy", "kgce/t"),
    ("CN-7", "废水循环利用率 ≥ 90%",           CN["wastewater_recycle"], "ww",   "%"),
    ("EU-1", "欧盟 2031 锂回收率 ≥ 80%",       EU["li_recovery_2031"], "li",      "%"),
    ("EU-2", "欧盟 2031 镍钴回收率 ≥ 95%",     EU["nico_cu_pb_recovery_2031"], "nico", "%"),
    ("EU-3", "欧盟 2031 再生锂含量 ≥ 6%",      EU["recycled_li_2031"], "recycled", "%"),
    ("CN-8", "再生利用产能 ≥ 5000 t/a",        CN["capacity_recycle_t_per_year"], "capacity", "t/a"),
]


def evaluate(cond):
    vals = {
        "li": cond["li"], "nico": cond["nico"], "powder": cond["powder"],
        "cual": cond["cual"], "f": cond["f"], "ww": cond["ww"],
        "energy": energy_per_t_lce(cond["energy_gj"]),
        "recycled": cond["recycled"], "capacity": cond["capacity"],
    }
    results = []
    for code, rule, thr, key, unit in ASSERTIONS:
        v = vals[key]
        ok = v >= thr
        # 规范要求严格低于能耗上限。
        if key == "energy":
            ok = v < thr
        results.append({"code": code, "rule": rule, "value": round(v, 4),
                        "threshold": thr, "unit": unit, "pass": ok})
    return vals, results


print("=" * 96)
print("政策量化引擎 · 三工况断言")
print("=" * 96)
out = {"energy_share_lce": lce_share, "conditions": {}}
for name, cond in CONDITIONS.items():
    vals, res = evaluate(cond)
    n_pass = sum(r["pass"] for r in res)
    label = "PASS" if n_pass == len(res) else "FAIL"
    print(f"\n【{name}】 {label}  ({n_pass}/{len(res)})   "
          f"能耗 {vals['energy']:.0f} kgce/t Li2CO3")
    for r in res:
        flag = "✓" if r["pass"] else "✗"
        if r["unit"] == "%":
            shown = f"{r['value']*100:.1f} %  阈值 {r['threshold']*100:.1f} %"
        else:
            shown = f"{r['value']:.0f} {r['unit']}  阈值 {r['threshold']:g}"
        print(f"  {flag} {r['code']:<5}{r['rule']:<34} 实测 {shown}")
    out["conditions"][name] = {"values": vals, "assertions": res,
                               "pass_count": n_pass, "total": len(res), "verdict": label}

# 合规标签（用于对外披露口径）
best = out["conditions"]["W3 绿电直接再生"]
out["certification_label"] = "CN_SPEC_2024_Compliant | EU_2023_1542_2031_Compliant" \
    if best["verdict"] == "PASS" else "NOT_CERTIFIED"

with open(os.path.join(DATA, "B_policy_results.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"\n合规标签：{out['certification_label']}")
print(f"能耗分摊系数（碳酸锂质量占比）= {lce_share:.4f}")
print("\n已写出 data_cohort/B_policy_results.json")
