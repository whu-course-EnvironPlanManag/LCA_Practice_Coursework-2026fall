"""
05_lca.py — 模块3b：全生命周期 GWP/水耗核算（摇篮到坟墓）
【AI 辅助编程提示词记录】
Prompt: "LCA 脚本：功能单位 1 kWh 电池全寿命周期交付电量，核算收集/拆解/再生 GWP 和水耗，对比原生卤水/硬岩基准。"
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

def calculate_lca(route, chemistry, green_power_ratio=0.3, mass_t=50000.0):
    proc = {r["process"]: r for r in load_csv("process_parameters.csv")}[route]
    chem = {r["chemistry"]: r for r in load_csv("battery_chemistry.csv")}[chemistry]
    grid_cf = 0.581 * (1 - green_power_ratio) + 0.020 * green_power_ratio
    energy_mj = float(proc["energy_MJ_per_kg_material"])
    electricity_kwh = energy_mj / 3.6
    water = float(proc["water_L_per_kg_material"])
    gwp_process = float(proc["gwp_kgCO2e_per_kg_material"])
    transport_gwp = 0.062 * 0.1
    disassembly_gwp = 0.05
    power_gwp = electricity_kwh * grid_cf
    total_gwp = transport_gwp + disassembly_gwp + gwp_process + power_gwp
    water_total = water + 0.01
    # 注：与原生锂的对比采用 LCE 口径（文献4：再生锂 6.1 vs 硬岩锂 14.5 kg CO2e/kg LCE，减排58%），
    # 与本表每 kg 电池处理量口径分母不同，不在表内混算（旧版按每kg电池折算原生锂的做法口径错误，已移除）
    return {"route": route, "chemistry": chemistry, "green_power_ratio": green_power_ratio,
        "gwp_kgCO2e_per_kg": round(total_gwp, 4), "water_L_per_kg": round(water_total, 4)}

def run_lca():
    results = []
    for route in ["hydrometallurgy", "pyrometallurgy", "direct_recycling"]:
        for chem in ["LFP", "NMC811"]:
            for gpr in [0.0, 0.3, 0.6, 1.0]:
                results.append(calculate_lca(route, chem, gpr))
    out = os.path.join(RESULTS_DIR, "lca_results.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    print("=" * 80); print("全生命周期 LCA 核算"); print("=" * 80)
    print(f"{'工艺':<18}{'化学':<8}{'绿电比':>8}{'GWP(kgCO2e/kg)':>18}{'水耗(L/kg)':>12}")
    print("-" * 70)
    for r in results:
        print(f"{r['route']:<18}{r['chemistry']:<8}{r['green_power_ratio']:>8.0%}{r['gwp_kgCO2e_per_kg']:>18.4f}{r['water_L_per_kg']:>12.4f}")
    print("\n注：与原生硬岩锂对比采用 LCE 口径（文献4，减排 58%），见报告 §6.2 结论①")
    print(f"\n输出: {out}"); print("=" * 80)
    return results

if __name__ == "__main__":
    run_lca()
