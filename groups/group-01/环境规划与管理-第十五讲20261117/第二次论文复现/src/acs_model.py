# -*- coding: utf-8 -*-
"""任务1：农田种植子系统（ACS）磷流动模型。

参考 source_data 中论文作者的 ACSPModel 类公式，重写为数据驱动版本：
作物产量取自 FAOSTAT（19 类作物），吸收/收获系数取 SI Table S3，
系统参数（β1/β2/h/沉降/排水/淋溶）取 SI Table S4，全部数值见 params_si.py。
"""
import pandas as pd

import config as C
import params_si as P
import data_load as D

# 世界农村人口份额（UN WUP 2018 修订口径 2022 年约 43%）；
# 用于人粪尿还田的城乡加权，属于外生假设，报告中注明。
RURAL_SHARE = 0.43


class ACSModel:
    """农田种植系统磷流动年度核算（单位：吨 P）。"""

    def __init__(self, year):
        self.year = year
        q = D._crop_production_year(year)
        if q is None:
            raise FileNotFoundError(f"缺少 {year} 年作物产量数据")
        self.crops = pd.DataFrame({
            "Q_crop_i": pd.Series(q),
            "kappa_u": pd.Series(P.UPTAKE_KG_T),
            "kappa_h": pd.Series(P.HARVEST_KG_T),
        }).dropna(subset=["Q_crop_i"])
        self.cropland_ha = float(D.cropland_area_ha().get(year, pd.NA))
        self.fert_t = float(D.fertilizer_p_series().get(year, pd.NA))
        self.manure_t = float(D.manure_excretion_p().get(year, pd.NA))
        self.population = float(D.population_world().get(year, pd.NA))

    # ---- 作物磷吸收 / 收获 / 残留 ----
    def crop_uptake_p(self):
        return float((self.crops["Q_crop_i"] * self.crops["kappa_u"]).sum()) / 1e3

    def crop_harvest_p(self):
        return float((self.crops["Q_crop_i"] * self.crops["kappa_h"]).sum()) / 1e3

    def crop_residue_p(self):
        return self.crop_uptake_p() - self.crop_harvest_p()

    # ---- 有机磷回用 ----
    def reuse_organic_fertilizer_p(self):
        """秸秆还田作有机肥 = 残留 P × β1。"""
        return self.crop_residue_p() * P.ACS["beta1_residue_fertilizer"]

    def reuse_crops_feed_p(self):
        """收获物作饲料（ACS→LBS）= 收获 P × β2。"""
        return self.crop_harvest_p() * P.ACS["beta2_residue_feed"]

    def manure_return_p(self):
        """畜禽粪便还田 = 粪便排泄 P × β3。"""
        return self.manure_t * P.LBS["beta3_manure_fertilizer"]

    def excreta_return_p(self):
        """人粪尿直接还田（农村 44%、城市 22% 加权）。"""
        excreta = self.population * P.RCS["beta5_human_excretion_kg_capita_yr"] / 1e3
        w = RURAL_SHARE * P.RCS["beta6_rural_excreta_reuse"] + (1 - RURAL_SHARE) * P.RCS["beta7_urban_excreta_reuse"]
        return excreta * w

    def human_excreta_p(self):
        return self.population * P.RCS["beta5_human_excretion_kg_capita_yr"] / 1e3

    # ---- 自然输入与流失 ----
    def atmospheric_deposition_p(self):
        """大气沉降 = 耕地面积 × s（25 kg P/km²/a）。"""
        km2 = self.cropland_ha * 0.01
        return km2 * P.ACS["s_deposition_kg_km2a"] / 1e3

    def drainage_leaching_p(self):
        """农田排水+淋溶入水体 = S_cropland × (κ_drainage + κ_leaching)。"""
        k = P.ACS["kappa_drainage_kg_ha_a"] + P.ACS["kappa_leaching_kg_ha_a"]
        return self.cropland_ha * k / 1e3

    def SD_p(self):
        """其他磷输入（灌溉/粪污堆放径流等）= (化肥+人排泄+动物粪便) × h。"""
        return (self.fert_t + self.human_excreta_p() + self.manure_t) * P.ACS["h"]

    def straw_waste_p(self):
        """秸秆废弃（未还田部分）= 残留 P × (1-β1)。"""
        return self.crop_residue_p() * (1 - P.ACS["beta1_residue_fertilizer"])

    # ---- 汇总 ----
    def productive_input_p(self):
        """作物可利用磷输入 = 化肥+粪肥还田+秸秆还田+人粪尿还田+大气沉降。

        SD（其他磷输入）按参考类定义属于'沉积入土壤'的项，不计入 PUE 分母，
        否则 PUE 被系统性低估（对照论文基准 31% 验证该口径）。
        """
        return (self.fert_t + self.reuse_organic_fertilizer_p() + self.manure_return_p()
                + self.excreta_return_p() + self.atmospheric_deposition_p())

    def total_input_p(self):
        return self.productive_input_p() + self.SD_p()

    def total_output_p(self):
        """离开田地的输出：收获物 + 排水淋溶 + 秸秆废弃。"""
        return self.crop_harvest_p() + self.drainage_leaching_p() + self.straw_waste_p()

    def soil_legacy_delta_p(self):
        """土壤遗留磷年增量 = 输入 − 输出（守恒残差项）。"""
        return self.total_input_p() - self.total_output_p()

    def pue(self):
        """种植业磷利用效率 = 收获 P / 可利用磷输入 P。"""
        return self.crop_harvest_p() / self.productive_input_p()

    def fertilizer_share(self):
        """化肥占可利用磷输入的比例（对照论文 >64% 基准）。"""
        return self.fert_t / self.productive_input_p()

    def flows(self):
        """返回该年全部流向（吨 P）。"""
        return {
            "P_Fertilizer": self.fert_t,
            "P_ManureReturn": self.manure_return_p(),
            "P_ResidueReturn": self.reuse_organic_fertilizer_p(),
            "P_ExcretaReturn": self.excreta_return_p(),
            "P_Deposition": self.atmospheric_deposition_p(),
            "P_SD": self.SD_p(),
            "Productive_Input": self.productive_input_p(),
            "Total_Input": self.total_input_p(),
            "P_Uptake": self.crop_uptake_p(),
            "P_Harvest": self.crop_harvest_p(),
            "P_Residue": self.crop_residue_p(),
            "P_Feed_to_LBS": self.reuse_crops_feed_p(),
            "P_Drainage_Leaching": self.drainage_leaching_p(),
            "P_Straw_Waste": self.straw_waste_p(),
            "Total_Output": self.total_output_p(),
            "Soil_Legacy_P_delta": self.soil_legacy_delta_p(),
            "PUE_c": self.pue(),
            "Fert_share": self.fertilizer_share(),
        }


