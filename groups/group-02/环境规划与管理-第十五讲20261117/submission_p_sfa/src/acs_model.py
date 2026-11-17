"""农田种植系统（ACS）模型。

参考 source_data/.../8.Code implementation of P_SFA modeling_cropping
system case.py 中 ACSPModel 的方法划分与方程（SI 式 5-1 与 5.3 节），
但改为由本课程包中真实可读的数据驱动：
  * 作物收获磷来自官方纯磷产出表（A–F、H–K 类）；
  * 施肥量来自 FAOSTAT 养分磷肥表；
  * 粪肥还田量来自 LBS 系统输出；
  * 种子磷来自 FAOSTAT Cropland Nutrient Balance 官方估计（data_extra）；
  * 流失系数、沉降系数、秸秆还田比例等来自 SI Table S3/S4。

缺失输入的参数（如逐作物 κu/κh、分作物种子含磷率）以显式接口保留，
计算时给出“缺少输入”提示，不以 0 或任意常数代替。
"""
from __future__ import annotations

from dataclasses import dataclass

from .params import coeff

MT_PER_KG = 1e-9  # kg -> Mt


@dataclass
class ACSResult:
    fertilizer: float
    manure: float
    deposition: float
    seed: float
    harvest: float
    residue: float
    residue_returned: float
    residue_waste: float
    uptake: float
    water_loss: float
    soil_accumulation: float
    seed_missing: bool = True


class ACSModel:
    """农田种植系统磷流计算类（对应论文 ACS）。"""

    def __init__(self, crop_params: dict, system_params: dict, coefficients):
        self.crop_params = crop_params
        self.system_params = system_params
        self.coef = coefficients

    # ---------------------------------------------------------- 独立方程
    def crop_harvest_p(self) -> float:
        """收获物含磷量（Mt P），由官方纯磷产出表直接给出。"""
        return float(self.crop_params["harvest_p"])

    def crop_uptake_p(self) -> float:
        """作物总吸收磷 = 收获磷 + 残留磷（残留比例由 κu/κh 归并）。"""
        return self.crop_harvest_p() * (1.0 + coeff(self.coef, "residue_ratio"))

    def crop_residue_p(self) -> float:
        return self.crop_harvest_p() * coeff(self.coef, "residue_ratio")

    def reuse_organic_fertilizer_p(self) -> float:
        """秸秆还田量 = 残留磷 × β1。"""
        return self.crop_residue_p() * coeff(self.coef, "beta1")

    def atmospheric_deposition_p(self) -> float:
        """大气沉降 = 耕地面积 × λ1。"""
        area_ha = float(self.system_params["cropland_ha"])
        return area_ha * coeff(self.coef, "lambda1") * MT_PER_KG

    def drainage_leaching_p(self) -> float:
        """排水 + 淋溶流失 = 耕地面积 × (κ_drainage + κ_leaching)。"""
        area_ha = float(self.system_params["cropland_ha"])
        k = coeff(self.coef, "kappa_drainage") + coeff(self.coef, "kappa_leaching")
        return area_ha * k * MT_PER_KG

    def seed_p(self) -> float | None:
        """种子磷（Mt P）。

        优先使用 FAOSTAT Cropland Nutrient Balance 的官方种子磷估计
        （data_extra/seed_p_1961_2022.csv，2022 年 0.475 Mt P）；
        未提供时返回 None，表示“缺少输入”，从平衡中显式排除。
        """
        v = self.system_params.get("seed_p")
        if v is None:
            return None
        return float(v)

    # ---------------------------------------------------------- 平衡方程
    def soil_accumulation_p(self) -> float:
        """土壤遗留磷（存量变化），由输入-输出平衡反算（对应式 5-3/5-5）。"""
        seed = self.seed_p()
        if seed is None:          # 缺输入：从平衡中排除，并在结果中标记
            seed = 0.0
        tin = (float(self.system_params["fertilizer_p"])
               + float(self.system_params["manure_p"])
               + self.atmospheric_deposition_p()
               + seed)
        tout = (self.crop_harvest_p()
                + self.residue_waste_p()
                + self.drainage_leaching_p())
        return tin - tout

    def residue_waste_p(self) -> float:
        return self.crop_residue_p() - self.reuse_organic_fertilizer_p()

    # ---------------------------------------------------------- 汇总
    def run(self) -> ACSResult:
        seed = self.seed_p()
        return ACSResult(
            fertilizer=float(self.system_params["fertilizer_p"]),
            manure=float(self.system_params["manure_p"]),
            deposition=self.atmospheric_deposition_p(),
            seed=float(seed) if seed is not None else 0.0,
            harvest=self.crop_harvest_p(),
            residue=self.crop_residue_p(),
            residue_returned=self.reuse_organic_fertilizer_p(),
            residue_waste=self.residue_waste_p(),
            uptake=self.crop_uptake_p(),
            water_loss=self.drainage_leaching_p(),
            soil_accumulation=self.soil_accumulation_p(),
            seed_missing=seed is None,
        )

    def verify_mass_balance(self, tolerance: float = 1e-4) -> tuple[bool, float]:
        r = self.run()
        tin = r.fertilizer + r.manure + r.deposition + r.seed
        tout = r.harvest + r.residue_waste + r.water_loss
        rel = abs(tin - tout - r.soil_accumulation) / (tin + 1e-6)
        return rel < tolerance, rel
