# -*- coding: utf-8 -*-
"""成员C：R1同工况物料去向、环境清单、费用闭合、LCOR/MAC与情景寻优。

本模块只使用Python标准库。所有数量均为2026规划年、年总量；币种CNY；
功能单位为1 t碳酸锂当量（LCE-eq）。数据属性分四类：
组内设定 / 文献原值 / 文献迁移 / 情景假设。
AI辅助生成，须由成员C人工逐项复核后签认；模型结果不构成企业实测或合规认证。
"""
from __future__ import annotations

import itertools
import math

# ---------------------------------------------------------------------------
# 0. 基础参数（R1，A 2026-11-04）
# ---------------------------------------------------------------------------
R1 = {
    "feed_pack_t": 68000.0,
    "candidate_pack_t": 8500.0,
    "q": 0.90,
    "y": 0.97,
    "recycle_pack_t": 60579.5,
    "lfp_share": 0.60,
    "nmc_share": 0.40,
    "lfp_pack_to_cell": 0.6627,
    "nmc_pack_to_cell": 0.63466,
    "powder_per_cell": 0.50,
    "design_recycle_t": 70000.0,
    "operating_years": 20,
}

# LS23 同源粉料路线记录（t/t粉料，另有注明者除外）
LS23 = {
    "crude_li_wet": 0.1420609,
    "crude_li_dry_factor": 0.80 * 0.99,
    "fep_wet": 0.7495861,
    "fep_dry_factor": 0.60 * 0.99,
    "alp": 0.1348885,
    "na2so4": 0.867238,
    "sponge_cu": 0.03958,
    "carbon_residue": 0.5624991,
    "caustic_residue": 0.01566,
    "scrubber_residue": 0.0078929,
    "steam_t_per_powder": 1.1747755,
    "pure_water_m3_per_powder": 0.3491132,
    "acid98_t_per_powder": 0.5630527,
    "h3po4_t_per_powder": 0.098239,
    "fe_t_per_powder": 0.01314,
    "co2_t_per_powder": 0.111,
    "o2_t_per_powder": 0.012,
    "ng_nm3_per_cell": 28.8,
    "n2_nm3_per_cell": 216.0,
    "pre_scrubber_residue_t_per_cell": 0.0345069,
    "foil_cu_t_per_cell": 0.1387118,
    "foil_al_t_per_cell": 0.0594479,
    "powder_li_fraction": 0.024155,
    "powder_fe_fraction": 0.151873,
    "powder_p_fraction": 0.085381,
    "powder_c_fraction": 0.45537,
    "powder_h2o_fraction": 0.0215,
    "li_to_crude_ratio": 0.8749782653694888,
}

# NMC622 / NMC811 元素产出（A R1 表4，t/a @ 60,579.5 t 再生整包基准）
NMC_PRODUCTS = {
    "NMC622": {"li2co3": 1709.26, "ni": 1774.13, "co": 593.80, "mn": 553.54,
               "cu": 2228.41, "al": 1162.65},
    "NMC811": {"li2co3": 1634.75, "ni": 2262.39, "co": 283.96, "mn": 264.71,
               "cu": 2173.05, "al": 1134.97},
}

# 2026 规划价格（CNY）。status: 组内报价/公开参考/情景假设
PRICES = {
    "lce": (133000.0, "电池级碳酸锂≥99.5%"),
    "cu": (62000.0, "再生阴极铜99.9%"),
    "al": (18200.0, "再生铝锭99.7%"),
    "fep": (9500.0, "磷酸铁（电池级参考，未取得成交原件）"),
    "alp": (2500.0, "磷酸铝（工业级参考）"),
    "na2so4": (350.0, "副产硫酸钠（工业级参考）"),
    "ni": (130000.0, "电解镍/LME折算"),
    "co": (250000.0, "电解钴/LME折算"),
    "mn": (15000.0, "电解锰参考"),
    "steel_scrap": (2200.0, "废钢参考"),
    "al_scrap": (14000.0, "废铝参考"),
    "cu_scrap": (55000.0, "废铜缆参考"),
    "reuse_kwh": (480.0, "梯次储能模组"),
    "grid": (0.62, "大工业网电"),
    "green": (0.41, "风光直购绿电"),
    "green_adder": (0.10, "绿电到户附加"),
    "steam": (180.0, "工业蒸汽，按t计"),
    "gas": (3.50, "天然气，元/Nm3"),
    "diesel": (7.50, "柴油，元/L"),
    "n2": (1.20, "氮气，元/Nm3"),
    "h2so4": (480.0, "98%硫酸"),
    "naoh32": (1150.0, "32%液碱"),
    "naoh_solid": (3100.0, "片碱/纯NaOH折算"),
    "cao": (650.0, "92%氧化钙"),
    "h3po4": (5200.0, "85%磷酸"),
    "fe": (6500.0, "99%铁粉"),
    "co2": (800.0, "工业液CO2"),
    "o2": (700.0, "工业液氧"),
    "h2o2": (1800.0, "27.5%双氧水"),
    "na2co3": (2200.0, "纯碱"),
    "hcl": (800.0, "31%盐酸"),
    "nh4oh": (2800.0, "氨水"),
    "water": (4.20, "工业新水"),
    "pure_water": (12.0, "外供纯水"),
    "ww_lfp": (8.0, "LFP废水处理"),
    "ww_nmc": (6.0, "NMC废水处理"),
    "carbon_disposal": (300.0, "碳渣一般固废处置"),
    "haz_waste": (2200.0, "危废处置"),
    "bms_disposal": (3000.0, "BMS/电子废物处置"),
    "plastic_disposal": (500.0, "废塑料处置"),
    "outbound_transport": (120.0, "产品外运，元/t"),
}

# 环境因子（kg CO2e / 单位；水 L/单位）
FACTORS = {
    "grid": (0.556, 2.00, "B-PWR-02"),
    "green": (0.035, 0.20, "B-PWR-01"),
    "gas": (0.067, 0.10, "B-HEAT-01"),       # per MJ
    "steam": (0.210, 1.00, "B-HEAT-02"),     # per MJ
    "diesel": (0.074, 0.05, "GREET-diesel"), # per MJ
    "h2so4": (0.150, 5.00, "B-RG-01"),
    "h2o2": (1.100, 12.00, "B-RG-02"),
    "naoh": (1.050, 9.00, "B-RG-03"),
    "na2co3": (0.950, 7.00, "B-RG-04"),
    "cao": (0.780, 3.00, "B-RG-05"),
    "h3po4": (1.200, 4.00, "C-RG-06"),
    "fe": (2.000, 6.00, "C-RG-07"),
    "co2": (0.900, 1.00, "C-RG-08"),
    "o2": (0.300, 1.50, "C-RG-09"),
    "n2": (0.050, 0.50, "C-RG-10"),
    "hcl": (1.000, 6.00, "C-RG-11"),
    "nh4oh": (0.900, 5.00, "C-RG-12"),
    "water": (0.344, 0.0, "C-UT-01"),
    "pure_water": (0.500, 0.0, "C-UT-02"),
    "ww": (0.300, 0.0, "B-PC-01"),
    "ww_fluoride": (0.800, 0.0, "B-PC-02"),
    "waste": (0.400, 0.0, "B-PC-03"),
    "transport": (0.120, 0.05, "B-TR-01"),
    "repack": (5.000, 2.00, "C-AS-01"),
}

