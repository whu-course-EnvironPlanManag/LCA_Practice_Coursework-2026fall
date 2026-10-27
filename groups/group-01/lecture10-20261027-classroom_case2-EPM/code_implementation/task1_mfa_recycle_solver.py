# -*- coding: utf-8 -*-
"""任务1：反应/分离/循环求解、独立元素校验及10万吨/年基准放大。

输入：同组 data_cohort/mfa_reaction_recycle_balance.csv；参数出处：
background_engineering_docs.md 第1、2节；lecture10_task_manual.md 任务1。

重要边界：CSV 是存在矛盾的工程定额，不能同时满足全部化学计量约束。
本脚本分别报告原始定额审计与理想化学计量模型，不修改或拟合原数据。
模型沿用手册碳利用率公式的纯组分折算口径：S01/S02/S12 总质量分别
视为 CO2/H2/CH3OH；不将其误称为按 CSV 杂质组成还原的真实工况。
采用稳态、无其他反应、甲醇/水完全冷凝、干气等比例分流假设。
缺少动力学/选择性数据，不能分别识别三个反应的实际反应进度。
模型只求两个独立的净反应坐标；工程净水、氧气和电耗仍按原始定额放大。

用法：python task1_mfa_recycle_solver.py
      python task1_mfa_recycle_solver.py --self-test
      python task1_mfa_recycle_solver.py --strict-data  # 数据不自洽时退出码2
仅用 Python 标准库；可从任意工作目录运行，不静默使用内置替代数据。
"""

import argparse
import copy
import csv
import math
from pathlib import Path
import sys
import unittest

# 分子量/原子量沿用任务1原框架，单位 kg/kmol；不另行调参。
MW_CO2, MW_H2, MW_CH3OH = 44.010, 2.016, 32.042
MW_H2O, MW_CO, MW_O2 = 18.015, 28.010, 31.999
M_C, M_H, M_O = 12.011, 1.008, 15.999
PRODUCT_MEOH_KG = 1000.0
TOLERANCE = 1e-4  # 任务要求：相对误差严格小于0.01%
SPECIES = ("CO2", "H2", "CH3OH", "H2O", "CO", "O2")
MW = dict(zip(SPECIES, (MW_CO2, MW_H2, MW_CH3OH, MW_H2O, MW_CO, MW_O2)))
ATOMS = {
    "CO2": (1, 0, 2), "H2": (0, 2, 0), "CH3OH": (1, 4, 1),
    "H2O": (0, 2, 1), "CO": (1, 0, 1), "O2": (0, 0, 2),
}
# 工程背景2.1的三条反应；列顺序同SPECIES，正数生成，负数消耗。
REACTIONS = ((-1, -3, 1, 1, 0, 0), (-1, -1, 0, 1, 1, 0),
             (0, -2, 1, 0, -1, 0))
WT_COLUMNS = {"CO2": "co2_wt_pct", "H2": "h2_wt_pct",
              "CH3OH": "meoh_wt_pct", "H2O": "h2o_wt_pct", "O2": "o2_wt_pct"}
MASS_COLUMN = "mass_flow_per_ton_product_kg"
MOLAR_COLUMN = "molar_flow_per_ton_product_kmol"


def find_data_file(filename="mfa_reaction_recycle_balance.csv"):
    """只定位同组数据，避免因启动目录不同而误读其他组文件。"""
    path = Path(__file__).resolve().parent.parent / "data_cohort" / filename
    if not path.is_file():
        raise FileNotFoundError(f"同组输入数据不存在：{path}")
    return path


