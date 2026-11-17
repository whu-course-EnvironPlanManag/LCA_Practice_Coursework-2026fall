"""
03_policy_engine.py — 模块2：政策合规判定 + EPR/CCER/税费激励核算
【AI 辅助编程提示词记录】
Prompt: "政策引擎：工信部2024红线一票否决 + 欧盟2023/1542合规 + 绿色激励核算，返回 ComplianceResult。"
是否经人工校验：是
"""
import importlib.util, os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("config", os.path.join(_HERE, "00_config.py"))
config = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(config)
DATA_DIR = config.DATA_DIR

MIIT = {"li_recovery_min": 0.90, "ni_co_mn_min": 0.98, "electrode_powder_min": 0.98,
    "fluorine_fixation_min": 0.995, "energy_max_kgce_per_t": 2200, "wastewater_recycle_min": 0.90}
EU = {2027: {"li_recovery": 0.50}, 2031: {"li_recovery": 0.80, "recycled_li": 0.06}, 2036: {"recycled_li": 0.12}}
ECON = {"ccer_CNY_per_tCO2e": 84.0, "water_tax_CNY_per_m3": 1.05, "epr_lfp_CNY_per_kg": 10.5,
    "epr_nmc_CNY_per_kg": 5.6, "recycled_li_premium_CNY_per_t": 21000.0, "heavy_metal_tax_CNY_per_kg": 8.4}

class ComplianceResult:
    def __init__(self, is_compliant, violations, financial_adjustment_CNY=0.0):
        self.is_compliant = is_compliant
        self.violations = violations
        self.financial_adjustment_CNY = financial_adjustment_CNY

def evaluate_compliance(scenario):
    violations = []
    if scenario.get("li_recovery_rate", 0) < MIIT["li_recovery_min"]:
        violations.append(f"锂回收率 {scenario.get('li_recovery_rate',0):.1%} < 90%")
    for m in ["ni", "co", "mn"]:
        if scenario.get(f"{m}_recovery_rate", 0) < MIIT["ni_co_mn_min"]:
            violations.append(f"{m.upper()}回收率 {scenario.get(f'{m}_recovery_rate',0):.1%} < 98%")
    if scenario.get("electrode_powder_recovery", 0) < MIIT["electrode_powder_min"]:
        violations.append(f"电极粉料回收率 {scenario.get('electrode_powder_recovery',0):.1%} < 98%")
    if scenario.get("fluorine_fixation_rate", 0) < MIIT["fluorine_fixation_min"]:
        violations.append(f"氟固化率 {scenario.get('fluorine_fixation_rate',0):.1%} < 99.5%")
    if scenario.get("energy_kgce_per_t", 9999) >= MIIT["energy_max_kgce_per_t"]:
        violations.append(f"能耗 {scenario.get('energy_kgce_per_t',0):.0f} >= 2200 kgce/t")
    if scenario.get("wastewater_recycle_rate", 0) < MIIT["wastewater_recycle_min"]:
        violations.append(f"废水循环率 {scenario.get('wastewater_recycle_rate',0):.1%} < 90%")
    eu_year = scenario.get("eu_year", 2031)
    if eu_year in EU:
        eu_t = EU[eu_year]
        if "li_recovery" in eu_t and scenario.get("li_recovery_rate", 0) < eu_t["li_recovery"]:
            violations.append(f"欧盟锂回收率 {scenario.get('li_recovery_rate',0):.1%} < {eu_t['li_recovery']:.0%}")
        if "recycled_li" in eu_t and scenario.get("recycled_li_content", 0) < eu_t["recycled_li"]:
            violations.append(f"欧盟再生锂比例 {scenario.get('recycled_li_content',0):.1%} < {eu_t['recycled_li']:.0%}")
    gwp_red = scenario.get("gwp_reduction_tCO2e", 0)
    water_save = scenario.get("water_saving_m3", 0)
    li2co3_t = scenario.get("li2co3_output_t", 0)
    lfp_t = scenario.get("lfp_mass_t", 0); nmc_t = scenario.get("nmc_mass_t", 0)
    adj = (gwp_red * ECON["ccer_CNY_per_tCO2e"] + water_save * ECON["water_tax_CNY_per_m3"]
        + li2co3_t * ECON["recycled_li_premium_CNY_per_t"]
        + lfp_t * 1000 * ECON["epr_lfp_CNY_per_kg"] + nmc_t * 1000 * ECON["epr_nmc_CNY_per_kg"])
    return ComplianceResult(len(violations) == 0, violations, adj)

if __name__ == "__main__":
    case = {"li_recovery_rate": 0.99, "ni_recovery_rate": 0.99, "co_recovery_rate": 0.99,
        "mn_recovery_rate": 0.98, "electrode_powder_recovery": 0.992, "fluorine_fixation_rate": 0.998,
        "energy_kgce_per_t": 1200, "wastewater_recycle_rate": 0.95, "recycled_li_content": 0.14,
        "eu_year": 2036, "gwp_reduction_tCO2e": 95000, "water_saving_m3": 150000,
        "li2co3_output_t": 18000, "lfp_mass_t": 35000, "nmc_mass_t": 35000}
    r = evaluate_compliance(case)
    print(f"合规: {r.is_compliant}, 违反项: {len(r.violations)}, 财务修正: CNY {r.financial_adjustment_CNY:,.0f}")
