"""命令行：--extract-yearbook、--plot-yearbook、--check-inputs、--run、--self-test。

AI提示词：实现湖北方向A的可复现数据流，缺少历史队列/报价/道路距离时阻止
正式模拟；500组以上真实输入驱动情景、政策剔除、前沿、锚点与工程一致性输出。
自动校验已经实现，输入取值与适用边界仍需组员人工复核。无需联网运行模型。
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import sys

import common
from common import DATA, OUTPUT, ROOT, ELEMENTS, InputError, number, source, write_csv, write_json
from input_data import TABLES, check_readiness, load_inputs
from dmfa_model import run_dmfa
from network_model import solve_network
from lca_tea import LI_TO_LCE, evaluate_inventory, find_procurement_quote, compare_pathway
from policy_engine import evaluate_policy, financial_adjustments
from decision import pareto_frontier


def calculate_mfa(bundle, pathway, collection_override=None):
    cfg, tables, cohorts, collections, diversions, recoveries, opening = bundle
    collections = dict(collections)
    if collection_override is not None:
        for key in collections:
            if key[0] >= cfg["planning_start_year"]:
                collections[key] = collection_override
    if pathway["id"] not in recoveries:
        raise InputError(f"缺少工艺{pathway['id']}的总有效回收率")
    return run_dmfa(cohorts, tables["material_parameters.csv"], cfg["model_start_year"],
                    cfg["planning_end_year"], collections, diversions, recoveries[pathway["id"]], opening)


def evaluate_case(bundle, pathway, rows, green_share, lce_price, baseline, network_cache):
    cfg, tables, *_ = bundle
    year = cfg["decision_year"]
    annual = [row for row in rows if row["year"] == year]
    tonnes = sum(row["refining_input_t"] for row in annual)
    if tonnes <= 0:
        raise InputError("代表年没有精炼进料，不能计算LCOR或指定产能")
    if pathway.get("lithium_output_kind") != "battery_grade_LCE":
        raise InputError("该工艺产物不是电池级碳酸锂；须另设同功能产品/直接修复比较模型，不能冒用LCE售价和原生LCE基准")
    energy = [r for r in tables["energy_factors.csv"] if int(r["year"]) == year]
    if len(energy) != 1:
        raise InputError("代表年电力因子须唯一且有证据，不自动跨年外推")
    chemistry_t = defaultdict(float)
    supply_by_city = defaultdict(lambda: defaultdict(float))
    for row in annual:
        chemistry_t[row["chemistry"]] += row["refining_input_t"]
        supply_by_city[row["city"]]["recycling"] += row["refining_input_t"]
        supply_by_city[row["city"]]["echelon"] += row["echelon_input_t"]
    if sum(r["echelon_input_t"]+r["echelon_return_t"] for r in annual) > 0:
        if pathway.get("echelon_return_location_assumption") != "original_city":
            raise InputError("有梯次物流，须明确返回原城市的简化情景，或接入实测梯次返厂OD数据")
        required_echelon = ("cost_cny_per_t", "gwp_kg_per_t", "water_l_per_t", "service_revenue_cny_per_t", "source", "source_locator")
        if any(pathway.get("echelon_service", {}).get(key) in (None, "") for key in required_echelon):
            raise InputError("梯次比例非零时须提供相应服务的成本、环境负荷和收益依据，不能默认免费/零排放")
    nodes = deepcopy(tables["network_nodes.csv"])
    for node in nodes:
        if node["role"] in {"refining", "echelon"} and float(node["variable_handling_cny_t"]) != 0:
            raise InputError("精炼/梯次的变动费用已由LCI/服务模型计取，网络节点该字段须为0，避免重复计算")
        if node["role"] == "echelon" and float(node["capacity_t_y"]) < cfg["policy_rules"]["course_screening"]["echelon_capacity_min_t_y"]:
            node["eligible"] = "false"
    allowed = set(pathway["refining_node_ids"])
    nodes = [n for n in nodes if n["role"] != "refining" or n["node_id"] in allowed]
    if {n["node_id"] for n in nodes if n["role"] == "refining"} != allowed:
        raise InputError("refining_node_ids引用了未提供的精炼候选地")
    node_ids = {n["node_id"] for n in nodes}
    edges = [e for e in tables["road_distances.csv"] if e["from_node"] in node_ids and e["to_node"] in node_ids]
    metrics = deepcopy(pathway["policy_case"])
    source(pathway, "pathway config")
    present = [element for element in ELEMENTS if sum(r[element+"_refining_input_kg"] for r in annual) > 1e-10]
    if pathway["pathway"] != "direct":
        for chemistry in chemistry_t:
            effective = bundle[5][pathway["id"]][chemistry]
            for element in present:
                if sum(r[element+"_refining_input_kg"] for r in annual if r["chemistry"] == chemistry) <= 1e-10:
                    continue
                field = "li_smelting_recovery_fraction" if element == "Li" else element.lower()+"_recovery_fraction"
                if metrics.get(field) not in (None, "") and effective[element] > float(metrics[field])+1e-9:
                    raise InputError(f"{chemistry}/{element}全链有效回收率大于其冶炼工序回收率，输入口径不一致")
    # 区域潜在再生供应比不自动填写为新电池实际再生含量证明。
    metrics.update({"as_of_date": cfg["policy_as_of_date"], "pathway": pathway["pathway"], "present_elements": present})
    policy_results = []
    for node in nodes:
        if node["role"] != "refining":
            continue
        case = {**metrics, "design_capacity_t_y": float(node["capacity_t_y"])}
        check = evaluate_policy(case, cfg["policy_rules"])
        policy_results.append(check)
        if check["status"] == "Redline_Vetoed":
            node["eligible"] = "false"
        elif check["status"] == "Data_Incomplete":
            raise InputError("工厂政策输入不全: "+", ".join(check["missing"]))
    if policy_results and all(check["status"] == "Redline_Vetoed" for check in policy_results):
        return {"status": "Redline_Vetoed", "reason": ";".join(sorted({name for check in policy_results for name in check["failed"]}))}, {}, []
    origin = {}
    for node in nodes:
        if node["role"] == "origin":
            if node["city"] in origin:
                raise InputError("本简化网络每城市须有唯一origin节点")
            origin[node["city"]] = node["node_id"]
    supplies = []
    for city, values in supply_by_city.items():
        if city not in origin:
            raise InputError(f"缺少{city}网络起点，不能丢弃该城市")
        for commodity, q in values.items():
            if q > 0:
                supplies.append({"node_id": origin[city], "commodity": commodity, "supply_t": q})
    cache_key = (pathway["id"], tuple((s["node_id"], s["commodity"], round(s["supply_t"], 9)) for s in supplies))
    if cache_key not in network_cache:
        network_cache[cache_key] = solve_network(nodes, edges, supplies, cfg["maximum_road_leg_km"])
    network = network_cache[cache_key]
    if network["status"] != "Optimal":
        return {"status": network["status"], "reason": network["reason"]}, network, []
    mixed_lci = {"gwp": 0.0, "water": 0.0, "variable_cost": 0.0}
    contributions, purchase = [], 0.0
    for chemistry, weight_t in chemistry_t.items():
        if weight_t <= 0:
            continue
        inventory = [r for r in tables["lci.csv"] if r["pathway"] == pathway["id"] and r["chemistry"] == chemistry]
        result = evaluate_inventory(inventory, green_share, energy[0])
        weight = weight_t/tonnes
        for key in mixed_lci:
            mixed_lci[key] += result[key]*weight
        contributions.extend({**r, "chemistry": chemistry, "mix_weight": weight} for r in result["contributions"])
        purchase += weight*find_procurement_quote(tables["procurement_quotes.csv"], chemistry, lce_price, float(pathway["soh_fraction"]))
    mixed_lci["gwp"] += network["transport_gwp_kg"]/tonnes
    mixed_lci["water"] += network["transport_water_l"]/tonnes
    contributions.append({"component": "collection_transport", "quantity": sum(r["tonne_km"] for r in network["flows"])/tonnes,
                          "unit": "t_km", "gwp_kg_per_t_battery": network["transport_gwp_kg"]/tonnes,
                          "water_l_per_t_battery": network["transport_water_l"]/tonnes,
                          "cost_cny_per_t_battery": network["annual_cost_cny"]/tonnes,
                          "chemistry": "mixed", "mix_weight": 1.0})
    echelon_t = sum(row["echelon_input_t"] for row in annual)
    echelon_service_cost, echelon_service_revenue = 0.0, 0.0
    if echelon_t > 0:
        service = pathway["echelon_service"]
        mixed_lci["gwp"] += echelon_t/tonnes*number(service["gwp_kg_per_t"], "梯次GWP", 0)
        mixed_lci["water"] += echelon_t/tonnes*number(service["water_l_per_t"], "梯次水耗", 0)
        echelon_service_cost = echelon_t*float(service["cost_cny_per_t"])
        echelon_service_revenue = echelon_t*float(service["service_revenue_cny_per_t"])
        contributions.append({"component": "echelon_service", "quantity": echelon_t/tonnes, "unit": "t",
                              "gwp_kg_per_t_battery": echelon_t/tonnes*float(service["gwp_kg_per_t"]),
                              "water_l_per_t_battery": echelon_t/tonnes*float(service["water_l_per_t"]),
                              "cost_cny_per_t_battery": echelon_service_cost/tonnes,
                              "chemistry": "mixed", "mix_weight": 1.0})
    lce_yield = sum(row["Li_secondary_kg"] for row in annual)/1000*LI_TO_LCE/tonnes
    products = {"lce_t_per_t_battery": lce_yield, "lce_price_cny_t": lce_price,
                "lce_environment_allocation_fraction": pathway["lce_environment_allocation_fraction"],
                "allocation_source": pathway["allocation_source"], "coproducts": pathway["coproducts_per_t_battery"]}
    if echelon_t > 0:
        products["coproducts"] = list(products["coproducts"])+[{"name": "echelon_service",
            "quantity_per_t_battery": echelon_t/tonnes, "price_cny_per_unit": float(pathway["echelon_service"]["service_revenue_cny_per_t"]),
            "source": pathway["echelon_service"]["source"], "source_locator": pathway["echelon_service"]["source_locator"]}]
    # 所选节点全部CAPEX及固定OPEX已进入网络年固定费用，不在这里再年金化一次。
    finance = {"design_capacity_t_y": sum(float(n["capacity_t_y"]) for n in nodes if n["node_id"] in network["opened_nodes"] and n["role"] == "refining"),
               "capex_cny": 0, "fixed_opex_cny_y": 0, "wacc": 0, "life_years": 1}
    physical = compare_pathway(mixed_lci, finance, tonnes, purchase, products, baseline,
                               network_cost_cny=network["annual_cost_cny"]+echelon_service_cost)
    policy_money = financial_adjustments(physical["avoided_gwp_kg_per_t_lce"]*lce_yield,
                    number(pathway["fresh_withdrawal_m3_per_t_battery"], "工厂直接新鲜取水量", 0),
                    pathway["taxable_pollutants_per_t_battery"], pathway["financial_policy"],
                    all(r["status"] == "EU_Numerical_Screen_Passed" for r in policy_results))
    result = compare_pathway(mixed_lci, finance, tonnes, purchase, products, baseline,
                    policy_cost_cny_t=policy_money["total_cny"], network_cost_cny=network["annual_cost_cny"]+echelon_service_cost)
    result.update({"status": "Feasible", "year": year, "pathway": pathway["id"], "primary_route": baseline["route"],
                   "green_share": green_share, "lce_price_cny_t": lce_price,
                   "refining_input_t": tonnes, "collected_t": sum(r["collected_battery_t"] for r in annual),
                   "echelon_input_t": echelon_t, "capex_cny": network["capex_cny"],
                   "annual_capital_cny": network["annual_capital_cny"], "network_cost_cny": network["annual_cost_cny"],
                   "policy_adjustment_cny_per_t_battery": policy_money["total_cny"],
                   "annual_base_opex_cny": result["gross_cost_cny_per_t_battery"]*tonnes-network["annual_capital_cny"],
                   "annual_product_and_service_revenue_cny": result["revenue_cny_per_t_battery"]*tonnes,
                   "annual_policy_adjustment_cny": policy_money["total_cny"]*tonnes,
                   "environment_allocation_method": pathway["allocation_source"]})
    return result, network, contributions


def run_full():
    bundle = load_inputs()
    cfg, tables, *_ = bundle
    if cfg["policy_as_of_date"][:4] != str(cfg["decision_year"]):
        raise InputError("policy_as_of_date须与decision_year一致")
    baselines = tables["primary_lce_baselines.csv"]
    if {r["route"] for r in baselines} != {"brine", "spodumene"} or len(baselines) != 2:
        raise InputError("须分别提供卤水和锂辉石的同功能单位原生基准")
    collection_grid = [number(x, "收集率情景", 0, 1) for x in cfg["grid"]["collection_fractions"]]
    green_grid = [number(x, "绿电情景", 0, 1) for x in cfg["grid"]["green_fractions"]]
    if len(set(collection_grid))*len(set(green_grid)) < 500:
        raise InputError("至少500个不同收集率×绿电组合，不能重复行充数")
    baseline_export = False
    records, details, network_cache, mfa_cache = [], {}, {}, {}
    for pathway in cfg["pathways"]:
        if len(set(pathway["lce_prices_cny_t"])) < 2:
            raise InputError("每个工艺至少提供两个有来源的Li价格及对应收购报价，用于价格敏感性；不能默认价格波动为零")
        if pathway["id"] not in {r["pathway"] for r in tables["recovery_parameters.csv"]}:
            raise InputError("工艺配置与回收率表不一致")
        base_rows, base_balance = calculate_mfa(bundle, pathway)
        if pathway["id"] == cfg["baseline_pathway_id"]:
            write_csv(OUTPUT / "dmfa_annual.csv", base_rows)
            write_csv(OUTPUT / "element_balance.csv", base_balance)
            baseline_export = True
            print("year city chemistry element opening+new+echelon_input_kg total_output_kg relative_error")
            for row in base_balance:
                print(row["year"], row["city"], row["chemistry"], row["element"], f"{row['total_input_kg']:.6f}", f"{row['total_output_kg']:.6f}", f"{row['relative_error']:.3e}")
        for collect, green, price, baseline in itertools.product(collection_grid, green_grid, pathway["lce_prices_cny_t"], baselines):
            key = (pathway["id"], collect)
            if key not in mfa_cache:
                mfa_cache[key] = calculate_mfa(bundle, pathway, collect)
            try:
                row, network, contributions = evaluate_case(bundle, pathway, mfa_cache[key][0], green, number(price, "Li价", 0), baseline, network_cache)
            except InputError as exc:
                row, network, contributions = {"status": "Data_Incomplete", "reason": str(exc)}, {}, []
            case_id = len(records)
            row.update({"case_id": case_id, "collection_fraction": collect, "green_share": green,
                        "lce_price_cny_t": price, "pathway": pathway["id"], "primary_route": baseline["route"]})
            records.append(row)
            if row["status"] == "Feasible":
                details[case_id] = (network, contributions, mfa_cache[key])
    if not baseline_export:
        raise InputError("baseline_pathway_id必须指向一个已配置工艺")
    fieldnames = list(dict.fromkeys(key for row in records for key in row))
    write_csv(OUTPUT / "scenario_results.csv", records, fieldnames)
    # 两种原生基准分别排序，避免混合比较边界或把基准差异当作技术改进。
    anchor_export = []
    for primary in ("brine", "spodumene"):
        feasible = [r for r in records if r["status"] == "Feasible" and r["primary_route"] == primary]
        frontier, anchors = pareto_frontier(feasible)
        write_csv(OUTPUT / f"pareto_{primary}.csv", frontier)
        for name, anchor in anchors.items():
            anchor_export.append({"anchor": name, **anchor})
        if anchors:
            b = anchors["B_Utopia_Distance_Min"]
            network, contributions, (dmfa, balance) = details[b["case_id"]]
            write_json(OUTPUT / f"recommended_network_{primary}.json", network)
            write_csv(OUTPUT / f"recommended_lci_{primary}.csv", contributions)
            write_csv(OUTPUT / f"recommended_dmfa_{primary}.csv", dmfa)
            write_csv(OUTPUT / f"recommended_balance_{primary}.csv", balance)
            node_lookup = {n["node_id"]: n for n in tables["network_nodes.csv"]}
            projects = []
            for key in network["opened_nodes"]:
                node = node_lookup[key]
                q = sum(r["flow_t"] for r in network["flows"] if r["to_node"] == key)
                projects.append({"node_id": key, "city": node["city"], "role": node["role"],
                    "design_capacity_t_y": node["capacity_t_y"], "actual_throughput_t_y": q,
                    "capex_cny": node["capex_cny"], "known_fixed_opex_cny_y": node["fixed_opex_cny_y"],
                    "known_handling_opex_cny_y": q*float(node["variable_handling_cny_t"]),
                    "opex_scope": "工厂过程变动费用在区域LCI表核算，未无依据分摊；本行不是完整项目OPEX",
                    "source": node["source"], "source_locator": node["source_locator"]})
            write_csv(OUTPUT / f"recommended_projects_{primary}.csv", projects)
    write_csv(OUTPUT / "anchors.csv", anchor_export)
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.iterdir() if p.is_file() and p.suffix in {".csv", ".json"}}
    write_json(OUTPUT / "run_manifest.json", {"scenarios": len(records), "feasible": len(details), "input_sha256": manifest,
        "scope": "固定输入、工艺与情景网格下的条件前沿；物流网络先按费用最小求解，不声称全连续空间全局多目标最优", "artificial_provincial_data": False})
    if not details:
        raise InputError("已记录全部工况，但没有可用方案；查看scenario_results.csv原因，不生成虚假前沿")
    from plot_results import render_results
    render_results(OUTPUT)
    print(f"完成{len(records)}组情景，其中{len(details)}组可用。")


def run_mfa_only():
    bundle = load_inputs(stage="mfa")
    pathway = {"id": bundle[0]["baseline_pathway_id"]}
    rows, balances = calculate_mfa(bundle, pathway)
    write_csv(OUTPUT / "dmfa_annual.csv", rows)
    write_csv(OUTPUT / "element_balance.csv", balances)
    for row in balances:
        print(row["year"], row["city"], row["chemistry"], row["element"],
              f"input={row['total_input_kg']:.6f} output={row['total_output_kg']:.6f} error={row['relative_error']:.3e}")
    print("dMFA已完成；未运行LCA-TEA或网络，不应把本命令当作全任务完成。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract-yearbook", action="store_true")
    parser.add_argument("--plot-yearbook", action="store_true", help="仅绘制真实年鉴背景图，无需预测模型参数")
    parser.add_argument("--check-inputs", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--dmfa-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        import unittest
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_models.py")).wasSuccessful() else 1
    try:
        if args.extract_yearbook:
            from extract_yearbook import extract_yearbook
            extract_yearbook()
        if args.plot_yearbook:
            from plot_yearbook_context import render_yearbook_context
            render_yearbook_context(OUTPUT)
        if args.check_inputs:
            issues = check_readiness()
            write_json(OUTPUT / "data_readiness.json", {"ready": not issues, "issues": issues, "scope": "只检查数据接口，不产生湖北预测值"})
            for issue in issues:
                print("[待补充]", issue)
            if issues:
                return 2
        if args.run:
            run_full()
        elif args.dmfa_only:
            run_mfa_only()
        if not any(vars(args).values()):
            parser.print_help()
        return 0
    except (ValueError, ArithmeticError, KeyError, TypeError) as exc:
        print("[未生成正式预测]", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