# 原生路线基准（kg CO2e/t 产品；用于系统扩展抵扣与MAC）
PRIMARY_GWP = {
    "lce_spodumene": 9000.0,
    "lce_saltlake": 4000.0,
    "fep": 1500.0,
    "cu": 4000.0,
    "al": 12000.0,
    "ni": 14000.0,
    "co": 8000.0,
    "mn": 2500.0,
    "na2so4": 250.0,
    "alp": 1500.0,
}

STEAM_GJ_PER_T = 2.6
NATURAL_GAS_MJ_PER_NM3 = 36.0
KGCE_PER_KWH = 0.1229
MJ_PER_KGCE = 29.3076
DEFAULT_CRF = 0.09439293

# 成本、投资与费用（组内报价/预算）
ECON = {
    "capex_recycle": 420.0e6,
    "capex_reuse": 36.0e6,
    "labor_total": 10.2e6,
    "labor_reuse_share": 0.15,
    "maintenance_rate": 0.02,
    "rd_social_total": 5.0e6,
    "rd_reuse_share": 0.20,
    "service_total": 3.0e6,
    "service_reuse_share": 0.15,
    "other_total": 1.0e6,
    "other_reuse_share": 0.15,
    "repack_cost_per_kwh": 60.0,
    "employees": 120,
}


def price(key):
    return PRICES[key][0]


def num(value, name, *, positive=False, upper=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name}: 必须为有限数值")
    if value < 0 or (positive and value == 0) or (upper is not None and value > upper):
        raise ValueError(f"{name}: 超出允许范围")
    return float(value)


def crf(rate=0.07, years=20):
    num(rate, "discount_rate", upper=1)
    num(years, "years", positive=True)
    if float(years).is_integer() is False:
        raise ValueError("operating_years 必须为整数")
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1) if rate else 1 / years


# ---------------------------------------------------------------------------
# 1. 物理量与物料去向
# ---------------------------------------------------------------------------
def physical(q=0.90, y=0.97, alpha=0.50, chemistry="NMC622"):
    """返回R1年度物理量。q/y 为梯次筛选与重组保留比例；alpha为LFP电耗分摊。"""
    for k, v in (("q", q), ("y", y), ("alpha", alpha)):
        num(v, k, upper=1)
    if chemistry not in NMC_PRODUCTS:
        raise ValueError("chemistry 仅支持 NMC622 / NMC811")

    feed = R1["feed_pack_t"]
    candidate = R1["candidate_pack_t"]
    retained = candidate * q * y
    recycle = feed - retained
    lfp_pack = recycle * R1["lfp_share"]
    nmc_pack = recycle * R1["nmc_share"]
    lfp_cell = lfp_pack * R1["lfp_pack_to_cell"]
    nmc_cell = nmc_pack * R1["nmc_pack_to_cell"]
    powder = lfp_cell * R1["powder_per_cell"]

    m = {
        "q": q, "y": y, "alpha": alpha, "chemistry": chemistry,
        "candidate_pack_t": candidate, "retained_pack_t": retained,
        "rejected_screen_pack_t": candidate * (1 - q),
        "rejected_reassembly_pack_t": candidate * q * (1 - y),
        "recycle_pack_t": recycle, "lfp_pack_t": lfp_pack, "nmc_pack_t": nmc_pack,
        "lfp_cell_t": lfp_cell, "nmc_cell_t": nmc_cell, "lfp_powder_t": powder,
        "pack_nonecell_t": recycle - lfp_cell - nmc_cell,
        "lfp_nonecell_t": lfp_pack - lfp_cell,
        "nmc_nonecell_t": nmc_pack - nmc_cell,
    }

    # LFP 产品（LS23）
    m["lfp_crude_li_wet_t"] = powder * LS23["crude_li_wet"]
    m["lfp_li2co3_dry_t"] = m["lfp_crude_li_wet_t"] * LS23["crude_li_dry_factor"]
    m["lfp_fep_wet_t"] = powder * LS23["fep_wet"]
    m["lfp_fep_dry_t"] = m["lfp_fep_wet_t"] * LS23["fep_dry_factor"]
    m["lfp_alp_t"] = powder * LS23["alp"]
    m["lfp_na2so4_t"] = powder * LS23["na2so4"]
    m["lfp_sponge_cu_t"] = powder * LS23["sponge_cu"]
    m["lfp_carbon_residue_t"] = powder * LS23["carbon_residue"]
    m["lfp_caustic_residue_t"] = powder * LS23["caustic_residue"]
    m["lfp_scrubber_residue_t"] = powder * LS23["scrubber_residue"]
    m["lfp_pre_scrubber_residue_t"] = lfp_cell * LS23["pre_scrubber_residue_t_per_cell"]
    m["lfp_cu_foil_t"] = lfp_cell * LS23["foil_cu_t_per_cell"]
    m["lfp_al_foil_t"] = lfp_cell * LS23["foil_al_t_per_cell"]
    m["lfp_other_cell_t"] = lfp_cell - powder - m["lfp_cu_foil_t"] - m["lfp_al_foil_t"]

    # LFP 输入
    m["lfp_steam_t"] = powder * LS23["steam_t_per_powder"]
    m["lfp_acid98_t"] = powder * LS23["acid98_t_per_powder"]
    m["lfp_caustic32_t"] = 19317.51
    m["lfp_cao92_t"] = 727.45
    m["lfp_h3po4_85_t"] = powder * LS23["h3po4_t_per_powder"]
    m["lfp_fe99_t"] = powder * LS23["fe_t_per_powder"]
    m["lfp_co2_t"] = powder * LS23["co2_t_per_powder"]
    m["lfp_o2_t"] = powder * LS23["o2_t_per_powder"]
    m["lfp_n2_nm3"] = lfp_cell * LS23["n2_nm3_per_cell"]
    m["lfp_ng_nm3"] = lfp_cell * LS23["ng_nm3_per_cell"]
    m["lfp_pure_water_m3"] = powder * LS23["pure_water_m3_per_powder"]
    m["lfp_tap_water_m3"] = 28566.06
    m["lfp_wastewater_m3"] = 6825.04
    m["lfp_electricity_kwh"] = 11232000 * (
        alpha * lfp_cell / 10000 + (1 - alpha) * powder / 10000)

    # Li 平衡与未分配 Li 去向（C情景拆分）
    m["lfp_li_input_t"] = powder * LS23["powder_li_fraction"]
    m["lfp_li_in_crude_t"] = powder * 0.0211351
    m["lfp_li_unallocated_t"] = m["lfp_li_input_t"] - m["lfp_li_in_crude_t"]
    m["lfp_li_loss_wastewater_t"] = m["lfp_li_unallocated_t"] * 0.45
    m["lfp_li_loss_residue_t"] = m["lfp_li_unallocated_t"] * 0.35
    m["lfp_li_loss_fep_t"] = m["lfp_li_unallocated_t"] * 0.20
    m["lfp_li_recovery"] = m["lfp_li_in_crude_t"] / m["lfp_li_input_t"]

    # NMC 产品（元素基 + 盐商品质量）
    n = NMC_PRODUCTS[chemistry]
    scale = recycle / R1["recycle_pack_t"]
    n = {k: v * scale for k, v in n.items()}
    m.update({f"nmc_{k}_t": v for k, v in n.items()})
    m["nmc_li2co3_t"] = n["li2co3"]
    m["nmc_ni_t"], m["nmc_co_t"], m["nmc_mn_t"] = n["ni"], n["co"], n["mn"]
    m["nmc_cu_t"], m["nmc_al_t"] = n["cu"], n["al"]
    m["nmc_niso4_t"] = n["ni"] * 262.85 / 58.69
    m["nmc_coso4_t"] = n["co"] * 281.10 / 58.93
    m["nmc_mnso4_t"] = n["mn"] * 169.02 / 54.94
    m["nmc_salt_mass_t"] = (m["nmc_niso4_t"] + m["nmc_coso4_t"]
                            + m["nmc_mnso4_t"] + n["li2co3"])
    m["nmc_element_products_t"] = (n["li2co3"] + n["ni"] + n["co"] + n["mn"]
                                   + n["cu"] + n["al"])
    m["nmc_other_cell_t"] = nmc_cell - m["nmc_element_products_t"]
    m["nmc_graphite_t"] = m["nmc_other_cell_t"] * 0.52
    m["nmc_casing_t"] = m["nmc_other_cell_t"] * 0.30
    m["nmc_electrolyte_t"] = m["nmc_other_cell_t"] * 0.18

    # NMC 试剂与公用工程
    m["nmc_h2so4_t"] = nmc_cell * 1.08
    m["nmc_h2o2_t"] = nmc_cell * 0.366
    m["nmc_naoh_t"] = nmc_cell * 0.561
    m["nmc_hcl_t"] = nmc_cell * 0.012
    m["nmc_nh4oh_t"] = nmc_cell * 0.031
    # 沉锂碳酸钠：按A R1给的计量式，替代ANL默认0.02 kg/kg
    m["nmc_na2co3_t"] = n["li2co3"] * 105.988 / 73.888 * 1.10 / 0.99
    # 中和副产硫酸钠：NaOH折算（C估算，非A原表）
    m["nmc_na2so4_t"] = m["nmc_naoh_t"] * 142.04 / 80.00
    m["nmc_ng_mj"] = nmc_cell * 2500.0
    m["nmc_diesel_mj"] = nmc_cell * 600.0
    m["nmc_water_m3"] = nmc_cell * 3.785411784
    m["nmc_wastewater_m3"] = m["nmc_water_m3"] * 0.80
    m["nmc_electricity_kwh"] = nmc_cell * 1000 * 0.125 / 3.6

    # 整包非电芯组分去向（C情景拆分）
    pn = m["pack_nonecell_t"]
    m["scrap_steel_t"] = pn * 0.55
    m["scrap_al_t"] = pn * 0.08
    m["scrap_cu_t"] = pn * 0.12
    m["scrap_bms_t"] = pn * 0.08
    m["scrap_plastic_t"] = pn * 0.17

    # 梯次
    m["reuse_capacity_kwh"] = retained * 118.0 * 0.80
    m["reuse_testing_kwh"] = candidate * 118.0 * 8.72 / 11.4
    m["reuse_new_parts_t"] = retained * 0.02

    # 汇总
    m["lce_t"] = m["lfp_li2co3_dry_t"] + m["nmc_li2co3_t"]
    m["lfp_li_in_lce_t"] = m["lfp_li2co3_dry_t"] * 2 * 6.94 / 73.888
    m["nmc_li_in_lce_t"] = m["nmc_li2co3_t"] * 2 * 6.94 / 73.888
    m["nmc_li_input_t"] = m["nmc_li_in_lce_t"] / 0.90
    m["li_smelting_recovery"] = (
        (m["lfp_li_in_crude_t"] + m["nmc_li_in_lce_t"])
        / (m["lfp_li_input_t"] + m["nmc_li_input_t"]))
    m["copper_product_t"] = m["lfp_cu_foil_t"] * 0.97 + m["nmc_cu_t"]
    m["al_product_t"] = m["lfp_al_foil_t"] * 0.97 + m["nmc_al_t"]
    m["recycling_load"] = recycle / R1["design_recycle_t"]
    return m


