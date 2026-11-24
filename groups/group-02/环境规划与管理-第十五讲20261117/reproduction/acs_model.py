# -*- coding: utf-8 -*-
"""
acs_model.py
============
农田种植系统 (Agricultural Cultivation System, ACS) 磷物质流模型。

1:1 复刻参考源码 `8.Code implementation of P_SFA modeling_cropping system case.py`
中的 `ACSPModel` 类，并补充 `run()` 汇总方法与参数构造器，使其可独立运行、
在控制台输出各流向数值（任务 1 通关节点）。
"""

import numpy as np
import pandas as pd


class ACSPModel:
    """Agricultural Cultivation System (ACS) Phosphorus Flow Model.

    作物级参数通过 `crop_params_df`（每行一种作物）传入，
    系统级参数通过 `system_params_df`（索引为参数名，列 `value` 为数值）传入。
    """

    def __init__(self, crop_params_df, system_params_df):
        self.crop_params = crop_params_df
        self.system_params = system_params_df

    def TP_crop_product(self):
        """作物产品总磷 P = sum(M_i × mi)"""
        return np.sum(self.crop_params['M_i'] * self.crop_params['mi'])

    def crop_uptake_p(self):
        """作物总吸收磷 P_crops_uptake_P = sum(Q_crop_i × κ_ui)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['κ_ui'])

    def crop_harvest_p(self):
        """作物收获磷 P_crops_harvest_P = sum(Q_crop_i × κ_hi)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['κ_hi'])

    def crop_residue_p(self):
        """作物残留磷 P_crops_residue_P = 吸收 - 收获"""
        return self.crop_uptake_p() - self.crop_harvest_p()

    def crop_food_p(self):
        """用于食物的磷 P_crops_food = sum(Q_crop_i × κ_hi × κ_harvest_food_i)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['κ_hi']
                      * self.crop_params['κ_harvest_food_i'])

    def crop_feed_p(self):
        """用于饲料的磷 P_crops_feed = sum(Q_crop_i × κ_hi × κ_harvest_feed_i)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['κ_hi']
                      * self.crop_params['κ_harvest_feed_i'])

    def crop_other_products_p(self):
        """用于其他产品的磷 P_crops_other_products = sum(Q × κ_hi × κ_harvest_other_products_i)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['κ_hi']
                      * self.crop_params['κ_harvest_other_products_i'])

    def crop_waste_p(self):
        """收获物中废弃的磷 P_crops_waste = sum(Q × κ_hi × κ_harvest_waste_i)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['κ_hi']
                      * self.crop_params['κ_harvest_waste_i'])

    def reuse_organic_fertilizer_p(self):
        """残留物回用为有机肥 P_reuse_crops_organic_fertilizer = P_crops_residue_P × β1"""
        beta1 = self.system_params.loc['β1', 'value']
        return self.crop_residue_p() * beta1

    def reuse_crops_feed_p(self):
        """残留物回用为饲料磷 P_reuse_crops_feed = P_crops_harvest_P × β2"""
        beta2 = self.system_params.loc['β2', 'value']
        return self.crop_harvest_p() * beta2

    def drainage_leaching_p(self):
        """排水与淋溶流失 P_ACS→SW = S_cropland × (κ_drainige + κ_leaching)"""
        s_cropland = self.system_params.loc['S_cropland', 'value']
        kappa_drainage = self.system_params.loc['κ_drainige', 'value']
        kappa_leaching = self.system_params.loc['κ_leaching', 'value']
        return s_cropland * kappa_drainage + s_cropland * kappa_leaching

    def atmospheric_deposition_p(self):
        """大气沉降磷 P_AD = S_cropland × s"""
        s_cropland = self.system_params.loc['S_cropland', 'value']
        s = self.system_params.loc['s', 'value']
        return s_cropland * s

    def seed_p(self):
        """种子磷 P_Seed = sum(S_m × K_m)"""
        return np.sum(self.crop_params['S_m'] * self.crop_params['K_m'])

    def straw_p(self):
        """秸秆磷 P_straw = sum(E_i × e_i × f_i)"""
        return np.sum(self.crop_params['E_i'] * self.crop_params['e_i'] * self.crop_params['f_i'])

    def returned_snpk_p(self):
        """秸秆还田磷 P_SNRK = sum(E_i × e_i × g_i × F_i)"""
        return np.sum(self.crop_params['E_i'] * self.crop_params['e_i']
                      * self.crop_params['g_i'] * self.crop_params['F_i'])

    def straw_waste_p(self):
        """秸秆废弃磷 P_SW = P_straw - P_SNRK"""
        return self.straw_p() - self.returned_snpk_p()

    def acs_non_cropland_p(self):
        """农田外磷 P_ACS-Non_cropland = P_SW"""
        return self.straw_waste_p()

    def SD_p(self):
        """其他磷输入 P_SD = (P_Fertilizer + P_human + P_animal) × h"""
        p_fertilizer = self.system_params.loc['P_Fertilizer', 'value']
        p_human = self.system_params.loc['P_human', 'value']
        p_animal = self.system_params.loc['P_animal', 'value']
        h = self.system_params.loc['h', 'value']
        return (p_fertilizer + p_human + p_animal) * h

    def acs_to_lbs_p(self):
        """作为饲料粮输出到养殖系统 P_ACS→LBS = sum(Q_crop_i × m_i × n_i)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['m_i'] * self.crop_params['n_i'])

    # ---- 汇总与守恒 ----
    def run(self):
        """计算并返回全部流向的字典（单位与输入参数一致）。"""
        return {
            "作物产品总磷 TP_crop_product": self.TP_crop_product(),
            "作物吸收磷 crop_uptake": self.crop_uptake_p(),
            "作物收获磷 crop_harvest": self.crop_harvest_p(),
            "作物残留磷 crop_residue": self.crop_residue_p(),
            "食物磷 crop_food": self.crop_food_p(),
            "饲料磷 crop_feed": self.crop_feed_p(),
            "其他产品磷 crop_other": self.crop_other_products_p(),
            "收获废弃磷 crop_waste": self.crop_waste_p(),
            "有机肥回用磷 reuse_organic": self.reuse_organic_fertilizer_p(),
            "残留饲料回用磷 reuse_feed": self.reuse_crops_feed_p(),
            "排水淋溶流失 drainage_leaching": self.drainage_leaching_p(),
            "大气沉降磷 atmospheric_deposition": self.atmospheric_deposition_p(),
            "种子磷 seed": self.seed_p(),
            "秸秆磷 straw": self.straw_p(),
            "秸秆还田磷 returned_straw": self.returned_snpk_p(),
            "秸秆废弃磷 straw_waste": self.straw_waste_p(),
            "农田外磷 acs_non_cropland": self.acs_non_cropland_p(),
            "其他输入磷 SD": self.SD_p(),
            "饲料粮输出磷 acs_to_lbs": self.acs_to_lbs_p(),
        }


def build_sample_params():
    """
    构造示例参数（8 种作物 × 系统级参数），用于演示 ACSPModel 的 2022 年输出。

    数值为无量纲/万吨级的示意标定，旨在演示计算逻辑与守恒关系，
    全局实际核算见 mfa_model.GlobalPModel。
    """
    n = 8
    rng = np.random.default_rng(42)
    crop = pd.DataFrame({
        "M_i": np.linspace(1.0, 8.0, n),          # 作物产量（万吨）
        "mi": np.linspace(2.0, 3.0, n),           # 产品含磷率（kg P/t）
        "Q_crop_i": np.linspace(1.0, 8.0, n),     # 作物生物量（万吨）
        "κ_ui": np.full(n, 0.60),                 # 全株含磷率
        "κ_hi": np.full(n, 0.40),                 # 收获物含磷率
        "κ_harvest_food_i": np.full(n, 0.50),     # 收获物中食物占比
        "κ_harvest_feed_i": np.full(n, 0.30),     # 收获物中饲料占比
        "κ_harvest_other_products_i": np.full(n, 0.10),
        "κ_harvest_waste_i": np.full(n, 0.10),
        "S_m": np.full(n, 0.5),                   # 播种面积
        "K_m": np.full(n, 0.02),                  # 种子含磷
        "E_i": np.linspace(1.0, 8.0, n),          # 秸秆产量
        "e_i": np.full(n, 0.20),                  # 秸秆含磷率
        "f_i": np.full(n, 0.80),                  # 秸秆可利用比例
        "g_i": np.full(n, 0.60),                  # 秸秆还田比例
        "F_i": np.full(n, 0.85),                  # 还田有效系数
        "m_i": np.full(n, 0.30),                  # 饲料粮比例
        "n_i": np.full(n, 0.90),                  # 饲料粮含磷率
    })
    system = pd.DataFrame({
        "value": {
            "β1": 0.40, "β2": 0.10,
            "S_cropland": 1573.3, "κ_drainige": 0.55, "κ_leaching": 0.45,
            "s": 0.60, "P_Fertilizer": 2050.0, "P_human": 60.0, "P_animal": 120.0, "h": 0.02,
        }
    })
    return crop, system


if __name__ == "__main__":
    crop_params, system_params = build_sample_params()
    model = ACSPModel(crop_params, system_params)
    print("=" * 60)
    print("农田种植系统 (ACS) 磷物质流核算 —— 2022")
    print("=" * 60)
    for name, val in model.run().items():
        print(f"  {name:32s} = {val:10.4f}")
    print("=" * 60)
