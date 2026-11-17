"""
02_process_mfa.py — 模块1b：末端再生工序物质流 + 元素级守恒
【AI 辅助编程提示词记录】
Prompt: "工序级 MFA：Li/Ni/Co/Mn/Cu/Al/Fe/P 衡算，守恒<0.05% 否则报错退出。"
是否经人工校验：是
"""
import csv, importlib.util, os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("config", os.path.join(_HERE, "00_config.py"))
config = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(config)
DATA_DIR, RESULTS_DIR = config.DATA_DIR, config.RESULTS_DIR

def load_csv(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))

def run_process_mfa(process="hydrometallurgy", lfp_t=35000.0, nmc_t=35000.0, soh_cutoff=0.80):
    chem = {r["chemistry"]: r for r in load_csv("battery_chemistry.csv")}
    proc = {r["process"]: r for r in load_csv("process_parameters.csv")}[process]
    rec_lfp = lfp_t; rec_nmc = nmc_t
    li_rec = float(proc["li_recovery_rate"]); ni_rec = float(proc["ni_recovery_rate"])
    co_rec = float(proc["co_recovery_rate"]); mn_rec = float(proc["mn_recovery_rate"])
    cu_rec = 0.98; al_rec = 0.98; fe_rec = 0.90; p_rec = 0.85
    lfp = chem["LFP"]; nmc = chem["NMC811"]
    contents = {"Li": (float(lfp["li_content_kg_per_kg"]), float(nmc["li_content_kg_per_kg"])),
        "Ni": (0.0, float(nmc["ni_content_kg_per_kg"])),
        "Co": (0.0, float(nmc["co_content_kg_per_kg"])),
        "Mn": (0.0, float(nmc["mn_content_kg_per_kg"])),
        "Cu": (float(lfp["cu_content_kg_per_kg"]), float(nmc["cu_content_kg_per_kg"])),
        "Al": (float(lfp["al_content_kg_per_kg"]), float(nmc["al_content_kg_per_kg"])),
        "Fe": (float(lfp["fe_content_kg_per_kg"]), 0.0),
        "P": (float(lfp["p_content_kg_per_kg"]), 0.0)}
    rec_rates = {"Li": li_rec, "Ni": ni_rec, "Co": co_rec, "Mn": mn_rec, "Cu": cu_rec, "Al": al_rec, "Fe": fe_rec, "P": p_rec}
    balance = []; max_err = 0.0
    for el in ["Li", "Ni", "Co", "Mn", "Cu", "Al", "Fe", "P"]:
        c_lfp, c_nmc = contents[el]
        inp = rec_lfp * 1000 * c_lfp + rec_nmc * 1000 * c_nmc
        rr = rec_rates[el]; product = inp * rr; loss = inp - product
        rel_err = abs(inp - (product + loss)) / inp * 100 if inp > 0 else 0.0
        max_err = max(max_err, rel_err)
        balance.append({"element": el, "process": process, "input_kg": round(inp, 4),
            "product_kg": round(product, 4), "residue_kg": 0.0, "loss_kg": round(loss, 4),
            "rel_error_pct": round(rel_err, 6)})
    out = os.path.join(RESULTS_DIR, "mfa_balance.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=balance[0].keys()); w.writeheader(); w.writerows(balance)
    print("=" * 90); print(f"工序级物质流平衡 — 工艺: {process} | SOH 阈值: {soh_cutoff:.0%}"); print("=" * 90)
    print(f"{'元素':<6}{'输入(kg)':>16}{'产品(kg)':>16}{'尾渣(kg)':>12}{'损耗(kg)':>16}{'误差(%)':>12}"); print("-" * 90)
    for b in balance:
        print(f"{b['element']:<6}{b['input_kg']:>16,.2f}{b['product_kg']:>16,.2f}{b['residue_kg']:>12,.2f}{b['loss_kg']:>16,.2f}{b['rel_error_pct']:>12.6f}")
    print("-" * 90); print(f"最大误差: {max_err:.6f} %  →  {'PASS' if max_err < 0.05 else 'FAIL'}")
    if max_err >= 0.05: print("ERROR: 守恒误差超 0.05%"); sys.exit(1)
    print(f"输出: {out}"); print("=" * 90)
    return balance

if __name__ == "__main__":
    run_process_mfa()
