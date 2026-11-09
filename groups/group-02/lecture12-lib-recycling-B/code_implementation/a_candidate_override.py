# -*- coding: utf-8 -*-
"""
A 候选参数 → B 功能单位（1 t Li₂CO₃）的试用换算层（PROVISIONAL / 默认不启用）
============================================================================
背景：成员 A 的 candidate_process_parameters 全部 active=false、usable_for_calculation=false，
      按 A 引导规则「选用时另写本组决策/参数覆盖文件」——本模块即该覆盖文件的代码载体，
      集中记录：采用了哪些候选值、出处、换算口径、假设与"试用"结论。

只做换算与自检，不改数值计算主流程；是否接入由外部参数 USE_A_CANDIDATES 控制（默认关）。

关键结论（运行 main() 可见）：
  * 能量侧 ND_SEC(1729.26 kgce/t Li₂CO₃) 直接落在 B 的功能单位上，可安全作为总能量锚点。
  * 试剂侧 LS_* 系数为「商品吨 × 浓度 = 有效吨」：硫酸98%、液碱32%、氧化钙92%。NaOH 商品量
    ~8.9 t（32%液碱）折纯后 ~2.856 t NaOH/t Li₂CO₃，量级合理，不再视为“物理不合理”。
    但 LS 路线属独立条件路线（JR 产粉与 LS 入料同口径未证 M03/M06/M07、多产品分配 M10 未定），
    仍不能直接拼进全厂正式清单，待 A 与 B/C 厘清口径后再接入。
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 一、采用的候选值（来自 A 的 candidate_process_parameters，逐条标注出处/口径）
# ---------------------------------------------------------------------------
# 综合能耗：直接落在 B 功能单位（1 t Li₂CO₃ 产品）上，无需进料换算
ND_SEC_KGCE_PER_T_LI2CO3 = 1729.26   # ND_SEC, numerator=kgce, denominator=t_Li2CO3_product
# 中低压蒸汽焓（占位，待 A M08 核压力/温度后精确化）
STEAM_ENTHALPY_MJ_PER_T = 2500.0      # MJ / t 蒸汽（中低压饱和蒸汽量级）

# 黑粉锂品位（A 的 JR23_LFP_POWDER 参考组分，reference_assay_not_active）
LFP_POWDER_LI_MASS = 0.03425          # Li 质量分数，SRC039 表3.4-7
# Li₂CO₃ 中 Li 元素质量分数（摩尔量：2×6.94 / 73.89）
LI_IN_LI2CO3 = 0.1879

# 朗赛湿法（LS_*）试剂/蒸汽系数，单位 t商业品 / t_粉料进料（SRC040 表3.5-1, p71–72）
LS_ACID = 0.5630527      # 98%硫酸       (specification_fraction=0.98)
LS_NAOH = 1.4639371      # 32%液碱       (specification_fraction=0.32)
LS_CAO = 0.0294          # 92%氧化钙     (specification_fraction=0.92)
LS_STEAM = 1.1747755     # 蒸汽 t蒸汽/t粉料
# LS_FE=0.01314(99%铁粉) / LS_PACID=0.098239(磷酸) / LS_CO2=0.111 / LS_O2=0.012
# 上述四项不在 B 现有活动量键集合内，本次仅记录、不接入。


def li_recovery(pm: float) -> float:
    """锂回收率—直接再生占比映射（B 侧占位线性式，待 A 实测收率校准）。"""
    return 0.90 + 0.09 * pm


def powder_per_t_li2co3(pm: float) -> float:
    """每 1 t Li₂CO₃ 需要的黑粉进料量 X（t 粉料 / t Li₂CO₃）。"""
    return LI_IN_LI2CO3 / (LFP_POWDER_LI_MASS * li_recovery(pm))


def energy_from_a(pm: float) -> dict:
    """由 ND_SEC 综合能耗 + LS_STEAM 蒸汽拆出的电耗/热耗（t Li₂CO₃ 口径）。

    口径说明：以 ND_SEC(综合能耗)为总能量上限；蒸汽按 LS_STEAM×X 折算；
    电耗 = 总能量 − 蒸汽（综合能耗按 GB/T 2589 含义已含蒸汽）。蒸汽焓为占位值。
    """
    X = powder_per_t_li2co3(pm)
    total_mj = ND_SEC_KGCE_PER_T_LI2CO3 * 29.3076          # kgce → MJ
    steam_mj = LS_STEAM * X * STEAM_ENTHALPY_MJ_PER_T       # t蒸汽→MJ
    elec_kwh = max(0.0, (total_mj - steam_mj) / 3.6)
    return {"electricity_kwh": elec_kwh, "heat_mj": steam_mj, "powder_feed_t": X}


# 商品浓度（specification_fraction）：硫酸98%、液碱32%、氧化钙92%
H2SO4_SPEC = 0.98
NAOH_SPEC = 0.32
CAO_SPEC = 0.92


def reagents_from_a(pm: float) -> dict:
    """LS_* 试剂系数 → 1 t Li₂CO₃ 口径。

    显式区分「商品吨」与「有效成分吨」（商品吨×浓度=有效吨），避免把 32% 液碱
    商品量误当纯 NaOH 而误判物理不合理。返回的 *_kg 均为有效成分质量，供 LCA
    因子（纯 NaOH / 纯 H2SO4 / 纯 CaO 因子）使用；同时保留液碱商品量备核。
    """
    X = powder_per_t_li2co3(pm)
    h2so4_commercial_kg = LS_ACID * X * 1000.0          # 98% 硫酸商品量
    naoh_commercial_kg = LS_NAOH * X * 1000.0           # 32% 液碱商品量
    cao_commercial_kg = LS_CAO * X * 1000.0             # 92% 氧化钙商品量
    h2so4_pure = h2so4_commercial_kg * H2SO4_SPEC
    naoh_pure = naoh_commercial_kg * NAOH_SPEC          # 纯 NaOH 有效量
    cao_pure = cao_commercial_kg * CAO_SPEC
    # 判据按有效成分：NaOH 纯量 ~2.856 t、H2SO4 纯量 ~3.4 t，均属合理量级
    plausible = naoh_pure < 4000.0 and h2so4_pure < 6000.0
    return {
        "sulfuric_acid_H2SO4_kg": h2so4_pure,
        "sodium_hydroxide_NaOH_kg": naoh_pure,
        "lime_CaO_kg": cao_pure,
        "sodium_hydroxide_32pct_commercial_kg": naoh_commercial_kg,
        "implausible_flag": not plausible,
    }


if __name__ == "__main__":
    print("=" * 78)
    print("A 候选参数 → B (1 t Li2CO3) 试用换算 · 诊断输出")
    print("=" * 78)
    print(f"{'pm':>5} {'粉料X(t)':>9} {'电耗(kWh)':>10} {'蒸汽(MJ)':>10} "
          f"{'H2SO4(kg)':>10} {'NaOH纯(kg)':>10} {'液碱32%商品(kg)':>14} {'CaO(kg)':>8}  自检")
    for pm in (0.0, 0.5, 1.0):
        e = energy_from_a(pm)
        r = reagents_from_a(pm)
        flag = "含不合理项" if r["implausible_flag"] else "OK"
        print(f"{pm:>5.1f} {e['powder_feed_t']:>9.3f} {e['electricity_kwh']:>10.1f} "
              f"{e['heat_mj']:>10.1f} {r['sulfuric_acid_H2SO4_kg']:>10.1f} "
              f"{r['sodium_hydroxide_NaOH_kg']:>10.1f} "
              f"{r['sodium_hydroxide_32pct_commercial_kg']:>14.1f} "
              f"{r['lime_CaO_kg']:>8.1f}  {flag}")
    print("\n结论：能量侧(电/蒸汽)可直接采用；试剂侧按「商品吨×浓度」折算为有效成分后量级合理，")
    print("      但 LS 路线进料/分配口径未核（M03/M06/M07/M10），仍不能直接拼进全厂正式清单。")