# ---------------------------------------------------------------------------
# 2. 环境清单
# ---------------------------------------------------------------------------
def environment_rows(m, green_fraction=0.5, energy_case="R1", include_transport=True):
    """同工况环境清单：每条活动量×因子，返回行列表与合计。"""
    num(green_fraction, "green_fraction", upper=1)
    grid_ef, grid_w, _ = FACTORS["grid"]
    green_ef, green_w, _ = FACTORS["green"]
    ef = (1 - green_fraction) * grid_ef + green_fraction * green_ef
    wf = (1 - green_fraction) * grid_w + green_fraction * green_w
    rows = []

    def add(stage, item, qty, unit, key, source, status="情景计算", water_per=None,
            factor_override=None):
        f, w, fid = FACTORS[key]
        if factor_override is not None:
            f = factor_override
        rows.append({
            "stage": stage, "item": item, "quantity": round(qty, 4), "unit": unit,
            "factor_id": fid, "factor": f, "gwp_kg": qty * f,
            "water_l": (water_per if water_per is not None else qty * w),
            "source": source, "status": status,
        })

    elec_nmc = m["nmc_electricity_kwh"]
    if energy_case == "conservative":
        # 用LFP湿法比电耗(约561 kWh/t电芯)补齐ANL代理未覆盖的公辅电耗
        elec_nmc = m["nmc_cell_t"] * 561.0
    add("电力", "LFP组合电耗", m["lfp_electricity_kwh"], "kWh", "grid",
        "A-R1 LS23组合电耗; EF=B-PWR", water_per=m["lfp_electricity_kwh"] * wf,
        factor_override=ef)
    add("电力", "NMC湿法电耗", elec_nmc, "kWh", "grid",
        "A-R1 ANL代理; EF=B-PWR", water_per=elec_nmc * wf, factor_override=ef)
    add("电力", "梯次测试电耗", m["reuse_testing_kwh"], "kWh", "grid",
        "A-R1 JRC测试; EF=B-PWR", water_per=m["reuse_testing_kwh"] * wf,
        factor_override=ef)
    add("热力", "LFP天然气", m["lfp_ng_nm3"] * NATURAL_GAS_MJ_PER_NM3, "MJ", "gas", "A-R1")
    add("热力", "LFP蒸汽", m["lfp_steam_t"] * STEAM_GJ_PER_T * 1000, "MJ", "steam",
        "A-R1质量×2.6GJ/t情景换算")
    add("热力", "NMC天然气", m["nmc_ng_mj"], "MJ", "gas", "A-R1 ANL Table10")
    add("热力", "NMC柴油", m["nmc_diesel_mj"], "MJ", "diesel", "A-R1 ANL Table10")

    add("药剂", "LFP硫酸(98%)", m["lfp_acid98_t"] * 0.98, "t", "h2so4", "A-R1 LS23")
    add("药剂", "LFP液碱(32%)", m["lfp_caustic32_t"] * 0.32, "t", "naoh", "A-R1 LS23")
    add("药剂", "LFP氧化钙(92%)", m["lfp_cao92_t"] * 0.92, "t", "cao", "A-R1 LS23")
    add("药剂", "LFP磷酸(85%)", m["lfp_h3po4_85_t"] * 0.85, "t", "h3po4", "A-R1 LS23")
    add("药剂", "LFP铁粉(99%)", m["lfp_fe99_t"] * 0.99, "t", "fe", "A-R1 LS23")
    add("药剂", "LFP液CO2", m["lfp_co2_t"], "t", "co2", "A-R1 LS23")
    add("药剂", "LFP液氧", m["lfp_o2_t"], "t", "o2", "A-R1 LS23")
    add("药剂", "LFP氮气", m["lfp_n2_nm3"] * 1.25 / 1000, "t", "n2", "A-R1 LS23")
    add("药剂", "NMC硫酸(98%)", m["nmc_h2so4_t"] * 0.98, "t", "h2so4", "A-R1 ANL")
    add("药剂", "NMC双氧水", m["nmc_h2o2_t"], "t", "h2o2", "A-R1 ANL")
    add("药剂", "NMC片碱", m["nmc_naoh_t"], "t", "naoh", "A-R1 ANL")
    add("药剂", "NMC碳酸钠", m["nmc_na2co3_t"], "t", "na2co3", "A-R1计量式")
    add("药剂", "NMC盐酸", m["nmc_hcl_t"], "t", "hcl", "A-R1 ANL")
    add("药剂", "NMC氨水", m["nmc_nh4oh_t"], "t", "nh4oh", "A-R1 ANL")

    add("水", "LFP新水", m["lfp_tap_water_m3"], "m3", "water", "A-R1 LS23")
    add("水", "LFP外供纯水", m["lfp_pure_water_m3"], "m3", "pure_water", "A-R1 LS23")
    add("水", "NMC过程水", m["nmc_water_m3"], "m3", "water", "A-R1 ANL代理")

    add("废水", "LFP已列废水", m["lfp_wastewater_m3"], "m3", "ww_fluoride", "A-R1 LS23")
    add("废水", "NMC废水", m["nmc_wastewater_m3"], "m3", "ww", "C按80%外排情景")

    add("固废", "LFP碳渣", m["lfp_carbon_residue_t"], "t", "waste", "A-R1 LS23")
    add("固废", "LFP钙渣/水洗渣", m["lfp_caustic_residue_t"] + m["lfp_scrubber_residue_t"]
        + m["lfp_pre_scrubber_residue_t"], "t", "waste", "A-R1 LS23")
    add("固废", "NMC石墨渣", m["nmc_graphite_t"], "t", "waste", "C情景拆分")
    add("固废", "NMC电解液/隔膜危废", m["nmc_electrolyte_t"], "t", "waste", "C情景拆分")

    add("梯次", "梯次重组新增件", m["reuse_new_parts_t"], "t", "repack", "C情景假设")

    if include_transport:
        add("运输", "退役电池入厂运输", R1["feed_pack_t"] * 300.0, "tkm", "transport",
            "C情景：平均300km")
        outbound = (m["lce_t"] + m["lfp_fep_wet_t"] + m["lfp_alp_t"] + m["lfp_na2so4_t"]
                    + m["lfp_sponge_cu_t"] + m["copper_product_t"] + m["al_product_t"]
                    + m["nmc_salt_mass_t"] + m["nmc_na2so4_t"] + m["scrap_steel_t"]
                    + m["scrap_al_t"] + m["scrap_cu_t"])
        add("运输", "产品与副产物外运", outbound * 200.0, "tkm", "transport",
            "C情景：平均200km")

    total_gwp = sum(r["gwp_kg"] for r in rows)
    total_water = sum(r["water_l"] for r in rows)
    return {"rows": rows, "gwp_kg": total_gwp, "water_l": total_water,
            "electricity_ef_kg_per_kwh": ef}


