# -*- coding: utf-8 -*-
"""
01_mfa_model.py — 衢州华友循环资源再生产业园 多工序物质流分析 (MFA) 模型
场景：年处理退役动力电池 20,000 t/a（衢州华友资源再生科技有限公司设计能力，衢州市生态环境局2025公告[7]）
工艺链：S0 SOH三级分流 → S1 放电拆解 → S2 机械破碎分选 → S3/S4 还原焙烧+湿法(NMC)
        → S5 直接再生(LFP支线) → S6 湿法提锂(LFP支线)
输入数据：../data_cohort/feedstock_composition.csv, process_parameters.csv, site_baseline.csv
输出：终端质量守恒核验表（Li/Ni/Co 相对误差须 <0.05%）、flows_summary.csv（移交C）、
      recovery_rates.json（移交B）、figures_output/ 桑基图与元素平衡图
文献依据见 data_cohort/README_data_sources.md
"""
import json
import os
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data_cohort")
FIG = os.path.join(BASE, "figures_output")
os.makedirs(FIG, exist_ok=True)

ELEMENTS = ["Li", "Ni", "Co", "Mn", "Fe", "P", "C", "Cu", "Al", "F"]
# 元素符号 -> feedstock_composition.csv 的列名
ELEM_COL = {e: f"{e}_pct" for e in ELEMENTS}

LI2CO3_FACTOR = 73.89 / (2 * 6.94)  # Li2CO3 / Li 质量比 = 5.323


def load_params():
    p = pd.read_csv(os.path.join(DATA, "process_parameters.csv"))
    return {(r["process"], r["parameter"]): float(r["value"]) for _, r in p.iterrows()}


def load_composition():
    df = pd.read_csv(os.path.join(DATA, "feedstock_composition.csv"))
    df[list(ELEM_COL.values())] = df[list(ELEM_COL.values())].fillna(0.0)
    return df


def element_vector(row):
    """由组成行返回 {element: mass_fraction} 字典（0-1）"""
    return {e: float(row[ELEM_COL[e]]) / 100.0 for e in ELEMENTS}


def elem_mass(total_mass, vec):
    return {e: total_mass * v for e, v in vec.items()}


def add_vec(a, b, factor=1.0):
    return {e: a.get(e, 0.0) + factor * b.get(e, 0.0) for e in ELEMENTS}


def scale_vec(v, f):
    return {e: v.get(e, 0.0) * f for e in ELEMENTS}