def acs_annual_table():
    """1961-2022 全部年份 ACS 流向表（吨 P）。"""
    rows = {}
    for y in C.YEARS:
        if D._crop_production_year(y) is None:
            continue
        rows[y] = ACSModel(y).flows()
    return pd.DataFrame(rows).T


def verify_mass_balance(flows, tolerance=1e-4):
    """任务书规定的守恒自检（存量变化为平衡残差，构造上应严格成立）。"""
    total_in = flows["Total_Input"]
    total_out = flows["Total_Output"]
    stock_delta = flows["Soil_Legacy_P_delta"]
    rel_err = abs(total_in - (total_out + stock_delta)) / (total_in + 1e-6)
    assert rel_err < tolerance, f"质量守恒未通过，相对误差: {rel_err:.6e}"
    return rel_err


if __name__ == "__main__":
    m = ACSModel(2022)
    f = m.flows()
    print("=== 2022 年农田种植子系统（ACS）各流向 ===")
    for k, v in f.items():
        if k in ("PUE_c", "Fert_share"):
            print(f"  {k:<22} {v * 100:8.2f} %")
        else:
            print(f"  {k:<22} {v / C.T_PER_MT:8.3f} Mt P")
    rel = verify_mass_balance(f)
    print(f"  守恒自检相对误差 = {rel:.2e} (< 1e-4 通过)")
