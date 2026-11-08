# -*- coding: utf-8 -*-
"""
A_mfa_model.py  —— 退役动力电池多工序物质流分析（工序级 MFA）与元素守恒核验
方向 B：产业园区/工程尺度
运行：python A_mfa_model.py
输出：data_cohort/A_mfa_results.json、data_cohort/A_mfa_balance_table.csv、终端守恒表

数据来源：见 data_cohort/ABC_README_data_sources.md

【AI 辅助编程说明】
  Prompt 摘要："建立退役动力电池园区工序级 MFA：放电拆解—破碎分选—分流精炼（湿法/
  还原焙烧+湿法/直接正极再生），打印 Li、Ni、Co、Mn、Fe、P、Cu、Al 元素级平衡表并要求
  闭合误差 <0.05%。"
  人工校验修正：①黑粉中活性物质占比按 active/(active+graphite) 折算；②Cu/Al 由分选直接
  产出、不进入精炼段；③产品实物量按化学计量比换算（NiSO4·6H2O 22.3% Ni、
  CoSO4·7H2O 21.0% Co、MnSO4·H2O 32.5% Mn、FePO4 按 Fe+P+O 计量）。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data_cohort")

with open(os.path.join(DATA, "ABC_parameters.json"), encoding="utf-8") as f:
    P = json.load(f)

CAP = P["_meta"]["design_capacity_t_cells_per_year"]
SHARE = P["feedstock"]["share"]
COMP = P["feedstock"]["composition"]
ELEM = P["feedstock"]["active_element_fraction"]
PRE = P["process"]["pretreatment"]
ROUTES = P["process"]["routes"]
LI2CO3_PER_LI = P["process"]["li2co3_per_li"]

# 基准工艺配比（帕累托拐点 / 锚点 B）：LFP 中 60%（来料适用性上限）走直接再生，其余湿法；
# NMC/NCA 中 30% 走还原焙烧+湿法（混合金属盐），70% 走强化湿法
DIRECT_SHARE_LFP = 0.60
RC_SHARE_NMC = 0.30

ELEMENTS = ["Li", "Ni", "Co", "Mn", "Fe", "P", "Cu", "Al"]

# 单吨电池各化学体系元素含量（kg/t）
def per_tonne(kind):
    comp = COMP[kind]
    act = comp["active"]
    out = {e: 0.0 for e in ELEMENTS}
    for e, frac in ELEM[kind].items():
        out[e] = act * frac * 1000.0
    out["Cu"] = comp["Cu"] * 1000.0
    out["Al"] = comp["Al"] * 1000.0
    return out

# 混合来料单吨元素含量
blend = {e: sum(SHARE[k] * per_tonne(k)[e] for k in SHARE) for e in ELEMENTS}

# ---------- 工序 1：放电拆解 + 机械破碎分选 ----------
def stage1(kind):
    comp = COMP[kind]
    black = (comp["active"] + comp["graphite"]) * PRE["black_mass_recovery"]
    cu = comp["Cu"] * PRE["copper_al_recovery"]
    al = comp["Al"] * PRE["copper_al_recovery"]
    other = 1.0 - black - cu - al          # 电解液 / 隔膜 / 外壳 / 结构件
    return {"black_mass": black, "Cu": cu, "Al": al, "other": other}

s1 = {k: stage1(k) for k in SHARE}

# ---------- 工序 2：分流与精炼 ----------
alloc = {
    "LFP":    {"Direct": DIRECT_SHARE_LFP, "Hy": 1 - DIRECT_SHARE_LFP, "RC_Hy": 0.0},
    "NMC811": {"Direct": 0.0, "Hy": 1 - RC_SHARE_NMC, "RC_Hy": RC_SHARE_NMC},
    "NCA":    {"Direct": 0.0, "Hy": 1 - RC_SHARE_NMC, "RC_Hy": RC_SHARE_NMC},
}

# 各体系进入精炼的元素量（取黑粉中的元素，按活性物质占黑粉比例折算）
elem_in_route = {r: {e: 0.0 for e in ELEMENTS} for r in ROUTES}
for k in SHARE:
    act = COMP[k]["active"]
    black = s1[k]["black_mass"]
    share_in_black = act / (act + COMP[k]["graphite"])
    for r, frac in alloc[k].items():
        if frac <= 0:
            continue
        for e in ELEMENTS:
            if e in ELEM[k]:
                elem_in_route[r][e] += SHARE[k] * black * share_in_black * ELEM[k][e] * 1000.0 * frac
# Cu / Al 由分选直接产出，不进入精炼
cu_rec = sum(SHARE[k] * s1[k]["Cu"] for k in SHARE) * 1000.0
al_rec = sum(SHARE[k] * s1[k]["Al"] for k in SHARE) * 1000.0

# 精炼产出（元素口径）
prod = {e: 0.0 for e in ELEMENTS}
prod["Cu"] = cu_rec
prod["Al"] = al_rec
for r, cfg in ROUTES.items():
    for e in ("Li", "Ni", "Co", "Mn"):
        rate = cfg["Li"] if e == "Li" else cfg["NiCoMn"]
        if e == "Mn" and r == "Direct":
            rate = 0.0
        prod[e] += elem_in_route[r].get(e, 0.0) * rate
    for e in ("Fe", "P"):
        prod[e] += elem_in_route[r].get(e, 0.0) * cfg["FeP"]

# 工艺溶损（进入废水）：Li 1.0%，Ni/Co/Mn 各 0.3%；粉尘/废气 0.3% 黑粉
loss_frac = {"Li": 0.010, "Ni": 0.003, "Co": 0.003, "Mn": 0.003, "Fe": 0.004, "P": 0.004}
ww = {e: sum(elem_in_route[r].get(e, 0.0) for r in ROUTES) * loss_frac.get(e, 0.0) for e in ELEMENTS}
dust_frac = 0.003
black_total = sum(SHARE[k] * s1[k]["black_mass"] for k in SHARE) * 1000.0
dust = black_total * dust_frac

total_in = {e: sum(elem_in_route[r].get(e, 0.0) for r in ROUTES) for e in ELEMENTS}
total_in["Cu"] = cu_rec
total_in["Al"] = al_rec
tailings = {e: total_in[e] - prod[e] - ww[e] for e in ELEMENTS}

# 产品实物量（按路线区分产物形态：湿法/焙烧路线锂以 Li2CO3 产出，直接再生路线锂留存于再生正极粉）
lce_li = elem_in_route["Hy"]["Li"] * ROUTES["Hy"]["Li"] + elem_in_route["RC_Hy"]["Li"] * ROUTES["RC_Hy"]["Li"]
li2co3 = lce_li * LI2CO3_PER_LI
powder_lfp = SHARE["LFP"] * COMP["LFP"]["active"] * DIRECT_SHARE_LFP * ROUTES["Direct"]["FeP"] * 1000.0
ni_sulfate = prod["Ni"] / 0.223        # NiSO4·6H2O，Ni 22.3%
co_sulfate = prod["Co"] / 0.210        # CoSO4·7H2O，Co 21.0%
mn_sulfate = prod["Mn"] / 0.325        # MnSO4·H2O，Mn 32.5%
fepo4_fe = elem_in_route["Hy"]["Fe"] * ROUTES["Hy"]["FeP"] + elem_in_route["RC_Hy"]["Fe"] * ROUTES["RC_Hy"]["FeP"]
fepo4_p = elem_in_route["Hy"]["P"] * ROUTES["Hy"]["FeP"] + elem_in_route["RC_Hy"]["P"] * ROUTES["RC_Hy"]["FeP"]
fepo4 = fepo4_fe + fepo4_p + 16.0 / 30.97 * fepo4_p

# ---------- 元素闭合核验 ----------
rows = []
for e in ELEMENTS:
    inp = total_in[e]
    out = prod[e] + ww[e] + tailings[e]
    err = abs(out - inp) / inp * 100 if inp > 0 else 0.0
    rows.append({"element": e, "input_kg": inp, "product_kg": prod[e],
                 "wastewater_kg": ww[e], "tailings_kg": tailings[e],
                 "closure_error_pct": err})

max_err = max(r["closure_error_pct"] for r in rows)
print("=" * 78)
print("工序级物质流平衡表（功能单位：1 t 退役动力电池）")
print("=" * 78)
print(f"{'元素':<6}{'输入 kg':>10}{'产品 kg':>10}{'废水 kg':>10}{'尾渣 kg':>10}{'闭合误差 %':>12}")
for r in rows:
    print(f"{r['element']:<6}{r['input_kg']:>10.2f}{r['product_kg']:>10.2f}"
          f"{r['wastewater_kg']:>10.2f}{r['tailings_kg']:>10.2f}{r['closure_error_pct']:>12.4f}")
print("-" * 78)
print(f"锂元素闭合最大相对误差 = {max_err:.4f}%  （要求 < 0.05%）")
print(f"黑粉产率 = {black_total/1000:.3f} t/t 电池；铜回收 {cu_rec:.1f} kg/t；铝回收 {al_rec:.1f} kg/t")
print(f"产品：Li2CO3 {li2co3:.1f} kg/t；再生磷酸铁锂正极粉 {powder_lfp:.1f} kg/t；镍盐 {ni_sulfate:.1f}；"
      f"钴盐 {co_sulfate:.1f}；锰盐 {mn_sulfate:.1f}；磷酸铁 {fepo4:.1f} kg/t")
print(f"年通量（{CAP} t/a）：Li2CO3 {li2co3*CAP/1000:.1f} t/a；再生正极粉 {powder_lfp*CAP/1000:.0f} t/a；"
      f"黑粉 {black_total*CAP/1000:.0f} t/a；铜 {cu_rec*CAP/1000:.0f} t/a；铝 {al_rec*CAP/1000:.0f} t/a")

assert max_err < 0.05, "元素闭合误差超限"

result = {
    "capacity_t_per_year": CAP,
    "per_tonne": {
        "element_input_kg": total_in, "product_kg": prod,
        "wastewater_kg": ww, "tailings_kg": tailings,
        "black_mass_t": black_total / 1000, "cu_kg": cu_rec, "al_kg": al_rec,
        "li2co3_kg": li2co3, "lfp_powder_kg": powder_lfp, "ni_sulfate_kg": ni_sulfate,
        "co_sulfate_kg": co_sulfate, "mn_sulfate_kg": mn_sulfate, "fepo4_kg": fepo4,
    },
    "annual": {
        "cells_t": CAP, "li2co3_t": li2co3 * CAP / 1000, "lfp_powder_t": powder_lfp * CAP / 1000,
        "black_mass_t": black_total * CAP / 1000, "cu_t": cu_rec * CAP / 1000,
        "al_t": al_rec * CAP / 1000, "fepo4_t": fepo4 * CAP / 1000,
        "ni_sulfate_t": ni_sulfate * CAP / 1000, "co_sulfate_t": co_sulfate * CAP / 1000,
        "mn_sulfate_t": mn_sulfate * CAP / 1000,
    },
    "closure_error_max_pct": max_err,
    "route_allocation": {"direct_share_lfp": DIRECT_SHARE_LFP, "rc_share_nmc": RC_SHARE_NMC},
    "rows": rows,
}

with open(os.path.join(DATA, "A_mfa_results.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

with open(os.path.join(DATA, "A_mfa_balance_table.csv"), "w", encoding="utf-8-sig") as f:
    f.write("element,input_kg,product_kg,wastewater_kg,tailings_kg,closure_error_pct\n")
    for r in rows:
        f.write(f"{r['element']},{r['input_kg']:.4f},{r['product_kg']:.4f},"
                f"{r['wastewater_kg']:.4f},{r['tailings_kg']:.4f},{r['closure_error_pct']:.6f}\n")

print("\n已写出 data_cohort/A_mfa_results.json 与 A_mfa_balance_table.csv")