def load_streams(csv_file=None):
    path = Path(csv_file) if csv_file is not None else find_data_file()
    numeric = [MASS_COLUMN, MOLAR_COLUMN, *WT_COLUMNS.values(), "other_inerts_wt_pct"]
    streams = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"stream_id", *numeric} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV缺少字段：{sorted(missing)}")
        for row in reader:
            sid = row["stream_id"]
            if sid in streams:
                raise ValueError(f"重复物流编号：{sid}")
            for column in numeric:
                value = float(row[column])
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"{sid}.{column}必须为非负有限数")
                if column.endswith("wt_pct") and value > 100:
                    raise ValueError(f"{sid}.{column}不能超过100%")
                row[column] = value
            streams[sid] = row
    required = {f"S{i:02d}" for i in range(1, 14)}
    if required - streams.keys():
        raise ValueError(f"缺少物流：{sorted(required - streams.keys())}")
    for sid in ("S01", "S02", "S12"):
        if streams[sid][MASS_COLUMN] <= 0 or streams[sid][MOLAR_COLUMN] <= 0:
            raise ValueError(f"{sid}质量流量和摩尔流量必须为正")
    return streams


def element_masses(flow):
    """由各组分kmol及化学式独立求C/H/O质量，不用闭合差定义尾气。"""
    return {element: sum(flow.get(s, 0.0) * ATOMS[s][i] * weight for s in SPECIES)
            for i, (element, weight) in enumerate(zip(("C", "H", "O"), (M_C, M_H, M_O)))}


def add_flows(*flows):
    return {s: sum(flow.get(s, 0.0) for flow in flows) for s in SPECIES}


def check_elements(inflow, outflow):
    incoming, outgoing = element_masses(inflow), element_masses(outflow)
    result = {}
    for element in ("C", "H", "O"):
        absolute = abs(incoming[element] - outgoing[element])
        relative = absolute / incoming[element] if incoming[element] else (0.0 if absolute == 0 else math.inf)
        result.update({f"{element}_in": incoming[element], f"{element}_out": outgoing[element],
                       f"{element}_err": relative})
    result["passed"] = all(result[f"{e}_err"] < TOLERANCE for e in ("C", "H", "O"))
    return result


def source_composition_flow(row):
    """仅转换CSV明确列出的组分；other_inerts未给化学式，绝不分配成CO。"""
    return {s: row[MASS_COLUMN] * row[column] / 100 / MW[s]
            for s, column in WT_COLUMNS.items()}


def audit_reference(streams):
    """检查原始数据而不归一化组成、不修正流量、不强制96%/3.8。"""
    m = lambda sid: streams[sid][MASS_COLUMN]
    n = lambda sid: streams[sid][MOLAR_COLUMN]
    eta = (m("S12") / MW_CH3OH) / (m("S01") / MW_CO2)
    mass_ratio = m("S06") / (m("S01") + m("S02"))
    molar_ratio = n("S06") / (n("S01") + n("S02"))
    issues = []
    for sid, row in streams.items():
        total = sum(row[c] for c in (*WT_COLUMNS.values(), "other_inerts_wt_pct"))
        if abs(total - 100) > 1e-6:
            issues.append(f"{sid}质量百分数之和为{total:.4f}%，不能作为已闭合组成。")
    if not math.isclose(eta, 0.96, rel_tol=0, abs_tol=1e-10):
        issues.append(f"手册纯组分口径碳利用率为{eta:.8%}，不严格等于96.0%。")
    if not math.isclose(molar_ratio, 3.8, rel_tol=0, abs_tol=1e-10):
        issues.append(f"表内摩尔循环比为{molar_ratio:.6f}:1，不等于3.8:1。")
    if not (math.isclose(m("S06"), 0.99 * m("S10"), rel_tol=0, abs_tol=1e-8)
            and math.isclose(m("S11"), 0.01 * m("S10"), rel_tol=0, abs_tol=1e-8)):
        issues.append(f"99%分流预测回流{0.99*m('S10'):.4f} kg、尾气{0.01*m('S10'):.4f} kg；"
                      f"CSV分别为{m('S06'):.4f}、{m('S11'):.4f} kg（存在取整差异）。")
    co2_in = m("S07") * streams["S07"]["co2_wt_pct"] / 100
    co2_out = m("S08") * streams["S08"]["co2_wt_pct"] / 100
    measured_conversion = (co2_in - co2_out) / co2_in if co2_in else math.nan
    if not math.isclose(measured_conversion, 0.25, rel_tol=0, abs_tol=1e-10):
        issues.append(f"S07/S08组成推得CO2单程转化率{measured_conversion:.6%}，不等于25%。")
    incoming = add_flows(*(source_composition_flow(streams[s]) for s in ("S01", "S02")))
    outgoing = add_flows(*(source_composition_flow(streams[s]) for s in ("S11", "S12", "S13")))
    elements = check_elements(incoming, outgoing)
    unknown_in = sum(m(s) * streams[s]["other_inerts_wt_pct"] / 100 for s in ("S01", "S02"))
    unknown_out = sum(m(s) * streams[s]["other_inerts_wt_pct"] / 100 for s in ("S11", "S12", "S13"))
    if unknown_in > 0 or unknown_out > 0:
        issues.append(f"合成系统其他组分输入{unknown_in:.6f} kg、输出{unknown_out:.6f} kg，"
                      "缺少化学式；原始CSV不能认证完整C/H/O守恒。")
    if not elements["passed"]:
        issues.append("原始CSV已知组分的C/H/O相对误差存在超过0.01%的项。")
    # 只审计拓扑总质量；相等不代表元素守恒。
    topology = {
        "混合器": m("S01") + m("S02") + m("S06") - m("S07"),
        "反应器": m("S07") - m("S08"),
        "分离器": m("S08") - m("S09") - m("S10"),
        "分流器": m("S10") - m("S06") - m("S11"),
        "精馏": m("S09") - m("S12") - m("S13"),
        "电解进水混合": m("S03") + m("S13") - m("S04"),
    }
    for name, residual in topology.items():
        if abs(residual) > 1e-8:
            issues.append(f"{name}总质量不闭合：残差{residual:.6f} kg/t。")
    return {"eta_carbon": eta, "recycle_ratio_mass": mass_ratio,
            "recycle_ratio_molar": molar_ratio, "elements_known_only": elements,
            "topology_mass_residuals_kg": topology, "issues": issues,
            "certified": not issues and elements["passed"]}