def credit_rows(m):
    """系统扩展：联产品抵扣原生生产，单位kg CO2e。"""
    items = [
        ("LCE", m["lce_t"], "lce_spodumene"),
        ("磷酸铁", m["lfp_fep_dry_t"], "fep"),
        ("磷酸铝", m["lfp_alp_t"], "alp"),
        ("硫酸钠(LFP)", m["lfp_na2so4_t"], "na2so4"),
        ("硫酸钠(NMC)", m["nmc_na2so4_t"], "na2so4"),
        ("铜", m["copper_product_t"] + m["lfp_sponge_cu_t"], "cu"),
        ("铝", m["al_product_t"], "al"),
        ("镍", m["nmc_ni_t"], "ni"),
        ("钴", m["nmc_co_t"], "co"),
        ("锰", m["nmc_mn_t"], "mn"),
    ]
    rows = []
    for name, qty, key in items:
        f = PRIMARY_GWP[key]
        rows.append({"product": name, "quantity_t": qty, "factor_kg_per_t": f,
                     "avoided_kg": qty * f, "basis": key})
    return {"rows": rows, "avoided_kg": sum(r["avoided_kg"] for r in rows)}


# ---------------------------------------------------------------------------
# 3. 费用与收入
# ---------------------------------------------------------------------------
def value_per_t_pack(m):
    """按产品参考价与实现系数估算每吨整包的可回收价值（用于采购价联动）。"""
    li_real, met_real = 0.70, 0.85
    lfp_rev = (m["lfp_li2co3_dry_t"] * price("lce") * li_real
               + m["lfp_fep_dry_t"] * price("fep") * met_real
               + m["lfp_alp_t"] * price("alp") * 0.80
               + m["lfp_na2so4_t"] * price("na2so4") * 0.80
               + (m["lfp_cu_foil_t"] * 0.97 + m["lfp_sponge_cu_t"]) * price("cu") * met_real
               + m["lfp_al_foil_t"] * 0.97 * price("al") * met_real)
    nmc_rev = (m["nmc_li2co3_t"] * price("lce") * li_real
               + m["nmc_cu_t"] * price("cu") * met_real
               + m["nmc_al_t"] * price("al") * met_real
               + m["nmc_ni_t"] * price("ni") * met_real
               + m["nmc_co_t"] * price("co") * met_real
               + m["nmc_mn_t"] * price("mn") * met_real
               + m["nmc_na2so4_t"] * price("na2so4") * 0.80)
    scrap = (m["scrap_steel_t"] * price("steel_scrap") * 0.9
             + m["scrap_al_t"] * price("al_scrap") * 0.9
             + m["scrap_cu_t"] * price("cu_scrap") * 0.9)
    # 非电芯废料按再生整包比例分摊
    lfp_scrap = scrap * m["lfp_pack_t"] / m["recycle_pack_t"]
    nmc_scrap = scrap * m["nmc_pack_t"] / m["recycle_pack_t"]
    return {"lfp": (lfp_rev + lfp_scrap) / m["lfp_pack_t"],
            "nmc": (nmc_rev + nmc_scrap) / m["nmc_pack_t"]}


