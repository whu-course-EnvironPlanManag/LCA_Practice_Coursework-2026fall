# -*- coding: utf-8 -*-
"""任务 2 入口：全系统闭环守恒自检 + 2022 年交互式桑基图"""
import pandas as pd

from config import OUT_DIR
from data_io import build_task1_dataset, load_food_P_supply_2021
from acs_model import calibrate_fert_history
from full_system import build_system, verify_system_balance, make_sankey, \
    subsystem_balance_table, NODES


def main():
    print("=" * 64)
    print("任务 2：全系统闭环守恒自检与桑基图生成")
    print("=" * 64)
    df, coef, summary, g, crop_s, animal_s = build_task1_dataset()
    fert_hist, alpha = calibrate_fert_history(crop_s)
    m_ratio = 1153000.0 / fert_hist.sum()
    yr, mg, kt = load_food_P_supply_2021()

    flows, F = build_system(food_supply=kt, m_ratio=m_ratio)
    detail = verify_system_balance(flows)
    print("\n[1] 全系统质量守恒自检：")
    for k in ["边界输入", "边界输出", "存量变化合计", "相对误差"]:
        print(f"    {k}: {detail[k]:,.2f} kt P" if k != "相对误差"
              else f"    {k}: {detail[k]:.2e}")
    print("    库存变化明细：", {n: round(v, 1)
          for n, v in detail["stock_detail"].items()})
    assert detail["相对误差"] < 1e-4
    print("✅ 通关：全系统守恒断言通过（相对误差 < 1e-4）")

    print("\n[2] 子系统输入/输出核算（kt P）：")
    tbl = subsystem_balance_table(flows)
    print(tbl.round(0).to_string(index=False))

    html = OUT_DIR / "sankey_2022.html"
    make_sankey(flows=flows, outfile=html)
    print(f"\n✅ 通关：交互式桑基图已导出 → {html}")

    pd.DataFrame(flows, columns=["源节点", "目标节点", "通量_ktP", "流名称"]) \
        .to_csv(OUT_DIR / "task2_flows_2022.csv", index=False,
                encoding="utf-8-sig")
    print(f"流清单已导出 → {OUT_DIR / 'task2_flows_2022.csv'}")


if __name__ == "__main__":
    main()