def solve_mfa_balance(single_pass_conv=0.250, purge_ratio=0.010, streams=None):
    """求稳态干气循环，保留原框架主要返回键；各物流以kmol/t表示。

    原方程：CO2_in=CO2_fresh+(1-p)*CO2_out；
    CO2_out=(1-X)*CO2_in；a=甲醇产量；b=净CO产量；
    CO2消耗=a+b，H2消耗=3a+b，H2O生成=a+b。
    H2_out=H2_fresh+(1-p)*H2_out-(3a+b)；
    CO_out=(1-p)*CO_out+b。三反应满足R3=R1-R2，因此
    a=xi1+xi3、b=xi2-xi3，不假设或伪造各反应的实际进度。
    固定X和p后，以上稳态方程可代数消元，直接求解。
    """
    if not math.isfinite(single_pass_conv) or not 0 < single_pass_conv <= 1:
        raise ValueError("单程转化率必须在(0, 1]内")
    if not math.isfinite(purge_ratio) or not 0 < purge_ratio <= 1:
        raise ValueError("驰放分流比必须在(0, 1]内；零驰放下净CO无稳态出口")
    streams = load_streams() if streams is None else streams
    x, p = single_pass_conv, purge_ratio
    fresh = {"CO2": streams["S01"][MASS_COLUMN] / MW_CO2,
             "H2": streams["S02"][MASS_COLUMN] / MW_H2}
    a = streams["S12"][MASS_COLUMN] / MW_CH3OH
    co2_in = fresh["CO2"] / (x + p * (1 - x))
    co2_out = (1 - x) * co2_in
    b = x * co2_in - a
    h2_out = (fresh["H2"] - 3 * a - b) / p
    if b < 0 or h2_out < 0:
        raise ValueError("给定进料/产量/X/p无非负稳态解；不能强行保持产量并截断负流量")
    offgas = {"CO2": co2_out, "H2": h2_out, "CO": b / p}
    recycle = {s: (1 - p) * value for s, value in offgas.items()}
    purge = {s: p * value for s, value in offgas.items()}
    inlet = add_flows(fresh, recycle)
    delta = {s: a * REACTIONS[0][i] + b * REACTIONS[1][i] for i, s in enumerate(SPECIES)}
    outlet = {s: inlet[s] + delta[s] for s in SPECIES}
    product = {"CH3OH": a}
    water = {"H2O": a + b}
    mass = lambda flow: sum(value * MW[s] for s, value in flow.items())
    m_fresh = mass(fresh)
    flows = {"fresh": fresh, "reactor_in": inlet, "reactor_out": outlet,
             "offgas": offgas, "recycle": recycle, "purge": purge,
             "product": product, "water": water}
    if any(not math.isfinite(v) or v < 0 for f in flows.values() for v in f.values()):
        raise ValueError("求解出现非有限或负组分流量，当前参数不能认证")
    result = {
        "basis": "手册纯组分折算、完全冷凝、稳态干气模型；非CSV全组成工况",
        "flows_kmol": flows, "reference_streams": streams,
        "single_pass_conv": x, "purge_ratio": p,
        "net_meoh_extent_kmol": a, "net_co_extent_kmol": b,
        "m_co2_fresh_kg": mass({"CO2": fresh["CO2"]}),
        "m_h2_fresh_kg": mass({"H2": fresh["H2"]}), "m_meoh_out_kg": mass(product),
        "m_h2o_gen_kg": mass(water), "m_gas_recycle_kg": mass(recycle),
        "m_gas_purge_kg": mass(purge), "eta_carbon": a / fresh["CO2"],
        "recycle_ratio_mass": mass(recycle) / m_fresh,
        "recycle_ratio_molar": sum(recycle.values()) / sum(fresh.values()),
        "n_co2_fresh_kmol": fresh["CO2"], "n_h2_fresh_kmol": fresh["H2"],
        # 原框架MW_CO2与原子量和差0.001 kg/kmol；保留并显示舍入质量残差。
        "mass_residual_kg": m_fresh - mass(add_flows(product, water, purge)),
    }
    return result


