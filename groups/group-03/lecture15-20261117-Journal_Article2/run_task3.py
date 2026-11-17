# -*- coding: utf-8 -*-
"""任务 3 入口：2050 BAU/3R 情景模拟 + 交叉敏感性回归 + 情景对比图"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config import OUT_DIR
from data_io import load_population_projection
from scenarios import (build_bau_2050, run_scenarios, simulate_3r,
                       monte_carlo_scenario, cross_sensitivity_analysis,
                       SCENARIO_DEFS)


def scenario_figure(F, tbl):
    """图 4A 风格：各情景相对 2050 BAU 的关键指标变化（%）"""
    scen = tbl["情景"].tolist()[1:]
    metrics = [("CFR削减", "CFR 化肥需求"), ("NPR削减", "NPR 磷矿需求"),
               ("流失削减", "环境流失总量")]
    fig = go.Figure()
    for col, label in metrics:
        fig.add_bar(name=label, x=scen,
                    y=[tbl.loc[tbl["情景"] == s, col].iloc[0] * 100 for s in scen])
    fig.update_layout(barmode="group", title="2050 年情景杠杆效应（相对 BAU，%）",
                      yaxis_title="变化 (%)", width=980, height=520,
                      font_size=13)
    out = OUT_DIR / "scenario_levers.html"
    fig.write_html(out, include_plotlyjs="cdn")
    return out


def main():
    print("=" * 64)
    print("任务 3：2050 年 3R 情景模拟与交叉敏感性回归")
    print("=" * 64)
    p22, p50 = load_population_projection()
    pop_ratio = p50 / p22
    print(f"\n[0] 人口外推（UN WPP Medium）：2022 {p22/1e9:.2f} → "
          f"2050 {p50/1e9:.2f} 十亿（×{pop_ratio:.3f}）")
    F = build_bau_2050(pop_ratio)
    print(f"    BAU 2050 校准：CFR={F['fert']/1000:.1f} Mt P, "
          f"NPR={F['npr_rock']/1000:.1f} Mt(P2O5当量), "
          f"环境流失={F['env_total_bau']/1000:.1f} Mt P, "
          f"粪污利用率 μ0={F['mu0']:.3f}")

    F, tbl = run_scenarios(pop_ratio)
    print("\n[1] 情景对比（相对 2050 BAU）：")
    show = tbl.copy()
    for c in ["CFR削减", "NPR削减", "流失削减"]:
        show[c] = (show[c] * 100).round(1).astype(str) + "%"
    print(show.round(0).to_string(index=False))
    fig = scenario_figure(F, tbl)
    print(f"    情景对比图已导出 → {fig}")
    tbl.to_csv(OUT_DIR / "task3_scenarios.csv", index=False,
               encoding="utf-8-sig")

    print("\n[2] 交叉敏感性回归（均值中心化交互项 + 标准化, n=600）：")
    data = monte_carlo_scenario(F)
    rows = []
    for v1, v2 in [("S22", "S43"), ("S22", "S45"), ("S43", "S45")]:
        ctrl = tuple(v for v in ("S22", "S43", "S45") if v not in (v1, v2))
        res = cross_sensitivity_analysis(data, v1, v2, "削减量", controls=ctrl)
        rows.append(res)
        print(f"    {v1} × {v2}: R²={res['r2']:.3f}, "
              f"β_inter={res['beta_inter']:.1f} (标准化 {res['beta_inter_std']:.3f}), "
              f"p={res['p_inter']:.2e} → {res['effect']}")
    reg = pd.DataFrame(rows)
    reg.to_csv(OUT_DIR / "task3_regression.csv", index=False,
               encoding="utf-8-sig")
    key = reg.iloc[0]
    assert key["r2"] > 0.85 and key["p_inter"] < 0.05 and key["beta_inter_std"] > 0
    print("\n✅ 通关：R²>0.85；S2.2×S4.3 交互项 p<0.05 且标准化系数>0（协同增强），"
          "2050 情景对比数据与回归统计表均已输出")


if __name__ == "__main__":
    main()
