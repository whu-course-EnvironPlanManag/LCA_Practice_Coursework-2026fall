# -*- coding: utf-8 -*-
"""任务3（前半）：2050 年 BAU 外推与"3R"情景模拟。

BAU：以 UN WPP 2024 中方案 2050 世界人口（96.64 亿）相对 2022 年（80.21 亿）
的比例 1.2048 缩放 2022 年人均磷需求（论文情景设定：人均膳食结构不变）。
3R 参数（任务书）：
- Reduce  S2.2：矿物化肥施用较 BAU 削减 20%；
- Replace S4.3：畜禽粪便堆肥还田利用率 β3 由 0.67 提高至 0.75；
- Recycle S6.2：污水磷回收（鸟粪石）率提高至 60%；
- S5：三者组合。
指标口径：NPR=原生磷矿开采需求（=化肥需求/80%，磷矿→化肥份额按论文 SI）；
CFR=农田矿物化肥投入；Loss=社会系统向环境（水体/土壤遗留增量）流失总量。
"""
import pandas as pd

import config as C
import params_si as P
import data_load as D
from mfa_model import GlobalPModel, PR_TO_FERT_SHARE

POP_RATIO_2050 = None  # 运行时计算


def pop_ratio():
    p2022, p2050 = D.population_projection_2050()
    return p2050 / p2022


def bau_2050():
    """2050 BAU 关键流（吨 P）：需求驱动项按人口比缩放，耕地固定项保持 2022 水平。"""
    m = GlobalPModel(2022)
    r = pop_ratio()
    fert = m.fert * r
    manure = m.manure * r
    excreta = m.rcs_excreta_p() * r
    rcs_waste = m.rcs_waste_p() * r
    water_loss = m.acs.drainage_leaching_p()  # 耕地固定，不随人口缩放
    legacy = m.acs.soil_legacy_delta_p() * r  # 盈余随需求增长
    # 环境流失 = 土壤遗留（最终淋溶入水体）+ 农田排水 + 污水排泄
    loss = legacy + water_loss + rcs_waste
    return {
        "fert": fert, "manure": manure, "excreta": excreta,
        "rcs_waste": rcs_waste, "water_loss": water_loss, "legacy": legacy,
        "NPR": fert / PR_TO_FERT_SHARE, "CFR": fert, "Loss": loss,
    }


def scenario_table():
    """四个 3R 情景 + BAU 的指标表（Mt P 与相对 BAU 变化率）。

    统一逻辑：化肥削减量/有机替代量等比转化为土壤遗留增量削减（超施主要来自化肥），
    污水回收同时削减化肥需求与进入水体的排泄磷。
    """
    b = bau_2050()
    beta3_base = P.LBS["beta3_manure_fertilizer"]

    def metrics(fert, legacy, rcs_waste):
        return {"fert": fert, "NPR": fert / PR_TO_FERT_SHARE, "CFR": fert,
                "legacy": legacy, "rcs_waste": rcs_waste,
                "Loss": legacy + b["water_loss"] + rcs_waste}

    rows = {"BAU_2050": metrics(b["fert"], b["legacy"], b["rcs_waste"])}

    # S2.2 Reduce：化肥减施 20%
    f22 = b["fert"] * 0.80
    rows["S2.2_Reduce_fert-20%"] = metrics(f22, b["legacy"] - (b["fert"] - f22), b["rcs_waste"])

    # S4.3 Replace：粪便堆肥还田率 0.67→0.75，增量还田替代等量化肥
    extra = b["manure"] * (0.75 - beta3_base)
    f43 = b["fert"] - extra
    rows["S4.3_Replace_manure75%"] = metrics(f43, b["legacy"] - extra, b["rcs_waste"])

    # S6.2 Recycle：鸟粪石回收污水磷 60%
    recycle = b["rcs_waste"] * 0.60
    f62 = b["fert"] - recycle
    rows["S6.2_Recycle_struvite60%"] = metrics(f62, b["legacy"] - recycle, b["rcs_waste"] - recycle)

    # S5 组合：三项叠加
    f5 = max(b["fert"] * 0.80 - extra - recycle, 0.0)
    rows["S5_Combined"] = metrics(f5, b["legacy"] - (b["fert"] - f5), b["rcs_waste"] - recycle)

    df = pd.DataFrame(rows).T / C.T_PER_MT
    df["NPR_vs_BAU%"] = (df["NPR"] / df.loc["BAU_2050", "NPR"] - 1) * 100
    df["CFR_vs_BAU%"] = (df["CFR"] / df.loc["BAU_2050", "CFR"] - 1) * 100
    df["Loss_vs_BAU%"] = (df["Loss"] / df.loc["BAU_2050", "Loss"] - 1) * 100
    return df


if __name__ == "__main__":
    print("2050/2022 人口比 = %.4f" % pop_ratio())
    df = scenario_table()
    print("=== 2050 年情景对比（Mt P 与相对 BAU 变化率）===")
    print(df[["fert", "NPR", "CFR", "Loss", "NPR_vs_BAU%", "CFR_vs_BAU%", "Loss_vs_BAU%"]]
          .round(2).to_string())