def verify_element_conservation(res):
    """独立核查合成系统边界及每个单元；尾气来自求解的各组分流量。"""
    f = res["flows_kmol"]
    result = check_elements(f["fresh"], add_flows(f["product"], f["water"], f["purge"]))
    result["units"] = {
        "混合器": check_elements(add_flows(f["fresh"], f["recycle"]), f["reactor_in"]),
        "反应器": check_elements(f["reactor_in"], f["reactor_out"]),
        "冷凝精馏": check_elements(f["reactor_out"], add_flows(f["offgas"], f["product"], f["water"])),
        "分流器": check_elements(f["offgas"], add_flows(f["recycle"], f["purge"])),
    }
    result["passed"] = result["passed"] and all(v["passed"] for v in result["units"].values())
    return result


def scale_up_park_level(res, annual_meoh_ton=100000.0):
    """按CSV工程定额放大；非化学计量模型预测，不补造电解排水/杂质参数。"""
    if not math.isfinite(annual_meoh_ton) or annual_meoh_ton <= 0:
        raise ValueError("年甲醇产能必须为正有限数")
    streams = res["reference_streams"]
    # 由S12的实际功能单位归一化，避免把kg/t与t/y混用。
    batches = annual_meoh_ton * 1000 / streams["S12"][MASS_COLUMN]
    annual = lambda sid: streams[sid][MASS_COLUMN] * batches / 1000
    # 工程背景2.3：52 kWh/kg H2 + 捕集255 + 循环压缩155 + 精馏120。
    power = streams["S02"][MASS_COLUMN] * 52.0 + 255.0 + 155.0 + 120.0
    return {"basis": "原始CSV工程定额，尚未通过全组成元素守恒认证",
            "annual_meoh_capacity_ton": annual_meoh_ton,
            "annual_co2_ton": annual("S01"), "annual_green_h2_ton": annual("S02"),
            "annual_crude_water_ton": annual("S13"), "annual_total_water_ton": annual("S04"),
            "annual_makeup_water_ton": annual("S03"), "annual_oxygen_ton": annual("S05"),
            "annual_purge_gas_ton": annual("S11"), "annual_recycle_gas_ton": annual("S06"),
            "annual_power_kwh": power * batches, "annual_power_b_kwh": power * batches / 1e8}


