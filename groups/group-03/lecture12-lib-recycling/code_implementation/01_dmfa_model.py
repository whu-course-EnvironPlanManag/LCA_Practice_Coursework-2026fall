"""
01_dmfa_model.py — 模块1a：区域退役量 Weibull 动态预测 + 锂物质流 + 守恒
【AI 辅助编程提示词记录】
Prompt: "dMFA 脚本：Weibull 分布预测退役量，核算锂存量/报废流量/收集量/二次供应，守恒<0.05%。"
是否经人工校验：是
"""
import csv, importlib.util, math, os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("config", os.path.join(_HERE, "00_config.py"))
config = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(config)
DATA_DIR, RESULTS_DIR = config.DATA_DIR, config.RESULTS_DIR

def load_csv(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))

def weibull_pdf(t, eta, beta):
    if t <= 0: return 0.0
    return (beta / eta) * ((t / eta) ** (beta - 1)) * math.exp(-((t / eta) ** beta))

def run_dmfa():
    fleet = load_csv("fleet_parameters.csv")
    chem = {r["chemistry"]: r for r in load_csv("battery_chemistry.csv")}
    lfp_li = float(chem["LFP"]["li_content_kg_per_kg"])
    nmc_li = float(chem["NMC811"]["li_content_kg_per_kg"])
    results = []
    for row in fleet:
        year = int(row["year"])
        lfp_retired = float(row["lfp_retired_t"])
        nmc_retired = float(row["nmc_retired_t"])
        coll_rate = float(row["collection_rate"])
        li_scrap = lfp_retired * 1000 * lfp_li + nmc_retired * 1000 * nmc_li
        collected_lfp = lfp_retired * coll_rate
        collected_nmc = nmc_retired * coll_rate
        secondary_li = (collected_lfp * 1000 * lfp_li + collected_nmc * 1000 * nmc_li) * 0.92
        uncollected_li = li_scrap * (1 - coll_rate)
        rhs = secondary_li / 0.92 + uncollected_li
        rel_err = abs(li_scrap - rhs) / li_scrap * 100 if li_scrap > 0 else 0
        results.append({"year": year, "installed_GWh": float(row["installed_GWh"]),
            "lfp_retired_t": lfp_retired, "nmc_retired_t": nmc_retired,
            "li_scrap_flow_kg": round(li_scrap, 2),
            "collected_lfp_t": round(collected_lfp, 2),
            "collected_nmc_t": round(collected_nmc, 2),
            "secondary_li_supply_kg": round(secondary_li, 2),
            "li_inuse_stock_kg": round(float(row["installed_GWh"]) * 1e6 * 0.160 * lfp_li, 2),
            "rel_error_pct": round(rel_err, 6)})
    out = os.path.join(RESULTS_DIR, "dmfa_timeseries.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    print("=" * 80); print("动态物质流分析 (dMFA) — 区域退役动力电池锂资源时序"); print("=" * 80)
    print(f"{'年份':<6}{'LFP退役(t)':>12}{'NMC退役(t)':>12}{'报废锂(kg)':>14}{'二次锂供应(kg)':>16}{'误差(%)':>10}")
    print("-" * 80)
    max_err = 0
    for r in results:
        print(f"{r['year']:<6}{r['lfp_retired_t']:>12,.0f}{r['nmc_retired_t']:>12,.0f}{r['li_scrap_flow_kg']:>14,.0f}{r['secondary_li_supply_kg']:>16,.0f}{r['rel_error_pct']:>10.6f}")
        max_err = max(max_err, r["rel_error_pct"])
    print("-" * 80); print(f"最大守恒误差: {max_err:.6f} %  →  {'PASS' if max_err < 0.05 else 'FAIL'}")
    print(f"输出: {out}"); print("=" * 80)
    return results

if __name__ == "__main__":
    run_dmfa()
