# -*- coding: utf-8 -*-
"""
成员 B · 任务二：退役动力电池锂资源回收工艺 LCA 模型
=========================================================
功能单位：1 t 电池级碳酸锂 (Li2CO3) 当量
系统边界：摇篮到大门 (Cradle-to-Gate)
    收集运输 -> 放电拆解 -> 机械破碎分选 -> 精炼再生(火法/湿法/直接再生) -> 污染治理
多产品分配：主产品电池级 Li2CO3 承担 100% 负荷；镍钴锰盐 / 磷酸铁副产按
    avoided burden（系统性替代原生开采）逻辑折减，占位待成员 A 物料衡算校准。

组内接口契约：
  - 成员 A（MFA）提供 activity_vector（每功能单位各工序活动量），
    键名须与本文件 `DEFAULT_ACTIVITIES` 对齐；
  - 成员 C（经济/政策）提供 LCOR 等经济指标，本模型只计算环境维度
    （GWP100 与水耗），经济维度由 scenario_analysis / optimization 经
    c_interface 调用成员 C 真实引擎（evaluate_policy / evaluate_tea）。

数据来源：data_cohort/environmental_factors.csv；原生基准引自 Peiseler et al. 2024
    (文献1 LCE 供应曲线：硬岩锂辉石约为盐湖卤水中位值 3 倍) 与公开 LCA 文献量级。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import pandas as pd

# 文件相对定位
_BASE = os.path.dirname(os.path.abspath(__file__))
FACTORS_CSV = os.path.join(_BASE, "..", "data_cohort", "environmental_factors.csv")

# ---------------------------------------------------------------------------
# 电力（绿电/电网）因子不再内嵌硬编码，统一从 environmental_factors.csv 读取。
# 修正确保区域电网水因子随电网碳强度档位同步变化（不再固定为 2 L/kWh）。
# ---------------------------------------------------------------------------

# 原生矿产基准（1 t 电池级 Li2CO3）：(GWP kgCO2e, 水 L)；引自文献1 + 公开 LCA 量级
VIRGIN_BENCHMARKS = {
    "salt_lake_brine": {"label": "盐湖卤水提锂基准", "gwp": 4000.0, "water": 470000.0},
    "hard_rock_spodumene": {"label": "硬岩锂辉石提锂基准", "gwp": 9000.0, "water": 170000.0},
}

# 占位工序活动量（每 1 t 电池级 Li2CO3），待成员 A 的工序级 MFA 交付后替换
DEFAULT_ACTIVITIES: dict[str, float] = {
    "electricity_kwh": 8000.0,                  # 各工序总电耗（kWh，按绿电比例拆分）
    "natural_gas": 12000.0,                     # 还原焙烧 + 蒸发结晶热源（MJ）
    "sulfuric_acid_H2SO4": 2500.0,              # 浸出剂（kg）
    "hydrogen_peroxide_H2O2": 400.0,            # 还原剂（kg）
    "sodium_hydroxide_NaOH": 1500.0,            # 中和 / 共沉淀剂（kg）
    "sodium_carbonate_Na2CO3": 1600.0,          # 沉锂剂（kg）
    "lime_CaO": 800.0,                          # 除氟 / 中和（kg）
    "diesel_truck": 2000.0,                     # 收集与危废运输（t·km）
    "wastewater_treatment": 30.0,               # 常规工艺废水（m3）
    "fluoride_wastewater_advanced": 10.0,       # 含氟高盐废水深度处理（m3）
    "hazardous_residue_disposal": 1.5,          # 浸出渣固化填埋（t）
}

# electricity_kwh 之外的键需与 CSV 的 factor_name 精确对应，此处做占位映射说明
_ACTIVITY_TO_FACTOR = {
    "natural_gas": "natural_gas",
    "process_steam": "process_steam",
    "sulfuric_acid_H2SO4": "sulfuric_acid_H2SO4",
    "hydrogen_peroxide_H2O2": "hydrogen_peroxide_H2O2",
    "sodium_hydroxide_NaOH": "sodium_hydroxide_NaOH",
    "sodium_carbonate_Na2CO3": "sodium_carbonate_Na2CO3",
    "lime_CaO": "lime_CaO",
    "diesel_truck": "diesel_truck",
    "wastewater_treatment": "wastewater_treatment",
    "fluoride_wastewater_advanced": "fluoride_wastewater_advanced",
    "hazardous_residue_disposal": "hazardous_residue_disposal",
}


@dataclass
class LCAResult:
    """一次 LCA 核算结果。

    unmapped_activities / missing_activities 仅当传入的 activities 含未知键或缺失
    已映射键（含值为 None）时非空，供调用方报告——缺失与明确为零必须区分，不静默补零。
    """
    gwp_kgco2e: float
    water_l: float
    breakdown: pd.DataFrame = field(default_factory=pd.DataFrame)
    unmapped_activities: list = field(default_factory=list)
    missing_activities: list = field(default_factory=list)


def load_factors(path: str = FACTORS_CSV) -> pd.DataFrame:
    """读取环境因子表。"""
    return pd.read_csv(path, encoding="utf-8", comment="#")


def _factor_map(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """factor_name -> {'gwp':..., 'water':...}"""
    m = {}
    for _, row in df.iterrows():
        m[row["factor_name"]] = {
            "gwp": float(row["gwp_kgco2e_per_unit"]),
            "water": float(row["water_l_per_unit"]),
        }
    return m


class LCAModel:
    """退役锂资源回收工艺 LCA 核算器（环境维度）。"""

    def __init__(self, factors_csv: str = FACTORS_CSV):
        self.factor_df = load_factors(factors_csv)
        self.factors = _factor_map(self.factor_df)
        self._grid_by_gwp = {
            float(row["gwp_kgco2e_per_unit"]): row["factor_name"]
            for _, row in self.factor_df.iterrows()
            if str(row["factor_name"]).startswith("grid_")
        }

    def _resolve_grid(self, grid_ef: float | None) -> dict[str, float]:
        """按电网碳强度匹配CSV中的区域电网因子；未匹配时回退全国基准。"""
        if grid_ef is None:
            if "grid_china_base" in self.factors:
                return self.factors["grid_china_base"]
            raise KeyError("环境因子表中缺少因子 grid_china_base")
        ef = float(grid_ef)
        name = self._grid_by_gwp.get(ef)
        if name is None:
            for gwp, n in self._grid_by_gwp.items():
                if abs(gwp - ef) < 1e-9:
                    name = n
                    break
        if name is not None:
            return self.factors[name]
        raise KeyError(f"环境因子表中缺少与 {ef} 匹配的区域电网因子")

    def compute(
        self,
        activities: dict[str, float] | None = None,
        green_ratio: float = 0.8,
        grid_ef: float | None = None,
        grid_water: float | None = None,
    ) -> LCAResult:
        """由工序活动量计算 GWP100 与水耗。

        参数
        ----
        activities : 工序活动量向量（成员 A 提供）；缺省使用占位 DEFAULT_ACTIVITIES。
        green_ratio : 园区绿电消纳比例 [0,1]，其余用电来自区域电网。
        grid_ef / grid_water : 区域电网碳/水因子（缺省取 grid_china_base）。
        """
        provided = activities is not None
        acts = dict(DEFAULT_ACTIVITIES if activities is None else activities)
        known = {"electricity_kwh"} | set(_ACTIVITY_TO_FACTOR.keys())
        # 显式区分「缺失/未映射」与「明确为零」：仅当传入不完整向量时记录，正常占位向量不缺项。
        unmapped = [k for k in acts if k not in known] if provided else []
        missing = [k for k in known if k not in acts or acts.get(k) is None] if provided else []

        green = self.factors.get("green_power_mix")
        if green is None:
            raise KeyError("环境因子表中缺少因子 green_power_mix")
        grid = self._resolve_grid(grid_ef)
        ef = grid["gwp"]
        wf = grid["water"] if grid_water is None else float(grid_water)

        rows = []
        elec = acts.get("electricity_kwh", 0.0) or 0.0

        # 电力：按绿电比例拆分为绿电 + 网电，碳/水因子均取自CSV
        g_elec = elec * green_ratio * green["gwp"]
        n_elec = elec * (1 - green_ratio) * ef
        g_elec_w = elec * green_ratio * green["water"]
        n_elec_w = elec * (1 - green_ratio) * wf
        rows.append(["电力-绿电", elec * green_ratio, g_elec, g_elec_w])
        rows.append(["电力-网电", elec * (1 - green_ratio), n_elec, n_elec_w])

        # 其余活动量：直接乘以对应环境因子；缺失/None 键已记入 missing，此处仅按 0 参与求和
        for act_key, fac_key in _ACTIVITY_TO_FACTOR.items():
            amount = acts.get(act_key, 0.0)
            if amount is None:
                amount = 0.0
            if fac_key not in self.factors:
                raise KeyError(f"环境因子表中缺少因子 {fac_key}")
            f = self.factors[fac_key]
            rows.append([fac_key, amount, amount * f["gwp"], amount * f["water"]])

        breakdown = pd.DataFrame(rows, columns=["item", "activity", "gwp_kgco2e", "water_l"])
        total_gwp = breakdown["gwp_kgco2e"].sum()
        total_water = breakdown["water_l"].sum()
        return LCAResult(gwp_kgco2e=total_gwp, water_l=total_water, breakdown=breakdown,
                         unmapped_activities=unmapped, missing_activities=missing)

    def compare_to_virgin(self, gwp_kgco2e: float, water_l: float) -> pd.DataFrame:
        """相对两类原生矿产基准的减排量 / 降幅。"""
        recs = []
        for key, b in VIRGIN_BENCHMARKS.items():
            dg = b["gwp"] - gwp_kgco2e
            dw = b["water"] - water_l
            recs.append({
                "benchmark": b["label"],
                "virgin_gwp_kgco2e": b["gwp"],
                "virgin_water_l": b["water"],
                "delta_gwp_kgco2e": dg,
                "delta_gwp_pct": dg / b["gwp"] * 100.0,
                "delta_water_l": dw,
                "delta_water_pct": dw / b["water"] * 100.0,
            })
        return pd.DataFrame(recs)


def run_self_check(green_ratio: float = 0.8) -> None:
    """终端自检：打印拆解与基准对比，验证模型可运行。"""
    model = LCAModel()
    res = model.compute(green_ratio=green_ratio)
    print(f"[LCA 自检] 功能单位 1 t 电池级 Li2CO3，绿电比例 {green_ratio:.0%}")
    print(f"  净 GWP100 = {res.gwp_kgco2e:,.1f} kgCO2e/t")
    print(f"  净水耗   = {res.water_l:,.1f} L/t  ({res.water_l/1000:.1f} m3/t)")
    print("\n  分项贡献（kgCO2e）：")
    for _, row in res.breakdown.sort_values("gwp_kgco2e", ascending=False).iterrows():
        print(f"    {row['item']:<28s} {row['gwp_kgco2e']:>10.1f}")
    print("\n  相对原生基准：")
    print(model.compare_to_virgin(res.gwp_kgco2e, res.water_l).to_string(index=False))


if __name__ == "__main__":
    run_self_check()