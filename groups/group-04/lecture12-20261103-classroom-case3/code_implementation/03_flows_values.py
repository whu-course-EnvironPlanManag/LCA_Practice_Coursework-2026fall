# -*- coding: utf-8 -*-
"""03_sankey_clean.py —— 用 plotly 重建清晰版桑基图（替代 02_figures.py 的手绘版）
修正原图问题：节点文字被裁切、流带交叉、标签重叠
"""
import os, importlib.util, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("mfa", os.path.join(BASE, "code_implementation", "01_mfa_model.py"))
mfa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mfa)
R = mfa.main()

# ---- 取各流股质量（t/a） ----
cap = R["capacity"]; f_dir = R["f_dir"]; f_ind = R["f_ind"]; f_rec = R["f_rec"]
s1 = R["s1_out"]; s2 = R["s2"]; bp = R["byproducts"]
nmc_bm = R["nmc_blackmass_mass"]; lfp_bm = R["lfp_blackmass_mass"]
nmc_prod = R["nmc_products"]; lfp_prod = R["lfp_products"]

cells_s1 = sum(s1[(c, "cells")][0] for c in ["LFP", "NMC811"])
s1_byproducts = sum(s1[(c, k)][0] for c in ["LFP", "NMC811"] for k in ["pack_structure", "electronics_wiring"])
echelon = cap * (f_dir + f_ind)
s1_in = cap * f_rec

nmc_bm_mass_raw = s2[("NMC811", "cathode")][0]
lfp_bm_mass_raw = s2[("LFP", "cathode")][0]
nmc_graphite = s2[("NMC811", "graphite")][0]
lfp_graphite = s2[("LFP", "graphite")][0]
nmc_elec = s2[("NMC811", "electrolyte")][0]
lfp_elec = s2[("LFP", "electrolyte")][0]

s2_byprod = sum(s2[(c, k)][0] for c in ["LFP", "NMC811"] for k in ["Cu", "Al", "separator", "cell_case"])
s2_vent = sum(s2[(c, "electrolyte_loss")][0] for c in ["LFP", "NMC811"])

print(json.dumps({
    "echelon": round(echelon, 1), "s1_in": round(s1_in, 1),
    "cells_s1": round(cells_s1, 1), "s1_byproducts": round(s1_byproducts, 1),
    "nmc_bm_total": round(nmc_bm, 1), "lfp_bm_total": round(lfp_bm, 1),
    "nmc_cathode": round(nmc_bm_mass_raw, 1), "lfp_cathode": round(lfp_bm_mass_raw, 1),
    "nmc_graphite": round(nmc_graphite, 1), "lfp_graphite": round(lfp_graphite, 1),
    "nmc_elec": round(nmc_elec, 1), "lfp_elec": round(lfp_elec, 1),
    "s2_byprod": round(s2_byprod, 1), "s2_vent": round(s2_vent, 1),
    "nmc_prod_li2co3": round(nmc_prod["Li2CO3"], 1),
    "nmc_prod_salt": round(nmc_prod["mixed_NiCoMn_salt"], 1),
    "lfp_regen": round(lfp_prod["regen_LFP_cathode"], 1),
    "lfp_li2co3": round(lfp_prod["Li2CO3_LFP"], 1),
    "lfp_fepo4": round(lfp_prod["FePO4"], 1),
}, ensure_ascii=False, indent=1))
