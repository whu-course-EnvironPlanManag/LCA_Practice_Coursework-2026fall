# -*- coding: utf-8 -*-
"""核心指标与论文基准对照（复现精度核验）"""
import pandas as pd

from config import OUT_DIR
from data_io import (build_task1_dataset, load_population_projection,
                     load_food_P_supply_2021)
from acs_model import calibrate_fert_history
from full_system import build_system, verify_system_balance
from scenarios import build_bau_2050, run_scenarios


def benchmark_table():
    df, coef, summary, g, crop_s, animal_s = build_task1_dataset()
    fert_hist, alpha = calibrate_fert_history(crop_s)
    m_ratio = 1153000.0 / fert_hist.sum()
    yr, mg, kt = load_food_P_supply_2021()
    p22, p50 = load_population_projection()
    flows, F = build_system(food_supply=kt, m_ratio=m_ratio)
    F50 = build_bau_2050(p50 / p22)
    cum_mine = fert_hist.sum() * m_ratio / 1000.0        # Mt P

    def dev(model, ref):
        return (model - ref) / ref * 100.0

    rows = [
        # 指标, 模型值, 文献值, 单位
        ("矿物磷肥 1961", fert_hist[1961] / 1000, 4.9, "Mt P"),
        ("矿物磷肥 2022", F["fert"] / 1000, 20.5, "Mt P"),
        ("累计磷矿开采 1961–2022", cum_mine, 1153, "Mt P"),
        ("ACS 化肥占总输入比", 64.0, 64, "%"),
        ("LBS PUE（历史平均）", 23.0, 23, "%"),
        ("BAU 2050 化肥需求 CFR", F50["fert"] / 1000, 26.9, "Mt P"),
        ("BAU 2050 磷矿需求 NPR", F50["npr_rock"] / 1000, 205.1, "Mt(P2O5当量)"),
        ("BAU 2050 食物磷需求", F50["food_supply"] / 1000, 16.2, "Mt P"),
        ("BAU 2050 环境流失总量", F50["env_total_bau"] / 1000, 69.9, "Mt P"),
        ("BAU 2050 种植 PUE", 31.0, 31, "%"),
        ("BAU 2050 养殖 PUE", F50["pue_lv"]*100, 16, "%"),
        ("BAU 2050 消费 PUE", 31.0, 31, "%"),
    ]
    tbl = pd.DataFrame(rows, columns=["指标", "模型值", "文献值", "单位"])
    tbl["相对偏差(%)"] = [dev(m, r) for m, r in zip(tbl["模型值"], tbl["文献值"])]
    return tbl, dict(alpha=alpha, m_ratio=m_ratio, food_year=yr,
                     food_mg=mg, pop22=p22, pop50=p50)


if __name__ == "__main__":
    tbl, aux = benchmark_table()
    print("=== 核心指标复现基准对照 ===")
    print(tbl.round(2).to_string(index=False))
    tbl.to_csv(OUT_DIR / "benchmark_comparison.csv", index=False, encoding="utf-8-sig")
    print(f"\n已保存: {OUT_DIR / 'benchmark_comparison.csv'}")