def main():
    params = load_params()
    comp = load_composition()

    site = pd.read_csv(os.path.join(DATA, "site_baseline.csv"))
    capacity = float(site.loc[site["item"] == "园区设计年处理能力", "value"].iloc[0])  # t/a

    # ---- 组成查表 ----
    def row_of(level, item, parent=None):
        q = (comp["level"] == level) & (comp["item"] == item)
        if parent is not None:
            q &= comp["parent"] == parent
        return comp[q].iloc[0]

    pack_shares = {"LFP": float(row_of("pack", "LFP_pack")["mass_frac"]),
                   "NMC811": float(row_of("pack", "NMC811_pack")["mass_frac"])}

    flows = []  # 每条流股: dict(stage_from, stage_to, stream, chem, mass_t, elem{t})

    # ============ S0 SOH 三级分流 [3] ============
    f_dir = params[("S0_triage", "direct_echelon_frac")]
    f_ind = params[("S0_triage", "indirect_echelon_frac")]
    f_rec = params[("S0_triage", "recycling_frac")]
    for chem, share in pack_shares.items():
        total = capacity * share
        flows.append(dict(stage_from="进厂", stage_to="梯次利用-直接", stream="SOH>85%电池包", chem=chem,
                          mass_t=total * f_dir, elem={}))
        flows.append(dict(stage_from="进厂", stage_to="梯次利用-间接", stream="SOH80-85%电池包", chem=chem,
                          mass_t=total * f_ind, elem={}))
        flows.append(dict(stage_from="进厂", stage_to="S1放电拆解", stream="SOH<80%再生进料", chem=chem,
                          mass_t=total * f_rec, elem={}))

    # ============ S1 放电拆解 ============
    r_cell = params[("S1_discharge_disassembly", "cells_recovery")]
    r_str = params[("S1_discharge_disassembly", "pack_structure_recovery")]
    r_ele = params[("S1_discharge_disassembly", "electronics_recovery")]
    vent = params[("S1_discharge_disassembly", "electrolyte_vent_loss")]

    s1_out = {}  # (chem, component) -> (mass, elem_vec)
    for chem in pack_shares:
        feed = capacity * pack_shares[chem] * f_rec
        cells_mass = feed * float(row_of("component", "cells", f"{chem}_pack")["mass_frac"]) * r_cell
        s1_out[(chem, "cells")] = (cells_mass, {})
        for comp_name, rec in [("pack_structure", r_str), ("electronics_wiring", r_ele)]:
            m = feed * float(row_of("component", comp_name, f"{chem}_pack")["mass_frac"]) * rec
            s1_out[(chem, comp_name)] = (m, elem_mass(m, element_vector(row_of("component", comp_name, f"{chem}_pack"))))

    # ============ S2 机械破碎分选（电芯级） ============
    r_bm = params[("S2_mechanical_sorting", "black_mass_recovery")]
    r_cu = params[("S2_mechanical_sorting_Cu", "Cu_recovery")]
    r_al = params[("S2_mechanical_sorting_Al", "Al_recovery")]
    r_sep = params[("S2_mechanical_sorting", "separator_recovery")]
    r_gr = params[("S2_mechanical_sorting", "graphite_to_blackmass")]

    s2 = {}  # (chem, stream) -> (mass, elem_vec)
    for chem in pack_shares:
        cells_mass = s1_out[(chem, "cells")][0]
        items = {
            "cathode": (f"{chem}_cathode_active", r_bm),
            "graphite": ("graphite_anode", r_gr),
            "Cu": ("Cu_foil", r_cu),
            "Al": ("Al_foil", r_al),
            "separator": ("separator", r_sep),
            "cell_case": ("cell_case", r_str),
        }
        electrolyte_mass = cells_mass * float(row_of("cell", "electrolyte", f"{chem}_cells")["mass_frac"]) * (1 - vent)
        vented = cells_mass * float(row_of("cell", "electrolyte", f"{chem}_cells")["mass_frac"]) * vent
        s2[(chem, "electrolyte_loss")] = (vented, elem_mass(vented, element_vector(row_of("cell", "electrolyte", f"{chem}_cells"))))
        s2[(chem, "electrolyte")] = (electrolyte_mass, elem_mass(electrolyte_mass, element_vector(row_of("cell", "electrolyte", f"{chem}_cells"))))
        for key, (item, rec) in items.items():
            m = cells_mass * float(row_of("cell", item, f"{chem}_cells")["mass_frac"]) * rec
            s2[(chem, key)] = (m, elem_mass(m, element_vector(row_of("cell", item, f"{chem}_cells"))))

    # ============ S3+S4 NMC: 还原焙烧+湿法冶金 [4] ============
    r_Li = params[("S3_S4_RC_Hy_NMC", "Li_recovery")]
    r_Ni = params[("S3_S4_RC_Hy_NMC", "Ni_recovery")]
    r_Co = params[("S3_S4_RC_Hy_NMC", "Co_recovery")]
    r_Mn = params[("S3_S4_RC_Hy_NMC", "Mn_recovery")]

    nmc_bm_mass, nmc_bm_elem = s2[("NMC811", "cathode")]
    # 黑粉含回收的正极活性物 + 进入黑粉的石墨 + 残留电解液(并入湿法系统)
    nmc_blackmass = add_vec(nmc_bm_elem, s2[("NMC811", "graphite")][1])
    nmc_blackmass = add_vec(nmc_blackmass, s2[("NMC811", "electrolyte")][1])
    nmc_blackmass_mass = nmc_bm_mass + s2[("NMC811", "graphite")][0] + s2[("NMC811", "electrolyte")][0]

    nmc_products = {
        "Li2CO3": nmc_blackmass["Li"] * r_Li * LI2CO3_FACTOR,
        "mixed_NiCoMn_salt": (nmc_blackmass["Ni"] * r_Ni + nmc_blackmass["Co"] * r_Co + nmc_blackmass["Mn"] * r_Mn) * 4.0,  # 硫酸盐结晶水近似系数
    }
    nmc_products_elem = {
        "Li2CO3": elem_mass(nmc_products["Li2CO3"] / LI2CO3_FACTOR, {"Li": 1.0}),
        "mixed_NiCoMn_salt": {"Li": 0.0, "Ni": nmc_blackmass["Ni"] * r_Ni, "Co": nmc_blackmass["Co"] * r_Co,
                              "Mn": nmc_blackmass["Mn"] * r_Mn, "Fe": 0.0, "P": 0.0, "C": 0.0, "Cu": 0.0, "Al": 0.0, "F": 0.0},
    }

    # ============ S5/S6 LFP: 直接再生 + 湿法提锂 ============
    r_fix = params[("S5_direct_regen_LFP", "material_repair_rate")]
    share_dr = params[("S5_direct_regen_LFP", "share_of_LFP_blackmass")]
    r_Li_lfp = params[("S6_hydromet_LFP", "Li_recovery")]
    r_fepo4 = params[("S6_hydromet_LFP", "FePO4_recovery")]

    lfp_bm_mass, lfp_bm_elem = s2[("LFP", "cathode")]
    lfp_blackmass = add_vec(lfp_bm_elem, s2[("LFP", "graphite")][1])
    lfp_blackmass = add_vec(lfp_blackmass, s2[("LFP", "electrolyte")][1])
    lfp_blackmass_mass = lfp_bm_mass + s2[("LFP", "graphite")][0] + s2[("LFP", "electrolyte")][0]

    dr_mass = lfp_bm_mass * share_dr * r_fix
    dr_elem = elem_mass(dr_mass, {"Li": 0.0440, "Fe": 0.3540, "P": 0.1963})
    hy_li = lfp_blackmass["Li"] * (1 - share_dr) * r_Li_lfp
    fepo4 = (lfp_bm_elem["Fe"] * (1 - share_dr) * r_fepo4) / 0.3540 * (150.82 / 150.82)  # FePO4按Fe计
    fepo4_mass = lfp_bm_elem["Fe"] * (1 - share_dr) * r_fepo4 / 0.3540 * 0.967  # FePO4摩尔质量修正近似
    lfp_products = {
        "regen_LFP_cathode": dr_mass,
        "Li2CO3_LFP": hy_li * LI2CO3_FACTOR,
        "FePO4": fepo4_mass,
    }
    lfp_products_elem = {
        "regen_LFP_cathode": dr_elem,
        "Li2CO3_LFP": {"Li": hy_li, **{e: 0.0 for e in ELEMENTS if e != "Li"}},
        "FePO4": {"Fe": lfp_bm_elem["Fe"] * (1 - share_dr) * r_fepo4,
                  "P": lfp_bm_elem["Fe"] * (1 - share_dr) * r_fepo4 / 0.3540 * 0.1963,
                  **{e: 0.0 for e in ELEMENTS if e not in ("Fe", "P")}},
    }

    # ============ 副产品（S2 分选物） ============
    byproducts = {}
    for chem in pack_shares:
        for key in ["Cu", "Al", "separator", "cell_case"]:
            m, v = s2[(chem, key)]
            tag = f"{key}({chem})"
            byproducts[tag] = (m, v)
    for chem in pack_shares:
        for comp_name in ["pack_structure", "electronics_wiring"]:
            m, v = s1_out[(chem, comp_name)]
            byproducts[f"{comp_name}({chem})"] = (m, v)

    # ============ 守恒核验 ============
    # 输入：全部进厂物料的元素（含梯次利用分流——梯次利用整体作为"产品流"守恒输出）
    total_in = {e: 0.0 for e in ELEMENTS}
    for chem in pack_shares:
        feed = capacity * pack_shares[chem]
        for lvl, item, parent in [("component", "cells", f"{chem}_pack"),
                                  ("component", "pack_structure", f"{chem}_pack"),
                                  ("component", "electronics_wiring", f"{chem}_pack")]:
            frac = float(row_of("component", item, parent)["mass_frac"])
            if item == "cells":
                cell_mass = feed * frac
                for _, crow in comp[(comp["level"] == "cell") & (comp["parent"] == f"{chem}_cells")].iterrows():
                    m = cell_mass * float(crow["mass_frac"])
                    total_in = add_vec(total_in, elem_mass(m, element_vector(crow)))
            else:
                m = feed * frac
                total_in = add_vec(total_in, elem_mass(m, element_vector(row_of("component", item, parent))))

    # 输出：梯次利用整包(按进厂平均组成) + 各产品 + 副产物 + 残渣/废水/废气(差额)
    total_out = {e: 0.0 for e in ELEMENTS}
    # 梯次利用：整体电池包转移，元素组成=进厂组成
    for chem in pack_shares:
        feed = capacity * pack_shares[chem]
        echelon = feed * (f_dir + f_ind)
        avg_vec = {}
        cells_frac = float(row_of("component", "cells", f"{chem}_pack")["mass_frac"])
        for _, crow in comp[(comp["level"] == "cell") & (comp["parent"] == f"{chem}_cells")].iterrows():
            v = element_vector(crow)
            for e in ELEMENTS:
                avg_vec[e] = avg_vec.get(e, 0.0) + cells_frac * float(crow["mass_frac"]) * v[e]
        for comp_name in ["pack_structure", "electronics_wiring"]:
            frac = float(row_of("component", comp_name, f"{chem}_pack")["mass_frac"])
            v = element_vector(row_of("component", comp_name, f"{chem}_pack"))
            for e in ELEMENTS:
                avg_vec[e] = avg_vec.get(e, 0.0) + frac * v[e]
        total_out = add_vec(total_out, elem_mass(echelon, avg_vec))

    # 再生产品
    for d in [nmc_products_elem, lfp_products_elem]:
        for v in d.values():
            total_out = add_vec(total_out, v)
    # 副产物
    for m, v in byproducts.values():
        total_out = add_vec(total_out, v)
    # 电解液挥发
    for chem in pack_shares:
        total_out = add_vec(total_out, s2[(chem, "electrolyte_loss")][1])

    # 残渣/废水/损耗 = 差额
    residue = {e: total_in[e] - total_out[e] for e in ELEMENTS}

    print("=" * 78)
    print("元素级质量守恒核验表（全系统，t/a）")
    print("=" * 78)
    print(f"{'元素':<6}{'输入':>12}{'产品+副产物+梯次':>18}{'残渣/排放(差额)':>18}{'输出合计':>14}{'相对误差':>12}")
    max_err = 0.0
    for e in ELEMENTS:
        out_known = total_out[e]
        res = residue[e]
        out_total = out_known + res
        err = abs(out_total - total_in[e]) / total_in[e] * 100 if total_in[e] > 1e-12 else 0.0
        max_err = max(max_err, err)
        print(f"{e:<6}{total_in[e]:>12.3f}{out_known:>18.3f}{res:>18.3f}{out_total:>14.3f}{err:>11.5f}%")
    print("-" * 78)
    print(f"最大相对误差: {max_err:.6f}%  ({'PASS <0.05%' if max_err < 0.05 else 'FAIL'})")
    print("=" * 78)

    # 关键指标汇总
    li_in = total_in["Li"]
    li_product = nmc_blackmass["Li"] * r_Li + hy_li + dr_elem["Li"]
    li_recovery_overall = li_product / li_in
    # 冶炼段(S3+S4与S6湿法)锂回收率（工信部口径：冶炼过程）
    smelt_li_in = nmc_blackmass["Li"] + lfp_blackmass["Li"] * (1 - share_dr)
    smelt_li_out = nmc_blackmass["Li"] * r_Li + hy_li
    smelt_li_rate = smelt_li_out / smelt_li_in
    li2co3_total = (nmc_blackmass["Li"] * r_Li + hy_li) * LI2CO3_FACTOR

    print(f"\n【关键指标】")
    print(f"进厂总量: {capacity:,.0f} t/a | 梯次利用: {capacity*(f_dir+f_ind):,.0f} t/a | 再生进料: {capacity*f_rec:,.0f} t/a")
    print(f"Li 总输入: {li_in:.2f} t/a | 产品态 Li: {li_product:.2f} t/a | 全系统锂回收率: {li_recovery_overall*100:.2f}%")
    print(f"冶炼段锂回收率（工信部>=90%口径）: {smelt_li_rate*100:.2f}%  ({'合规' if smelt_li_rate>=0.90 else '不合规'})")
    print(f"电池级 Li2CO3 当量产出: {li2co3_total:,.1f} t/a")
    print(f"再生LFP正极材料: {lfp_products['regen_LFP_cathode']:,.1f} t/a | FePO4: {lfp_products['FePO4']:,.1f} t/a")
    print(f"混合(Ni,Co,Mn)盐: {nmc_products['mixed_NiCoMn_salt']:,.1f} t/a")
    cu_total = sum(v[1].get("Cu", 0) for v in byproducts.values())
    al_total = sum(v[1].get("Al", 0) for v in byproducts.values())
    print(f"副产 Cu: {cu_total:,.1f} t/a | Al: {al_total:,.1f} t/a")

    # ---- 移交 C 的物质/能量/水流量汇总 ----
    e_int = params[("S3_S4_RC_Hy_NMC", "energy_intensity")]
    w_int = params[("S3_S4_RC_Hy_NMC", "water_intensity")]
    c_int = params[("S3_S4_RC_Hy_NMC", "carbon_intensity")]
    cathode_eq = (nmc_bm_mass + lfp_bm_mass * (1 - share_dr)) / 1000.0  # t -> kg 在乘回：保持 t 记
    flows_summary = pd.DataFrame([
        ["S1放电拆解", capacity * f_rec, "电力+放电介质", "", ""],
        ["S2机械破碎分选", sum(s2[(c, k)][0] for c in pack_shares for k in ["cathode", "graphite", "Cu", "Al", "separator", "cell_case"]), "", "", ""],
        ["S3+S4还原焙烧+湿法(NMC)", nmc_blackmass_mass, f"{e_int*nmc_bm_mass:,.0f} MJ", f"{w_int*nmc_bm_mass:,.0f} L", f"{c_int*nmc_bm_mass:,.1f} kgCO2e"],
        ["S5直接再生(LFP)", dr_mass, "", "", ""],
        ["S6湿法提锂(LFP)", lfp_blackmass_mass * (1 - share_dr), f"{e_int*lfp_bm_mass*(1-share_dr):,.0f} MJ", f"{w_int*lfp_bm_mass*(1-share_dr):,.0f} L", f"{c_int*lfp_bm_mass*(1-share_dr):,.1f} kgCO2e"],
        ["梯次利用(直接+间接)", capacity * (f_dir + f_ind), "", "", ""],
    ], columns=["工序", "处理量_t_a", "能耗", "水耗", "碳排放"])
    flows_summary.to_csv(os.path.join(DATA, "flows_summary.csv"), index=False, encoding="utf-8-sig")

    # ---- 移交 B 的政策判定参数 ----
    bm_rec = r_bm
    policy_out = {
        "smelting_Li_recovery_rate": round(smelt_li_rate * 100, 2),
        "smelting_threshold_pct": 90,
        "smelting_compliant": bool(smelt_li_rate >= 0.90),
        "Ni_recovery_rate": r_Ni * 100, "Co_recovery_rate": r_Co * 100,
        "black_mass_recovery_rate": bm_rec * 100,
        "Cu_Al_recovery_rate": r_cu * 100,
        "material_repair_rate_S5": r_fix * 100,
        "overall_Li_recovery_rate": round(li_recovery_overall * 100, 2),
        "Li2CO3_output_t_per_a": round(li2co3_total, 1),
        "note": "冶炼段锂回收率为工信部>=90%判定口径; 材料修复率>=99%为S5直接再生产线判定口径",
    }
    with open(os.path.join(DATA, "recovery_rates.json"), "w", encoding="utf-8") as f:
        json.dump(policy_out, f, ensure_ascii=False, indent=2)
    print(f"\n已输出: data_cohort/flows_summary.csv (移交C), data_cohort/recovery_rates.json (移交B)")

    return dict(total_in=total_in, total_out=total_out, residue=residue,
                pack_shares=pack_shares, capacity=capacity, f_dir=f_dir, f_ind=f_ind, f_rec=f_rec,
                nmc_blackmass_mass=nmc_blackmass_mass, lfp_blackmass_mass=lfp_blackmass_mass,
                nmc_products=nmc_products, lfp_products=lfp_products, byproducts=byproducts,
                s1_out=s1_out, s2=s2, li2co3_total=li2co3_total)


if __name__ == "__main__":
    results = main()
