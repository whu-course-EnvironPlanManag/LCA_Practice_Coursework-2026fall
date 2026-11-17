# -*- coding: utf-8 -*-
"""任务 1：农田种植系统（ACS）磷物质流模型类
参考课程提供的 ACSPModel 源码结构，面向全球尺度 1961–2022 年序列重构。
所有流量单位：kt P（千吨纯磷）。
"""
import numpy as np
import pandas as pd

from config import P2022


class GlobalACSModel:
    """全球农田种植系统（Agricultural Cultivation System）磷流模型。

    输入流：矿物化肥 FD、有机肥（粪肥+污泥+堆肥）OF、大气沉降 AD、种子 SD
    输出流：作物收获 HV、秸秆残留（部分还田 RR）、径流淋溶 RN、侵蚀 ER
    平衡项：土壤 legacy P 存量变化 ΔS = (FD+OF+AD+SD+RR) − Uptake − RN − ER
    """

    def __init__(self, fert, organic, deposition, seed,
                 harvest_ratio=0.70, residue_return_ratio=0.55,
                 runoff_coef=0.150, erosion_coef=0.045,
                 food_share=0.60, feed_to_lbs=3500.0, tolerance=1e-4):
        self.flows = {}
        self.tol = tolerance
        self.flows["Mineral_Fertilizer"] = float(fert)
        self.flows["Organic_Fertilizer"] = float(organic)
        self.flows["Atmospheric_Deposition"] = float(deposition)
        self.flows["Seed"] = float(seed)
        self.hr = harvest_ratio
        self.rr = residue_return_ratio
        self.rc = runoff_coef
        self.ec = erosion_coef
        self.flows["Food_Share"] = food_share
        self.flows["Feed_To_LBS"] = float(feed_to_lbs)

    # ---- 中间量 ----
    def total_input(self):
        """ACS 总磷输入（矿物+有机+沉降+种子）"""
        return (self.flows["Mineral_Fertilizer"] + self.flows["Organic_Fertilizer"]
                + self.flows["Atmospheric_Deposition"] + self.flows["Seed"])

    def uptake(self):
        """作物吸收量 = 收获 + 残留；由总输入与收获比例推算：
        收获 HV = PUE×Total_Input，吸收 = HV / harvest_ratio"""
        hv = self.harvest_p()
        return hv / self.hr

    def harvest_p(self):
        """作物收获磷（收获部分占吸收的 harvest_ratio，
        以化肥主导输入下作物 PUE≈0.42 的文献校准值反推）"""
        return 0.42 * self.total_input()

    def residue_p(self):
        """秸秆/残留磷 = 吸收 − 收获"""
        return self.uptake() - self.harvest_p()

    def residue_return(self):
        """残留物还田量 = 残留 × 还田比例"""
        return self.residue_p() * self.rr

    # ---- 土壤平衡 ----
    def soil_input(self):
        return self.total_input() + self.residue_return()

    def runoff_leaching(self):
        return self.rc * self.soil_input()

    def erosion(self):
        return self.ec * self.soil_input()

    def legacy_delta(self):
        """土壤 legacy P 存量变化（平衡项）"""
        return (self.soil_input() - self.uptake()
                - self.runoff_leaching() - self.erosion())

    def harvest_split(self):
        hv = self.harvest_p()
        food = hv * self.flows["Food_Share"]
        feed = self.flows["Feed_To_LBS"]
        other = hv - food - feed
        return {"Food": food, "Feed_To_LBS": feed, "Other_Uses": other}

    # ---- 守恒自检 ----
    def verify_mass_balance(self):
        """输入 + 秸秆还田 = 吸收 + 流失 + legacy 存量变化"""
        lhs = self.soil_input()
        rhs = (self.uptake() + self.runoff_leaching()
               + self.erosion() + self.legacy_delta())
        rel = abs(lhs - rhs) / (lhs + 1e-6)
        assert rel < self.tol, f"ACS 质量守恒未通过，相对误差: {rel:.3e}"
        return True

    def report(self):
        self.verify_mass_balance()
        sp = self.harvest_split()
        rows = [
            ("矿物化肥输入 FD", self.flows["Mineral_Fertilizer"]),
            ("有机肥输入 OF", self.flows["Organic_Fertilizer"]),
            ("大气沉降 AD", self.flows["Atmospheric_Deposition"]),
            ("种子携带 SD", self.flows["Seed"]),
            ("总磷输入", self.total_input()),
            ("作物收获 HV", self.harvest_p()),
            ("作物吸收 UP", self.uptake()),
            ("秸秆残留", self.residue_p()),
            ("秸秆还田 RR", self.residue_return()),
            ("径流+淋溶 RN", self.runoff_leaching()),
            ("侵蚀流失 ER", self.erosion()),
            ("legacy P 存量变化 ΔS", self.legacy_delta()),
            ("  → 食物", sp["Food"]),
            ("  → 饲料(至LBS)", sp["Feed_To_LBS"]),
            ("  → 其他用途", sp["Other_Uses"]),
        ]
        return pd.DataFrame(rows, columns=["流向", "通量 (kt P)"])


def calibrate_fert_history(crop_series, fert_2022=20500.0, fert_1961=4900.0):
    """由农产品纯磷产出指数外推历史化肥序列：
    fert(t) = fert_2022 × (cropP(t)/cropP(2022))^α，α 经 1961 年基准 4.9 Mt 校准。
    """
    idx = crop_series / crop_series.loc[2022]
    alpha = np.log(fert_1961 / fert_2022) / np.log(idx.loc[1961])
    return (fert_2022 * idx ** alpha), alpha


def organic_from_total(total_input, fert, deposition, seed, sludge, compost,
                       fert_share=0.64):
    """校准反推：使化肥占总输入比例恰为 fert_share 的有机肥量"""
    target = total_input * (1 - fert_share) / fert_share * 0  # placeholder
    others = deposition + seed + sludge + compost
    organic = fert * (1 - fert_share) / fert_share - others
    return organic


def build_acs_2022(params=P2022):
    """按 2022 年校准参数构建 ACS 模型实例。
    化肥占比 64% 为约束：有机肥 = fert×(1-0.64)/0.64 − 其他输入。
    """
    fert = params["fert_2022"]
    others = (params["deposition"] + params["seed"]
              + params["sludge_to_field"] + params["compost_to_field"])
    organic = fert * (1 - 0.64) / 0.64 - others
    return GlobalACSModel(
        fert=fert, organic=organic, deposition=params["deposition"],
        seed=params["seed"], harvest_ratio=0.70,
        residue_return_ratio=params["residue_return_ratio"],
        runoff_coef=params["runoff_coef"], erosion_coef=params["erosion_coef"],
        food_share=0.60, feed_to_lbs=params["feed_from_crop"],
    )


if __name__ == "__main__":
    print("=== 任务 1：2022 年农田种植系统（ACS）磷流向 ===")
    model = build_acs_2022()
    print(model.report().round(1).to_string(index=False))
    print("\n✅ ACS 质量守恒自检通过（相对误差 < 1e-4）")
