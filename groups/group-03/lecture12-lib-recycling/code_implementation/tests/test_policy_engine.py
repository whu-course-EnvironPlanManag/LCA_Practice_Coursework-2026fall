"""
tests/test_policy_engine.py — 政策引擎单元测试（3 组工况）
工况：①不达标粗放回收（全 FAIL）②常规达标湿法（PASS）③绿电+直接再生（PASS 且激励更高）
"""
import importlib.util, os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _PARENT = os.path.dirname(_HERE)
_spec = importlib.util.spec_from_file_location("policy_engine", os.path.join(_PARENT, "03_policy_engine.py"))
pe = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pe)
evaluate_compliance = pe.evaluate_compliance

def test_case1():
    case = {"li_recovery_rate": 0.75, "ni_recovery_rate": 0.85, "co_recovery_rate": 0.88,
        "mn_recovery_rate": 0.80, "electrode_powder_recovery": 0.90, "fluorine_fixation_rate": 0.95,
        "energy_kgce_per_t": 3500, "wastewater_recycle_rate": 0.70, "recycled_li_content": 0.02, "eu_year": 2031}
    r = evaluate_compliance(case)
    assert not r.is_compliant and len(r.violations) >= 3
    print(f"[PASS] 工况1: 不达标粗放回收 -> {len(r.violations)} 项违反")

def test_case2():
    case = {"li_recovery_rate": 0.92, "ni_recovery_rate": 0.98, "co_recovery_rate": 0.98,
        "mn_recovery_rate": 0.98, "electrode_powder_recovery": 0.985, "fluorine_fixation_rate": 0.996,
        "energy_kgce_per_t": 1800, "wastewater_recycle_rate": 0.92, "recycled_li_content": 0.08, "eu_year": 2031,
        "gwp_reduction_tCO2e": 50000, "water_saving_m3": 80000, "li2co3_output_t": 15000,
        "lfp_mass_t": 35000, "nmc_mass_t": 35000}
    r = evaluate_compliance(case)
    assert r.is_compliant and r.financial_adjustment_CNY > 0
    print(f"[PASS] 工况2: 常规达标湿法 -> 合规, 激励 CNY {r.financial_adjustment_CNY:,.0f}")

def test_case3():
    case = {"li_recovery_rate": 0.99, "ni_recovery_rate": 0.99, "co_recovery_rate": 0.99,
        "mn_recovery_rate": 0.98, "electrode_powder_recovery": 0.992, "fluorine_fixation_rate": 0.998,
        "energy_kgce_per_t": 1200, "wastewater_recycle_rate": 0.95, "recycled_li_content": 0.14, "eu_year": 2036,
        "gwp_reduction_tCO2e": 95000, "water_saving_m3": 150000, "li2co3_output_t": 18000,
        "lfp_mass_t": 35000, "nmc_mass_t": 35000}
    r = evaluate_compliance(case)
    case2 = {"li_recovery_rate": 0.92, "ni_recovery_rate": 0.98, "co_recovery_rate": 0.98,
        "mn_recovery_rate": 0.98, "electrode_powder_recovery": 0.985, "fluorine_fixation_rate": 0.996,
        "energy_kgce_per_t": 1800, "wastewater_recycle_rate": 0.92, "recycled_li_content": 0.08, "eu_year": 2031,
        "gwp_reduction_tCO2e": 50000, "water_saving_m3": 80000, "li2co3_output_t": 15000,
        "lfp_mass_t": 35000, "nmc_mass_t": 35000}
    r2 = evaluate_compliance(case2)
    assert r.is_compliant and r.financial_adjustment_CNY > r2.financial_adjustment_CNY
    print(f"[PASS] 工况3: 绿电直接再生 -> 合规, 激励 CNY {r.financial_adjustment_CNY:,.0f} (高于湿法)")

if __name__ == "__main__":
    print("=" * 60); print("政策引擎单元测试"); print("=" * 60)
    results = []
    for fn in [test_case1, test_case2, test_case3]:
        try: fn(); results.append(True)
        except AssertionError as e: print(f"[FAIL] {fn.__name__}: {e}"); results.append(False)
    print("=" * 60); print(f"结果: {sum(results)}/{len(results)} 通过"); print("=" * 60)
    sys.exit(0 if all(results) else 1)