def cost_rows(m, feed_mode="group", linkage=0.80, feed_multiplier=1.0, green_fraction=0.5):
    """年度费用。feed_mode: group=组内报价; value=按可回收价值×linkage。"""
    num(linkage, "linkage", upper=1)
    v = value_per_t_pack(m)
    if feed_mode == "group":
        plfp, pnmc = 5200.0, 8800.0
    elif feed_mode == "value":
        plfp, pnmc = v["lfp"] * linkage, v["nmc"] * linkage
    else:
        raise ValueError("feed_mode 仅支持 group/value")
    plfp *= feed_multiplier
    pnmc *= feed_multiplier

    rows = []

    def add(category, name, qty, unit, unit_price, flow, status="组内报价/预算", source="C-ECON"):
        rows.append({"category": category, "item": name, "quantity": qty, "unit": unit,
                     "unit_price": unit_price, "annual_CNY": qty * unit_price,
                     "flow_ref": flow, "source": source, "status": status})

    add("feedstock", "LFP退役整包到厂", m["lfp_pack_t"], "t", plfp, "lfp_pack_t",
        "组内参考价" if feed_mode == "group" else "金属价值联动情景价")
    add("feedstock", "NMC退役整包到厂", m["nmc_pack_t"], "t", pnmc, "nmc_pack_t",
        "组内参考价" if feed_mode == "group" else "金属价值联动情景价")

    add("labor", "人工预算", 1, "项", ECON["labor_total"] * (1 - ECON["labor_reuse_share"]),
        "shared", "预算")
    add("maintenance", "维修预算", 1, "项", ECON["capex_recycle"] * ECON["maintenance_rate"],
        "capex_recycle", "预算")
    add("rd", "研发预算", 1, "项", ECON["rd_social_total"] * (1 - ECON["rd_reuse_share"]),
        "shared", "预算")
    add("services", "其他服务预算", 1, "项",
        ECON["service_total"] * (1 - ECON["service_reuse_share"]), "shared", "预算")
    add("other", "其他费用预算", 1, "项",
        ECON["other_total"] * (1 - ECON["other_reuse_share"]), "shared", "预算")

    ep = (1 - green_fraction) * price("grid") + green_fraction * (price("green") + price("green_adder"))
    add("utilities", "电力（LFP+NMC）", m["lfp_electricity_kwh"] + m["nmc_electricity_kwh"],
        "kWh", ep, "electricity", "组内电价")
    add("utilities", "蒸汽", m["lfp_steam_t"], "t", price("steam"), "lfp_steam_t")
    add("utilities", "天然气", m["lfp_ng_nm3"], "Nm3", price("gas"), "lfp_ng_nm3")
    add("utilities", "NMC天然气", m["nmc_ng_mj"] / NATURAL_GAS_MJ_PER_NM3, "Nm3",
        price("gas"), "nmc_ng_mj")
    add("utilities", "柴油", m["nmc_diesel_mj"] / 36.0 / 3.6, "L", price("diesel"),
        "nmc_diesel_mj")
    add("utilities", "氮气", m["lfp_n2_nm3"], "Nm3", price("n2"), "lfp_n2_nm3")
    add("utilities", "工业新水", m["lfp_tap_water_m3"], "m3", price("water"), "lfp_tap_water_m3")
    add("utilities", "外供纯水", m["lfp_pure_water_m3"], "m3", price("pure_water"),
        "lfp_pure_water_m3")
    add("utilities", "NMC过程水", m["nmc_water_m3"], "m3", price("water"), "nmc_water_m3")

    add("reagents", "98%硫酸(LFP)", m["lfp_acid98_t"], "t", price("h2so4"), "lfp_acid98_t")
    add("reagents", "32%液碱(LFP)", m["lfp_caustic32_t"], "t", price("naoh32"),
        "lfp_caustic32_t")
    add("reagents", "92%氧化钙", m["lfp_cao92_t"], "t", price("cao"), "lfp_cao92_t")
    add("reagents", "85%磷酸", m["lfp_h3po4_85_t"], "t", price("h3po4"), "lfp_h3po4_85_t")
    add("reagents", "99%铁粉", m["lfp_fe99_t"], "t", price("fe"), "lfp_fe99_t")
    add("reagents", "液CO2", m["lfp_co2_t"], "t", price("co2"), "lfp_co2_t")
    add("reagents", "液氧", m["lfp_o2_t"], "t", price("o2"), "lfp_o2_t")
    add("reagents", "98%硫酸(NMC)", m["nmc_h2so4_t"], "t", price("h2so4"), "nmc_h2so4_t")
    add("reagents", "双氧水", m["nmc_h2o2_t"], "t", price("h2o2"), "nmc_h2o2_t")
    add("reagents", "片碱(NMC)", m["nmc_naoh_t"], "t", price("naoh_solid"), "nmc_naoh_t")
    add("reagents", "碳酸钠", m["nmc_na2co3_t"], "t", price("na2co3"), "nmc_na2co3_t")
    add("reagents", "盐酸", m["nmc_hcl_t"], "t", price("hcl"), "nmc_hcl_t")
    add("reagents", "氨水", m["nmc_nh4oh_t"], "t", price("nh4oh"), "nmc_nh4oh_t")

    add("pollution_control", "LFP废水处理", m["lfp_wastewater_m3"], "m3", price("ww_lfp"),
        "lfp_wastewater_m3")
    add("pollution_control", "NMC废水处理", m["nmc_wastewater_m3"], "m3", price("ww_nmc"),
        "nmc_wastewater_m3")
    add("pollution_control", "碳渣处置", m["lfp_carbon_residue_t"], "t",
        price("carbon_disposal"), "lfp_carbon_residue_t")
    add("pollution_control", "钙渣/水洗渣危废", m["lfp_caustic_residue_t"]
        + m["lfp_scrubber_residue_t"] + m["lfp_pre_scrubber_residue_t"], "t",
        price("haz_waste"), "lfp_residues")
    add("pollution_control", "NMC石墨渣处置", m["nmc_graphite_t"], "t",
        price("carbon_disposal"), "nmc_graphite_t")
    add("pollution_control", "NMC电解液/隔膜危废", m["nmc_electrolyte_t"], "t",
        price("haz_waste"), "nmc_electrolyte_t")
    add("pollution_control", "BMS/电子废物处置", m["scrap_bms_t"], "t",
        price("bms_disposal"), "scrap_bms_t")
    add("pollution_control", "废塑料处置", m["scrap_plastic_t"], "t",
        price("plastic_disposal"), "scrap_plastic_t")

    outbound = (m["lce_t"] + m["lfp_fep_wet_t"] + m["lfp_alp_t"] + m["lfp_na2so4_t"]
                + m["lfp_sponge_cu_t"] + m["copper_product_t"] + m["al_product_t"]
                + m["nmc_salt_mass_t"] + m["nmc_na2so4_t"] + m["scrap_steel_t"]
                + m["scrap_al_t"] + m["scrap_cu_t"])
    add("transport", "产品与副产物外运", outbound, "t", price("outbound_transport"),
        "outbound")

    return {"rows": rows, "lfp_price": plfp, "nmc_price": pnmc,
            "feedstock_CNY": m["lfp_pack_t"] * plfp + m["nmc_pack_t"] * pnmc}


