# -*- coding: utf-8 -*-
"""任务 1 入口：数据清洗 + ACS 模型，输出 2022 年各流向数值与历史序列"""
import pandas as pd

from config import OUT_DIR
from data_io import build_task1_dataset, load_food_P_supply_2021, \
    load_population_projection
from acs_model import build_acs_2022, calibrate_fert_history, GlobalACSModel


def main():
    print("=" * 64)
    print("任务 1：数据清洗与农田种植子系统（ACS）复现")
    print("=" * 64)
    df, coef, summary, g, crop_s, animal_s = build_task1_dataset()
    print("\n[1] 数据清洗与跨表整合完成")
    print(summary.to_string(index=False))
    print(f"\n全球农产品纯磷产出：1961 年 {g[1961]/1e6:.2f} Mt P → "
          f"2022 年 {g[2022]/1e6:.2f} Mt P")
    print(f"  植物性产品 2022：{crop_s[2022]/1e6:.2f} Mt P；"
          f"动物性产品 2022：{animal_s[2022]/1e6:.2f} Mt P")
    print(f"含磷率字典：{len(coef)} 条产品系数（g P / kg 实物量）")

    fert_hist, alpha = calibrate_fert_history(crop_s)
    print(f"\n[2] 化肥历史序列（幂律标定 α={alpha:.3f}）：")
    for y in [1961, 1980, 2000, 2010, 2022]:
        print(f"    {y}: {fert_hist[y]/1000:.2f} Mt P")

    print("\n[3] 2022 年农田种植系统（ACS）磷流向：")
    model = build_acs_2022()
    rep = model.report()
    print(rep.round(1).to_string(index=False))
    assert model.verify_mass_balance()
    print("\n✅ 通关：ACS 质量守恒断言通过（相对误差 < 1e-4），"
          "2022 年各流向已输出")

    # 导出历史序列
    out = pd.DataFrame({"年份": fert_hist.index,
                        "农产品纯磷产出_MtP": g[fert_hist.index].values / 1e6,
                        "矿物化肥_MtP": fert_hist.values / 1e6})
    out.to_csv(OUT_DIR / "task1_history_series.csv", index=False,
               encoding="utf-8-sig")
    rep.to_csv(OUT_DIR / "task1_acs_2022.csv", index=False,
               encoding="utf-8-sig")
    print(f"\n结果已导出至 {OUT_DIR}")


if __name__ == "__main__":
    main()
