# -*- coding: utf-8 -*-
"""生成C成员最终交付的数据表、情景集合与摘要（2026-11-04）。

运行：python build_final_data.py
只依赖Python标准库；输出到 data_cohort/final_20261104/。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
DATA = ROOT / "data_cohort" / "final_20261104"
DATA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE.parent))

import lcor_mac_model as M  # noqa: E402
from policy_engine import evaluate_policy  # noqa: E402


def write_csv(path, rows, fields=None):
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields = fields or list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def policy_case(case_id, metrics, date="2026-11-04", route="smelting",
                metals=("Li", "Ni", "Co", "Mn", "Cu", "Al")):
    return {
        "case_id": case_id, "route": route, "evaluation_date": date,
        "metals_present": list(metals),
        "eu_material_recovery_scope": False, "eu_new_battery_scope": False,
        "produces_lithium_carbonate": True,
        "metrics": {k: v for k, v in metrics.items() if v is not None},
    }


def main():
    m = M.physical()
    base = M.evaluate(m, feed_mode="value", linkage=0.80, recovery_case="base")
    group = M.evaluate(m, feed_mode="group", recovery_case="base")
    compliant = M.evaluate(m, feed_mode="value", linkage=0.80, recovery_case="improved",
                           rd_compliance=True, green_fraction=0.5)
    green100 = M.evaluate(m, feed_mode="value", linkage=0.80, recovery_case="improved",
                          rd_compliance=True, green_fraction=1.0)
    nmc811 = M.evaluate(M.physical(chemistry="NMC811"), feed_mode="value", linkage=0.80,
                        recovery_case="improved", rd_compliance=True)
    nmc811_green = M.evaluate(M.physical(chemistry="NMC811"), feed_mode="value",
                              linkage=0.80, recovery_case="improved", rd_compliance=True,
                              green_fraction=1.0)
    price_low = M.evaluate(m, feed_mode="value", linkage=0.80, recovery_case="improved",
                           rd_compliance=True, li_realization=0.55, metal_realization=0.85)
    price_high = M.evaluate(m, feed_mode="value", linkage=0.80, recovery_case="improved",
                            rd_compliance=True, li_realization=0.85, metal_realization=0.95)

    # 物料去向与环境清单
    flow_rows = M.material_flow_rows(m)
    write_csv(DATA / "material_flow_R1.csv", flow_rows)
    env = M.environment_rows(m)
    write_csv(DATA / "environmental_inventory_R1.csv", env["rows"])
    credit = M.credit_rows(m)
    write_csv(DATA / "product_credits_R1.csv", credit["rows"])
    write_csv(DATA / "mass_balance_checks.csv", M.mass_balance_checks(m))
    write_csv(DATA / "lfp_wet_stage_balance.csv", [M.lfp_wet_stage_balance(m)])

    # 经济参数与费用收入
    param_rows = []
    for key, (value, note) in M.PRICES.items():
        param_rows.append({"parameter_id": key, "value": value, "unit": "CNY/单位",
                           "status": "规划报价/参考价，未取得成交原件",
                           "note": note, "source": "C-ECON-2026"})
    for key, value in M.ECON.items():
        param_rows.append({"parameter_id": key, "value": value, "unit": "CNY或比例",
                           "status": "组内预算/规划假设", "note": "工程与年度预算",
                           "source": "C-ECON-2026"})
    for key, (gwp, water, fid) in M.FACTORS.items():
        param_rows.append({"parameter_id": "EF-" + key, "value": gwp, "unit": "kgCO2e/单位",
                           "status": "文献/数据库参考值", "note": f"水因子{water}",
                           "source": fid})
    for key, value in M.PRIMARY_GWP.items():
        param_rows.append({"parameter_id": "PRIMARY-" + key, "value": value,
                           "unit": "kgCO2e/t", "status": "文献参考值",
                           "note": "原生路线基准", "source": "C-PRIMARY"})
    write_csv(DATA / "economic_parameters_final.csv", param_rows)

    write_csv(DATA / "cost_breakdown_base.csv",
              [{"category": r["category"], "item": r["item"], "quantity": r["quantity"],
                "unit": r["unit"], "unit_price": r["unit_price"],
                "annual_CNY": r["annual_CNY"], "flow_ref": r["flow_ref"],
                "status": r["status"]} for r in base["costs"]["rows"]])
    write_csv(DATA / "revenue_breakdown_base.csv",
              [{"product": r["product"], "quantity": r["quantity"], "unit": r["unit"],
                "unit_price": r["unit_price"], "realization": r["realization"],
                "annual_CNY": r["annual_CNY"], "flow_ref": r["flow_ref"],
                "status": r["status"]} for r in base["revenues"]["rows"]])

    # 关键工况
    key_cases = []
    for cid, r, note in [
        ("K1", group, "组内采购价5,200/8,800，基准R1回收率"),
        ("K2", base, "金属价值80%联动，基准R1回收率"),
        ("K3", compliant, "金属价值80%联动+政策合规改进（Li92%、Cu/Al98%、研发3%）"),
        ("K4", green100, "K3+100%绿电"),
        ("K5", nmc811, "K3但三元按NMC811"),
        ("K6", price_low, "K3但锂实现55%、金属实现85%"),
        ("K7", price_high, "K3但锂实现85%、金属95%"),
        ("K8", nmc811_green, "K3但三元按NMC811且100%绿电"),
    ]:
        key_cases.append({
            "case_id": cid, "note": note,
            "chemistry": r["case"]["chemistry"],
            "green_fraction": r["case"]["green_fraction"],
            "feed_mode": r["case"]["feed_mode"], "linkage": r["case"]["linkage"],
            "recovery_case": r["case"]["recovery_case"],
            "rd_compliance": r["case"]["rd_compliance"],
            "lce_t": r["flows"]["lce_t"], "lcor_CNY_per_t": r["lcor_CNY_per_t"],
            "gross_lcor_CNY_per_t": r["gross_lcor_CNY_per_t"],
            "gwp_kg_per_t_lce": r["gwp_kg_per_t_lce"],
            "water_m3_per_t_lce": r["water_m3_per_t_lce"],
            "mac_CNY_per_tCO2e": r["mac_CNY_per_tCO2e"],
            "feed_price_lfp": r["feed_price_lfp"], "feed_price_nmc": r["feed_price_nmc"],
            "breakeven_feed_ratio": r["breakeven_feed_ratio"],
            "rd_revenue_fraction": r["rd_revenue_fraction"],
            "net_cost_CNY": r["net_cost_CNY"], "revenue_CNY": r["revenue_CNY"],
            "opex_CNY": r["opex_CNY"], "annuity_CNY": r["annuity_CNY"],
            "reuse_margin_CNY": r["reuse"]["margin"],
        })
    write_csv(DATA / "key_cases.csv", key_cases)

    # 983/960组情景 + 政策判定
    scenarios = []
    for i, p in enumerate(M.scenario_grid()):
        mm = M.physical(chemistry=p["chemistry"])
        r = M.evaluate(mm, green_fraction=p["green_fraction"], feed_mode="value",
                       linkage=p["linkage"], li_realization=p["li_realization"],
                       metal_realization=p["metal_realization"],
                       recovery_case=p["recovery_case"],
                       rd_compliance=(p["recovery_case"] == "improved"),
                       energy_case=p["energy_case"])
        pj = policy_case(f"S{i:04d}", r["policy_metrics"])
        pol = evaluate_policy(pj)
        scenarios.append({
            "case_id": f"S{i:04d}", "chemistry": p["chemistry"],
            "green_fraction": p["green_fraction"], "linkage": p["linkage"],
            "recovery_case": p["recovery_case"], "li_realization": p["li_realization"],
            "metal_realization": p["metal_realization"], "energy_case": p["energy_case"],
            "lce_t": r["flows"]["lce_t"],
            "lcor_CNY_per_t": r["lcor_CNY_per_t"],
            "gwp_kg_per_t_lce": r["gwp_kg_per_t_lce"],
            "mac_CNY_per_tCO2e": r["mac_CNY_per_tCO2e"],
            "water_m3_per_t_lce": r["water_m3_per_t_lce"],
            "feed_price_lfp": r["feed_price_lfp"], "feed_price_nmc": r["feed_price_nmc"],
            "li_recovery": r["policy_metrics"]["li_smelting_recovery"],
            "cu_al_recovery": r["policy_metrics"]["cu_recovery"],
            "energy_kgce_per_t": r["policy_metrics"]["lce_energy_kgce_per_t"],
            "rd_fraction": r["rd_revenue_fraction"],
            "policy_status": pol["status"], "policy_fail": pol["fail_count"] if "fail_count" in pol else sum(1 for c in pol["checks"] if c["status"] == "FAIL"),
            "feasible": pol["status"] == "PASS",
        })
    write_csv(DATA / "scenarios_final.csv", scenarios)

    feasible = [s for s in scenarios if s["feasible"]]
    # 推荐前沿只纳入市场可成立的采购价联动区间（≥0.75），避免用低价假设制造"最优"
    recommendable = [s for s in feasible if s["linkage"] >= 0.75]
    front = M.pareto_front([{"case_id": s["case_id"], "gwp": s["gwp_kg_per_t_lce"],
                             "lcor": s["lcor_CNY_per_t"], **s} for s in recommendable])
    knee = M.knee_point(front)
    # 名义推荐集：联动80%、名义实现率70%/85%、R1能耗口径，只让体系/绿电/回收率变化
    nominal = [s for s in feasible if s["linkage"] == 0.80
               and s["li_realization"] == 0.70 and s["metal_realization"] == 0.85
               and s["recovery_case"] == "improved" and s["energy_case"] == "R1"]
    front_nominal = M.pareto_front([{"case_id": s["case_id"], "gwp": s["gwp_kg_per_t_lce"],
                                     "lcor": s["lcor_CNY_per_t"], **s} for s in nominal])
    knee_nominal = M.knee_point(front_nominal)

    # 单因素敏感性（以K3合规工况为基准）
    sens = []

    def add_sens(parameter, value, r):
        sens.append({"parameter": parameter, "value": value,
                     "lcor_CNY_per_t": r["lcor_CNY_per_t"],
                     "gwp_kg_per_t_lce": r["gwp_kg_per_t_lce"],
                     "mac_CNY_per_tCO2e": r["mac_CNY_per_tCO2e"]})

    add_sens("基准", "K3", compliant)
    for v in (0.75, 0.80, 0.85):
        add_sens("采购价联动比例", v, M.evaluate(m, linkage=v, recovery_case="improved",
                                                rd_compliance=True))
    for v in (0.0, 0.5, 1.0):
        add_sens("绿电比例", v, M.evaluate(m, linkage=0.80, green_fraction=v,
                                          recovery_case="improved", rd_compliance=True))
    for v in (0.55, 0.70, 0.85):
        add_sens("锂结算实现率", v, M.evaluate(m, linkage=0.80, li_realization=v,
                                             recovery_case="improved", rd_compliance=True))
    for v in (0.75, 0.85, 0.95):
        add_sens("金属结算实现率", v, M.evaluate(m, linkage=0.80, metal_realization=v,
                                               recovery_case="improved", rd_compliance=True))
    for v in (0.05, 0.07, 0.10):
        add_sens("折现率", v, M.evaluate(m, linkage=0.80, discount_rate=v,
                                        recovery_case="improved", rd_compliance=True))
    for v in ("R1", "conservative"):
        add_sens("能耗口径", v, M.evaluate(m, linkage=0.80, energy_case=v,
                                          recovery_case="improved", rd_compliance=True))
    for v in (100000.0, 133000.0, 180000.0):
        old = M.PRICES["lce"]
        M.PRICES["lce"] = (v, old[1])
        add_sens("碳酸锂价格", v, M.evaluate(m, linkage=0.80, recovery_case="improved",
                                            rd_compliance=True))
        M.PRICES["lce"] = old
    for v in ("saltlake", "spodumene"):
        add_sens("原生基准", v, M.evaluate(m, linkage=0.80, recovery_case="improved",
                                          rd_compliance=True, primary=v))
    write_csv(DATA / "sensitivity_final.csv", sens)

    summary = {
        "date": "2026-11-04",
        "basis": "A R1物料流 + LS23/ANL工艺清单 + B环境因子 + C价格与费用假设",
        "feed_pack_t": M.R1["feed_pack_t"],
        "recycle_pack_t": M.R1["recycle_pack_t"],
        "lce_t": m["lce_t"],
        "li_recovery": m["li_smelting_recovery"],
        "base": {k: base[k] for k in ("lcor_CNY_per_t", "gwp_kg_per_t_lce",
                                      "mac_CNY_per_tCO2e", "revenue_CNY",
                                      "opex_CNY", "annuity_CNY")},
        "key_cases": key_cases,
        "scenario_count": len(scenarios),
        "feasible_count": len(feasible),
        "recommendable_count": len(recommendable),
        "pareto_count": len(front),
        "nominal_count": len(front_nominal),
        "knee_nominal": knee_nominal,
        "pareto_nominal": front_nominal,
        "knee": knee,
        "pareto": front,
        "environment_total_gwp_t": env["gwp_kg"] / 1000.0,
        "credit_total_gwp_t": credit["avoided_kg"] / 1000.0,
        "notes": [
            "情景价格为规划参考价，不是已核实成交价；补贴、碳信用和溢价均为0。",
            "政策可行仅指已编码定量项通过；缺失项保持UNKNOWN，不构成法律合规认证。",
        ],
    }
    (DATA / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print("scenarios", len(scenarios), "feasible", len(feasible), "pareto", len(front))
    print("key cases", [(c["case_id"], round(c["lcor_CNY_per_t"]),
                         round(c["mac_CNY_per_tCO2e"] or 0)) for c in key_cases])
    if knee:
        print("knee", knee["case_id"], knee["lcor_CNY_per_t"], knee["gwp_kg_per_t_lce"])


if __name__ == "__main__":
    main()