def revenue_rows(m, li_realization=0.70, metal_realization=0.85, reuse_realization=0.75):
    for k, v in (("li_realization", li_realization), ("metal_realization", metal_realization),
                 ("reuse_realization", reuse_realization)):
        num(v, k, upper=1)
    rows = []

    def add(product, qty, unit, unit_price, realization, flow, status="参考价×实现系数，非已核实合同"):
        rows.append({"product": product, "quantity": qty, "unit": unit,
                     "unit_price": unit_price, "realization": realization,
                     "annual_CNY": qty * unit_price * realization,
                     "flow_ref": flow, "status": status})

    add("碳酸锂当量（粗品/当量）", m["lce_t"], "t", price("lce"), li_realization, "lce_t")
    add("磷酸铁（干纯）", m["lfp_fep_dry_t"], "t", price("fep"), metal_realization, "lfp_fep_dry_t")
    add("磷酸铝", m["lfp_alp_t"], "t", price("alp"), 0.80, "lfp_alp_t")
    add("硫酸钠(LFP)", m["lfp_na2so4_t"], "t", price("na2so4"), 0.80, "lfp_na2so4_t")
    add("硫酸钠(NMC副产)", m["nmc_na2so4_t"], "t", price("na2so4"), 0.80, "nmc_na2so4_t")
    add("铜（箔+海绵铜）", m["copper_product_t"] + m["lfp_sponge_cu_t"], "t", price("cu"),
        metal_realization, "copper")
    add("铝（箔）", m["al_product_t"], "t", price("al"), metal_realization, "al")
    add("镍（硫酸镍中元素）", m["nmc_ni_t"], "t", price("ni"), metal_realization, "nmc_ni_t")
    add("钴（硫酸钴中元素）", m["nmc_co_t"], "t", price("co"), metal_realization, "nmc_co_t")
    add("锰（硫酸锰中元素）", m["nmc_mn_t"], "t", price("mn"), metal_realization, "nmc_mn_t")
    add("废钢", m["scrap_steel_t"], "t", price("steel_scrap"), 0.90, "scrap_steel_t")
    add("废铝", m["scrap_al_t"], "t", price("al_scrap"), 0.90, "scrap_al_t")
    add("废铜缆", m["scrap_cu_t"], "t", price("cu_scrap"), 0.90, "scrap_cu_t")
    return {"rows": rows, "total_CNY": sum(r["annual_CNY"] for r in rows)}


def reuse_economics(m, feed_mode="group", linkage=0.80, feed_multiplier=1.0,
                    reuse_realization=0.75, green_fraction=0.5):
    v = value_per_t_pack(m)
    if feed_mode == "group":
        plfp, pnmc = 5200.0, 8800.0
    else:
        plfp, pnmc = v["lfp"] * linkage, v["nmc"] * linkage
    plfp *= feed_multiplier
    pnmc *= feed_multiplier
    blended = (plfp * R1["lfp_share"] + pnmc * R1["nmc_share"])
    feed = m["retained_pack_t"] * blended
    parts = m["reuse_new_parts_t"] * 5000.0
    test = m["reuse_testing_kwh"] * ((1 - green_fraction) * price("grid")
                                     + green_fraction * (price("green") + price("green_adder")))
    repack = m["reuse_capacity_kwh"] * ECON["repack_cost_per_kwh"]
    labor = ECON["labor_total"] * ECON["labor_reuse_share"]
    maint = ECON["capex_reuse"] * ECON["maintenance_rate"]
    rd = ECON["rd_social_total"] * ECON["rd_reuse_share"]
    serv = ECON["service_total"] * ECON["service_reuse_share"]
    other = ECON["other_total"] * ECON["other_reuse_share"]
    annuity = ECON["capex_reuse"] * crf()
    cost = feed + parts + test + repack + labor + maint + rd + serv + other + annuity
    revenue = m["reuse_capacity_kwh"] * price("reuse_kwh") * reuse_realization
    return {"feed_cost": feed, "repack": repack, "cost": cost, "revenue": revenue,
            "margin": revenue - cost, "feed_price": blended,
            "annuity": annuity, "kwh": m["reuse_capacity_kwh"]}


# ---------------------------------------------------------------------------
# 4. LCOR / MAC 与情景
# ---------------------------------------------------------------------------
def apply_recovery_case(m, case="base"):
    """政策合规改进工况：提高Li与Cu/Al回收率，并计入改造投资与运行费。

    base=按R1默认（Li 87.50%，Cu/Al 90%）；improved=Li 92%、Cu/Al 98%。
    提升以同一进料为分母，产品量按比例增加；改造费作为情景假设单列。
    """
    if case not in {"base", "improved"}:
        raise ValueError("recovery_case 仅支持 base/improved")
    out = dict(m)
    if case == "improved":
        factor_li = 0.92 / m["li_smelting_recovery"]
        factor_metal = 0.98 / 0.90
        for key in ("lfp_li2co3_dry_t", "nmc_li2co3_t", "lce_t",
                    "lfp_li_in_lce_t", "nmc_li_in_lce_t"):
            out[key] = m[key] * factor_li
        for key in ("copper_product_t", "al_product_t", "lfp_cu_foil_t", "lfp_al_foil_t",
                    "nmc_cu_t", "nmc_al_t", "lfp_sponge_cu_t"):
            out[key] = m[key] * factor_metal
        out["li_smelting_recovery"] = 0.92
        out["cu_al_recovery"] = 0.98
        out["compliance_extra_capex"] = 20.0e6
        out["compliance_extra_opex"] = 8.0e6
        out["recovery_case"] = "improved"
    else:
        out["cu_al_recovery"] = 0.90
        out["compliance_extra_capex"] = 0.0
        out["compliance_extra_opex"] = 0.0
        out["recovery_case"] = "base"
    return out


def policy_metrics(m, energy_case="R1", rd_revenue_fraction=None):
    """把物料/能耗结果映射为政策引擎指标；缺证据项保留None，不代填。"""
    elec = m["lfp_electricity_kwh"] + m["nmc_electricity_kwh"]
    if energy_case == "conservative":
        elec = m["lfp_electricity_kwh"] + m["nmc_cell_t"] * 561.0
    tce = (elec * KGCE_PER_KWH
           + (m["lfp_ng_nm3"] * NATURAL_GAS_MJ_PER_NM3
              + m["lfp_steam_t"] * STEAM_GJ_PER_T * 1000
              + m["nmc_ng_mj"] + m["nmc_diesel_mj"]) / MJ_PER_KGCE)
    return {
        "li_smelting_recovery": m["li_smelting_recovery"],
        "ni_smelting_recovery": 0.98,
        "co_smelting_recovery": 0.98,
        "mn_smelting_recovery": 0.98,
        "cu_recovery": m.get("cu_al_recovery", 0.90),
        "al_recovery": m.get("cu_al_recovery", 0.90),
        "electrode_powder_recovery": 0.9898,
        "powder_al_impurity": 0.010,
        "powder_cu_impurity": 0.008,
        "fluorine_fixation": 0.995,
        "process_wastewater_reuse": 0.90,
        "lce_energy_kgce_per_t": tce / m["lce_t"],
        "rd_revenue_fraction": rd_revenue_fraction,
        "recycling_capacity_t_per_year": R1["design_recycle_t"],
    }


