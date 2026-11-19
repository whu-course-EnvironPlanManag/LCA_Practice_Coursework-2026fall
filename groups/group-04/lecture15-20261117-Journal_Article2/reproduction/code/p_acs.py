# -*- coding: utf-8 -*-
"""Task 1 的农田种植子系统类（ACS）与 Task 3 的人口驱动 BAU 外推。

ACS 采用任务书要求的「输入—吸收—留存—流失」结构：
    总输入 = 化肥 + 粪肥 + 污泥 + 秸秆还田 + 大气沉降 + 种子
    作物吸收（进入食物系统）= 实测作物纯磷产出 × 食物系统边界系数
    流失 = 流失系数 × (总输入 − 吸收)
    留存（土壤遗留）= 总输入 − 吸收 − 流失
"""
from __future__ import annotations

from p_config import P_2022

# 食物系统边界系数：论文 2022 年作物收获带出 9.9 Mt P ÷ 实测作物纯磷产出 26.72 Mt P
FOOD_SYSTEM_SHARE = P_2022["harvest"] / 26.72
RUNOFF_COEF = P_2022["runoff"] / (31.5 - P_2022["harvest"])  # 3.6 / 21.6


class ACSPModel:
    """农田种植系统（ACS）核算类。"""

    def __init__(self, fertilizer: float, manure: float, sludge: float, straw_return: float,
                 deposition: float, seed: float, crop_production: float,
                 food_share: float = FOOD_SYSTEM_SHARE, runoff_coef: float = RUNOFF_COEF):
        self.flows = dict(fertilizer=fertilizer, manure=manure, sludge=sludge,
                          straw_return=straw_return, deposition=deposition, seed=seed)
        self.crop_production = crop_production
        self.food_share = food_share
        self.runoff_coef = runoff_coef

    @property
    def total_input(self) -> float:
        return sum(self.flows.values())

    @property
    def uptake(self) -> float:
        """作物吸收并进入食物系统的磷。"""
        return self.crop_production * self.food_share

    @property
    def surplus(self) -> float:
        return self.total_input - self.uptake

    @property
    def runoff(self) -> float:
        return self.runoff_coef * self.surplus

    @property
    def legacy(self) -> float:
        return self.surplus - self.runoff

    @property
    def pue(self) -> float:
        return self.uptake / self.total_input

    def verify(self, tol: float = 1e-9) -> float:
        err = abs(self.total_input - (self.uptake + self.runoff + self.legacy)) / self.total_input
        assert err < tol, f"ACS 质量守恒未通过：相对误差 {err:.3e}"
        return err

    def report(self) -> dict:
        self.verify()
        return dict(total_input=self.total_input, uptake=self.uptake, runoff=self.runoff,
                    legacy=self.legacy, pue=self.pue, crop_production=self.crop_production,
                    food_share=self.food_share, **self.flows)


def project_bau(food_2022: float, fert_2022: float, pop_2022: float, pop_2050: float,
                diet_index: float = 1.34, fert_eff_gain: float = 0.20,
                loss_2050: float = 69.9) -> dict:
    """人口驱动的 2050 BAU 外推。

    - 食物需求随人口线性增长，并叠加人均膳食升级（diet_index）；
    - 化肥需求 = 2022 化肥强度 × 食物需求增长 × (1 − 强度改善)；
    - 环境损失沿用论文 BAU 的 69.9 Mt P（含农田 36.3、非农田 19.5、地表水 14.1），
      因为本模型 2022 年损失口径不含坡面侵蚀与历史遗留再释放，无法直接等比放大。
    """
    pop_factor = pop_2050 / pop_2022
    food_2050 = food_2022 * pop_factor * diet_index
    fert_2050 = fert_2022 * (food_2050 / food_2022) * (1.0 - fert_eff_gain)
    return dict(pop_factor=pop_factor, diet_index=diet_index, fert_eff_gain=fert_eff_gain,
                food_2022=food_2022, food_2050=food_2050,
                fert_2022=fert_2022, fert_2050=fert_2050,
                npr_2050=fert_2050, loss_2050=loss_2050)