def print_elements(result):
    for element in ("C", "H", "O"):
        print(f"  {element}: 输入{result[element+'_in']:.6f} kg | "
              f"输出{result[element+'_out']:.6f} kg | 误差{result[element+'_err']:.8%}")


class MFATests(unittest.TestCase):
    """检验化学式、稳态方程、独立校验敏感性及边界工况。"""

    def test_reaction_atoms_and_dependency(self):
        for reaction in REACTIONS:
            atoms = element_masses(dict(zip(SPECIES, reaction)))
            for value in atoms.values():
                self.assertAlmostEqual(value, 0.0, places=12)
        self.assertEqual(tuple(a - b for a, b in zip(*REACTIONS[:2])), REACTIONS[2])

    def test_steady_state_and_conversion(self):
        for x, p in ((0.25, 0.01), (0.25, 0.004), (0.5, 0.01), (1.0, 1.0)):
            result = solve_mfa_balance(x, p)
            flows = result["flows_kmol"]
            self.assertTrue(verify_element_conservation(result)["passed"])
            self.assertAlmostEqual((flows["reactor_in"]["CO2"] - flows["reactor_out"]["CO2"])
                                   / flows["reactor_in"]["CO2"], x)
            for s in SPECIES:
                self.assertAlmostEqual(flows["reactor_out"][s],
                                       add_flows(flows["offgas"], flows["product"], flows["water"])[s])
            for s, value in flows["offgas"].items():
                self.assertAlmostEqual(flows["purge"][s], p * value)
                self.assertAlmostEqual(flows["recycle"][s], (1 - p) * value)
            self.assertLess(abs(result["mass_residual_kg"]) /
                            (result["m_co2_fresh_kg"] + result["m_h2_fresh_kg"]), TOLERANCE)

    def test_independent_check_detects_damage(self):
        result = copy.deepcopy(solve_mfa_balance())
        result["flows_kmol"]["purge"]["CO2"] += 1.0
        check = verify_element_conservation(result)
        self.assertFalse(check["passed"])
        self.assertGreater(check["C_err"], TOLERANCE)
        self.assertGreater(check["O_err"], TOLERANCE)

    def test_invalid_and_infeasible_parameters(self):
        for x, p in ((0, 0.01), (1.1, 0.01), (0.25, 0), (0.25, -0.01),
                     (math.nan, 0.01), (0.25, math.inf), (0.25, 0.045)):
            with self.assertRaises(ValueError):
                solve_mfa_balance(x, p)

    def test_reference_is_not_falsely_certified(self):
        streams = load_streams()
        audit = audit_reference(streams)
        self.assertFalse(audit["certified"])
        self.assertFalse(audit["elements_known_only"]["passed"])
        self.assertAlmostEqual(audit["recycle_ratio_molar"], 365.12 / (32.33 + 98.21))
        self.assertNotAlmostEqual(audit["eta_carbon"], 0.96, places=4)
        self.assertTrue(all(abs(v) < 1e-8 for v in audit["topology_mass_residuals_kg"].values()))

    def test_scale_and_missing_file(self):
        result = solve_mfa_balance()
        park = scale_up_park_level(result)
        expected = {"annual_co2_ton": 142300, "annual_green_h2_ton": 19800,
                    "annual_makeup_water_ton": 138500, "annual_oxygen_ton": 158400,
                    "annual_power_kwh": 1082600000}
        for key, value in expected.items():
            self.assertAlmostEqual(park[key], value)
            self.assertAlmostEqual(scale_up_park_level(result, 50000)[key], value / 2)
        with self.assertRaises(ValueError):
            scale_up_park_level(result, 0)
        with self.assertRaises(FileNotFoundError):
            find_data_file("__nonexistent_mfa_input__.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="执行内置物理与程序自检")
    parser.add_argument("--strict-data", action="store_true", help="原始数据不能认证时返回退出码2")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(MFATests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    streams = load_streams()
    audit = audit_reference(streams)
    result = solve_mfa_balance(streams=streams)
    check = verify_element_conservation(result)
    print("任务1：MFA稳态循环求解与工程定额审计")
    print(f"数据源：{find_data_file()}")
    print("\n【CSV工程基准；数值直接读取/计算，未经强制标定】")
    print(f"  循环气{streams['S06'][MASS_COLUMN]:.4f} kg/t；"
          f"质量循环比{audit['recycle_ratio_mass']:.6f}:1；摩尔循环比{audit['recycle_ratio_molar']:.6f}:1")
    print(f"  手册纯组分口径碳利用率{audit['eta_carbon']:.8%}；严格等于96%：否")
    print("  各拓扑节点总质量残差(kg/t)：", audit["topology_mass_residuals_kg"])
    for issue in audit["issues"]:
        print("  [数据差异]", issue)
    print("  原始CSV已知组分C/H/O核查（未识别其他组分，不代表完整元素平衡）：")
    print_elements(audit["elements_known_only"])
    print("\n【理想化学计量求解；与上方工程定额分开】")
    print("  口径：", result["basis"])
    print(f"  CO2单程转化率{result['single_pass_conv']:.2%}；驰放{result['purge_ratio']:.2%}")
    for key, label in (("m_co2_fresh_kg", "新鲜CO2"), ("m_h2_fresh_kg", "新鲜H2"),
                       ("m_meoh_out_kg", "甲醇"), ("m_h2o_gen_kg", "反应生成水"),
                       ("m_gas_recycle_kg", "循环干气"), ("m_gas_purge_kg", "驰放干气")):
        print(f"  {label}: {result[key]:.6f} kg/t")
    print(f"  质量循环比{result['recycle_ratio_mass']:.6f}:1；"
          f"摩尔循环比{result['recycle_ratio_molar']:.6f}:1；碳利用率{result['eta_carbon']:.8%}")
    print(f"  净CO生成{result['net_co_extent_kmol']:.8f} kmol/t；各反应进度不能单独识别。")
    print("  物流组分(kmol/t)：")
    for name, flow in result["flows_kmol"].items():
        print(f"    {name}: " + ", ".join(f"{s}={v:.8f}" for s, v in flow.items() if v != 0))
    print("  独立元素守恒校验：")
    print_elements(check)
    for name, unit in check["units"].items():
        print(f"    {name}: {'通过' if unit['passed'] else '不通过'}")
    mass_relative_error = abs(result["mass_residual_kg"]) / (result["m_co2_fresh_kg"] + result["m_h2_fresh_kg"])
    print(f"  原框架分子量舍入导致总质量残差{result['mass_residual_kg']:.8f} kg/t，"
          f"相对误差{mass_relative_error:.8%}。")
    if mass_relative_error >= TOLERANCE:
        raise ArithmeticError("模型总质量误差超出0.01%")
    if not check["passed"]:
        raise ArithmeticError("化学计量模型元素守恒误差超出0.01%，拒绝通过")
    print("  模型边界及各单元C/H/O相对误差均<0.01%；该结论不适用于原始CSV。")
    park = scale_up_park_level(result)
    print("\n【10万吨/年原始工程定额放大】")
    print("  口径：", park["basis"])
    for key, label in (("annual_co2_ton", "年需捕集CO2"), ("annual_green_h2_ton", "年需电解绿氢"),
                       ("annual_total_water_ton", "电解总进水"), ("annual_crude_water_ton", "精馏水回用"),
                       ("annual_makeup_water_ton", "新鲜脱盐水净补水"), ("annual_oxygen_ton", "副产纯氧")):
        print(f"  {label}: {park[key]:,.2f} t/年")
    print(f"  全厂综合用电: {park['annual_power_kwh']:,.0f} kWh/年 = {park['annual_power_b_kwh']:.3f}亿kWh/年")
    print("\n结论：理想模型求解/守恒通过；原始资料有矛盾，无法同时认证4640、3.8和严格96%。")
    return 2 if args.strict_data and not audit["certified"] else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        sys.exit(main())
    except (OSError, ValueError, ArithmeticError) as error:
        print(f"[错误] {error}", file=sys.stderr)
        sys.exit(1)