def material_flow_rows(m):
    """物料去向表：每条流股的数量、形态、去向与计价/处置。"""
    rows = []

    def add(sid, stage, stream, qty, form, destination, treatment, basis):
        rows.append({"flow_id": sid, "stage": stage, "stream": stream,
                     "quantity_t": round(qty, 4), "form": form,
                     "destination": destination, "treatment": treatment, "basis": basis})

    add("F00", "入厂", "退役动力电池整包", R1["feed_pack_t"], "整包", "园区",
        "到厂含运", "A-R1 组内设定")
    add("F01", "梯次", "梯次保留旧包当量", m["retained_pack_t"], "整包当量",
        "梯次模组", "重组后交付", "A-R1 q×y")
    add("F02", "梯次", "筛除返回再生", m["rejected_screen_pack_t"], "整包", "再生线",
        "返回F03", "A-R1 (1-q)")
    add("F03", "梯次", "重组弃用返回再生", m["rejected_reassembly_pack_t"], "整包",
        "再生线", "返回F03", "A-R1 q(1-y)")
    add("F04", "再生", "再生整包", m["recycle_pack_t"], "整包", "拆解",
        "拆解分选", "A-R1")
    add("F05", "再生", "其中LFP整包", m["lfp_pack_t"], "整包", "LFP线", "—", "A-R1 60%")
    add("F06", "再生", "其中三元整包", m["nmc_pack_t"], "整包", "三元线", "—", "A-R1 40%")
    add("F07", "拆解", "LFP电芯", m["lfp_cell_t"], "电芯", "破碎分选", "—", "A-R1 66.27%")
    add("F08", "拆解", "三元电芯", m["nmc_cell_t"], "电芯", "湿法", "—", "A-R1 63.466%")
    add("F09", "拆解", "整包非电芯组分", m["pack_nonecell_t"], "壳体/线束/BMS",
        "再生/资源化", "拆分计价", "C情景拆分")
    add("F10", "分选", "LFP黑粉", m["lfp_powder_t"], "粉料", "LFP湿法", "—",
        "A-R1 50%电芯")
    add("F11", "分选", "LFP铜箔", m["lfp_cu_foil_t"], "97%Cu", "铜产品", "外售",
        "LS23表3.4-1")
    add("F12", "分选", "LFP铝箔", m["lfp_al_foil_t"], "97%Al", "铝产品", "外售",
        "LS23表3.4-1")
    add("F13", "分选", "LFP其他电芯组分", m["lfp_other_cell_t"], "隔膜/电解液/壳体",
        "危废/废料", "处置", "C差减")
    add("F14", "湿法", "粗碳酸锂(湿)", m["lfp_crude_li_wet_t"], "含水20%，干纯99%",
        "锂产品", "按LCE当量结算", "LS23表3.4-1")
    add("F15", "湿法", "磷酸铁(湿)", m["lfp_fep_wet_t"], "含水40%，干纯99%",
        "铁磷产品", "外售/进一步精制", "LS23表3.4-1")
    add("F16", "湿法", "磷酸铝", m["lfp_alp_t"], "商品", "副产物", "外售", "LS23表3.4-1")
    add("F17", "湿法", "硫酸钠(LFP)", m["lfp_na2so4_t"], "商品", "副产物", "外售",
        "LS23表3.4-1")
    add("F18", "湿法", "海绵铜", m["lfp_sponge_cu_t"], "元素Cu", "铜产品", "外售",
        "LS23表3.4-1")
    add("F19", "湿法", "碳渣", m["lfp_carbon_residue_t"], "石墨/炭黑", "一般固废",
        "建材/填埋", "LS23表4.3-23")
    add("F20", "湿法", "钙渣与水洗渣", m["lfp_caustic_residue_t"] + m["lfp_scrubber_residue_t"]
        + m["lfp_pre_scrubber_residue_t"], "渣", "危废", "处置", "LS23表4.3-23")
    add("F21", "三元", "碳酸锂当量", m["nmc_li2co3_t"], "化合物当量", "锂产品",
        "按LCE当量结算", "A-R1 ANL")
    add("F22", "三元", "硫酸镍", m["nmc_niso4_t"], "NiSO4·6H2O", "镍产品", "外售",
        "C按元素折算")
    add("F23", "三元", "硫酸钴", m["nmc_coso4_t"], "CoSO4·7H2O", "钴产品", "外售",
        "C按元素折算")
    add("F24", "三元", "硫酸锰", m["nmc_mnso4_t"], "MnSO4·H2O", "锰产品", "外售",
        "C按元素折算")
    add("F25", "三元", "铜(元素)", m["nmc_cu_t"], "元素Cu", "铜产品", "外售", "A-R1 ANL")
    add("F26", "三元", "铝(元素)", m["nmc_al_t"], "元素Al", "铝产品", "外售", "A-R1 ANL")
    add("F27", "三元", "石墨渣", m["nmc_graphite_t"], "石墨", "一般固废", "处置",
        "C情景拆分")
    add("F28", "三元", "电解液/隔膜", m["nmc_electrolyte_t"], "危废", "危废", "处置",
        "C情景拆分")
    add("F29", "三元", "副产硫酸钠", m["nmc_na2so4_t"], "商品", "副产物", "外售",
        "C按NaOH折算")
    add("F30", "梯次", "梯次模组交付容量", m["reuse_capacity_kwh"], "kWh", "梯次产品",
        "按容量结算", "A-R1 700,495 kWh")
    add("F31", "三废", "LFP废水", m["lfp_wastewater_m3"], "m3", "污水处理", "处理",
        "LS23 §4.2.8")
    add("F32", "三废", "NMC废水", m["nmc_wastewater_m3"], "m3", "污水处理", "处理",
        "C按80%外排")
    return rows


def mass_balance_checks(m):
    """关键质量平衡校核；返回(名称, 左, 右, 相对误差)。"""
    checks = []
    checks.append(("整包分流", R1["feed_pack_t"],
                   m["retained_pack_t"] + m["recycle_pack_t"]))
    checks.append(("再生整包=电芯+非电芯", m["recycle_pack_t"],
                   m["lfp_cell_t"] + m["nmc_cell_t"] + m["pack_nonecell_t"]))
    checks.append(("LFP电芯=黑粉+铜箔+铝箔+其他", m["lfp_cell_t"],
                   m["lfp_powder_t"] + m["lfp_cu_foil_t"] + m["lfp_al_foil_t"]
                   + m["lfp_other_cell_t"]))
    checks.append(("三元电芯=元素产品+其他", m["nmc_cell_t"],
                   m["nmc_element_products_t"] + m["nmc_other_cell_t"]))
    checks.append(("非电芯组分去向", m["pack_nonecell_t"],
                   m["scrap_steel_t"] + m["scrap_al_t"] + m["scrap_cu_t"]
                   + m["scrap_bms_t"] + m["scrap_plastic_t"]))
    checks.append(("LFP Li输入=产品Li+未分配Li", m["lfp_li_input_t"],
                   m["lfp_li_in_crude_t"] + m["lfp_li_unallocated_t"]))
    checks.append(("未分配Li去向", m["lfp_li_unallocated_t"],
                   m["lfp_li_loss_wastewater_t"] + m["lfp_li_loss_residue_t"]
                   + m["lfp_li_loss_fep_t"]))
    out = []
    for name, left, right in checks:
        err = abs(left - right) / left if left else 0.0
        out.append({"check": name, "left": left, "right": right, "rel_error": err,
                    "status": "PASS" if err < 1e-6 else "FAIL"})
    return out


def lfp_wet_stage_balance(m):
    """LFP湿法工序输入输出质量平衡（含外加药剂），差减项为蒸发水与尾气。"""
    inputs = (m["lfp_powder_t"] + m["lfp_acid98_t"] + m["lfp_caustic32_t"]
              + m["lfp_cao92_t"] + m["lfp_h3po4_85_t"] + m["lfp_fe99_t"]
              + m["lfp_co2_t"] + m["lfp_o2_t"])
    outputs = (m["lfp_crude_li_wet_t"] + m["lfp_fep_wet_t"] + m["lfp_alp_t"]
               + m["lfp_na2so4_t"] + m["lfp_sponge_cu_t"] + m["lfp_carbon_residue_t"]
               + m["lfp_caustic_residue_t"] + m["lfp_scrubber_residue_t"]
               + m["lfp_pre_scrubber_residue_t"] + m["lfp_wastewater_m3"])
    return {"inputs_t": inputs, "outputs_t": outputs, "vapor_and_offgas_t": inputs - outputs,
            "closure": outputs / inputs}

def evaluate(m, green_fraction=0.5, feed_mode="value", linkage=0.80,
             li_realization=0.70, metal_realization=0.85, reuse_realization=0.75,
             energy_case="R1", feed_multiplier=1.0, discount_rate=0.07,
             primary="spodumene", recovery_case="base", rd_compliance=False):
    """单工况完整核算：LCOR、净GWP、MAC、联产品抵扣与梯次线。"""
    m = apply_recovery_case(m, recovery_case)
    costs = cost_rows(m, feed_mode, linkage, feed_multiplier, green_fraction)
    revs = revenue_rows(m, li_realization, metal_realization, reuse_realization)
    env = environment_rows(m, green_fraction, energy_case)
    cred = credit_rows(m)

    extra_capex = m.get("compliance_extra_capex", 0.0)
    extra_opex = m.get("compliance_extra_opex", 0.0)
    annuity = (ECON["capex_recycle"] + extra_capex) * crf(discount_rate, R1["operating_years"])
    opex = sum(r["annual_CNY"] for r in costs["rows"]) + extra_opex
    if extra_opex:
        costs["rows"].append({"category": "compliance", "item": "合规改造新增运行费",
                              "quantity": 1, "unit": "项", "unit_price": extra_opex,
                              "annual_CNY": extra_opex, "flow_ref": "compliance",
                              "source": "C情景假设", "status": "情景假设"})
    if energy_case == "conservative":
        ep = ((1 - green_fraction) * price("grid")
              + green_fraction * (price("green") + price("green_adder")))
        extra = (m["nmc_cell_t"] * 561.0 - m["nmc_electricity_kwh"]) * ep
        opex += extra
        costs["rows"].append({"category": "utilities", "item": "NMC公辅电耗补齐",
                              "quantity": m["nmc_cell_t"] * 561.0 - m["nmc_electricity_kwh"],
                              "unit": "kWh", "unit_price": ep, "annual_CNY": extra,
                              "flow_ref": "nmc_electricity", "source": "C情景假设",
                              "status": "情景假设"})
    revenue = revs["total_CNY"]

    rd_base = ECON["rd_social_total"] * (1 - ECON["rd_reuse_share"])
    rd_total = rd_base
    if rd_compliance:
        rd_total = max(rd_base, 0.03 * revenue)
        topup = rd_total - rd_base
        if topup > 0:
            opex += topup
            costs["rows"].append({"category": "rd", "item": "研发补足至收入3%",
                                  "quantity": 1, "unit": "项", "unit_price": topup,
                                  "annual_CNY": topup, "flow_ref": "rd",
                                  "source": "课程政策目标", "status": "政策合规情景"})

    net = annuity + opex - revenue
    lcor = net / m["lce_t"]
    gross = (annuity + opex) / m["lce_t"]
    gwp_gross = env["gwp_kg"] / 1000.0
    gwp_net = gwp_gross - cred["avoided_kg"] / 1000.0
    gwp_per_lce = gwp_net * 1000.0 / m["lce_t"]
    primary_gwp = PRIMARY_GWP["lce_spodumene" if primary == "spodumene" else "lce_saltlake"]
    primary_cost = price("lce")
    denom = (primary_gwp - gwp_per_lce) / 1000.0
    mac = (lcor - primary_cost) / denom if denom > 0 else None
    reuse = reuse_economics(m, feed_mode, linkage, feed_multiplier, reuse_realization,
                            green_fraction)

    v = value_per_t_pack(m)
    feed_value = m["lfp_pack_t"] * v["lfp"] + m["nmc_pack_t"] * v["nmc"]
    be_ratio = (revenue - annuity - (opex - costs["feedstock_CNY"])) / feed_value \
        if feed_value else None

    return {
        "case": {"green_fraction": green_fraction, "feed_mode": feed_mode,
                 "linkage": linkage, "li_realization": li_realization,
                 "metal_realization": metal_realization, "reuse_realization": reuse_realization,
                 "energy_case": energy_case, "discount_rate": discount_rate,
                 "primary": primary, "chemistry": m["chemistry"],
                 "recovery_case": recovery_case, "rd_compliance": rd_compliance},
        "flows": m, "costs": costs, "revenues": revs, "environment": env,
        "credits": cred, "reuse": reuse,
        "annuity_CNY": annuity, "opex_CNY": opex, "revenue_CNY": revenue,
        "net_cost_CNY": net, "lcor_CNY_per_t": lcor, "gross_lcor_CNY_per_t": gross,
        "gwp_gross_t": gwp_gross, "gwp_net_t": gwp_net,
        "gwp_kg_per_t_lce": gwp_per_lce,
        "water_m3_per_t_lce": env["water_l"] / 1000.0 / m["lce_t"],
        "mac_CNY_per_tCO2e": mac,
        "net_cost_per_t_pack_CNY": net / R1["feed_pack_t"],
        "revenue_per_t_pack_CNY": revenue / m["recycle_pack_t"],
        "feed_price_lfp": costs["lfp_price"], "feed_price_nmc": costs["nmc_price"],
        "breakeven_feed_ratio": be_ratio,
        "rd_revenue_fraction": rd_total / revenue if revenue else None,
        "policy_metrics": policy_metrics(m, energy_case,
                                         rd_total / revenue if revenue else None),
    }


def scenario_grid():
    """960组工况：体系×绿电×采购价联动×回收率×实现率×能耗口径。"""
    grid = []
    for (chem, green, linkage, recovery, li_real, met_real, energy) in itertools.product(
            ["NMC622", "NMC811"], [0.0, 0.25, 0.5, 0.75, 1.0],
            [0.50, 0.65, 0.80, 0.90], ["base", "improved"],
            [0.55, 0.70, 0.85], [0.85, 0.95], ["R1", "conservative"]):
        grid.append({"chemistry": chem, "green_fraction": green, "linkage": linkage,
                     "recovery_case": recovery, "li_realization": li_real,
                     "metal_realization": met_real, "energy_case": energy})
    return grid


def pareto_front(points, minimize=("gwp", "lcor")):
    """二维非支配排序；points为dict列表，含gwp/lcor键。"""
    front = []
    for p in points:
        dominated = False
        for q in points:
            if q is p:
                continue
            if all(q[k] <= p[k] for k in minimize) and any(q[k] < p[k] for k in minimize):
                dominated = True
                break
        if not dominated:
            front.append(p)
    return sorted(front, key=lambda p: p["gwp"])


def knee_point(front):
    """归一化理想点欧氏距离最小。"""
    if not front:
        return None
    gs = [p["gwp"] for p in front]
    ls = [p["lcor"] for p in front]
    g0, g1, l0, l1 = min(gs), max(gs), min(ls), max(ls)
    best, best_d = None, float("inf")
    for p in front:
        gn = 0 if g1 == g0 else (p["gwp"] - g0) / (g1 - g0)
        ln = 0 if l1 == l0 else (p["lcor"] - l0) / (l1 - l0)
        d = math.hypot(gn, ln)
        if d < best_d:
            best, best_d = p, d
    return best
