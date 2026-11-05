"""读取组员填写的标准输入；缺值即报告，不启用演示默认数据。"""
from collections import defaultdict
from datetime import date
from common import DATA, ELEMENTS, InputError, read_csv, load_config, number, fraction, source

TABLES = {
    "installation_cohorts.csv": ["year", "city", "chemistry", "installed_kwh", "record_type", "source", "source_locator"],
    "material_parameters.csv": ["chemistry", "vintage_year", "eta_years", "beta", "pack_specific_energy_kwh_per_kg", *[e+"_kg_per_kwh" for e in ELEMENTS], "source", "source_locator"],
    "opening_stock.csv": ["base_year", "city", "chemistry", "vintage_year", "age_years", "surviving_kwh", "source", "source_locator"],
    "collection_rates.csv": ["year", "city", "collection_fraction", "source", "source_locator"],
    "echelon_parameters.csv": ["year", "chemistry", "echelon_share", "delay_years", "source", "source_locator"],
    "recovery_parameters.csv": ["pathway", "chemistry", *[e+"_effective_recovery" for e in ELEMENTS], "source", "source_locator"],
    "energy_factors.csv": ["year", "grid_gwp_kg_per_kwh", "green_gwp_kg_per_kwh", "grid_water_l_per_kwh", "green_water_l_per_kwh", "grid_price_cny_per_kwh", "green_price_cny_per_kwh", "source", "source_locator"],
    "lci.csv": ["pathway", "chemistry", "component", "quantity_per_t_battery", "unit", "gwp_kg_per_unit", "water_l_per_unit", "cost_cny_per_unit", "source", "source_locator"],
    "procurement_quotes.csv": ["chemistry", "lce_price_cny_t", "soh_fraction", "purchase_cny_per_t_battery", "source", "source_locator"],
    "primary_lce_baselines.csv": ["route", "functional_unit", "system_boundary", "gwp_kg_per_t_lce", "water_l_per_t_lce", "cost_cny_per_t_lce", "source", "source_locator"],
    "network_nodes.csv": ["node_id", "city", "role", "capacity_t_y", "capex_cny", "wacc", "life_years", "fixed_opex_cny_y", "variable_handling_cny_t", "eligible", "longitude", "latitude", "source", "source_locator"],
    "road_distances.csv": ["from_node", "to_node", "commodity", "road_distance_km", "transport_cny_tkm", "transport_gwp_kg_tkm", "transport_water_l_tkm", "source", "source_locator"],
}


MFA_TABLES = set(list(TABLES)[:6])


def check_readiness(stage="all"):
    issues = []
    for name, fields in TABLES.items():
        if stage == "mfa" and name not in MFA_TABLES:
            continue
        try:
            read_csv(name, fields, allow_empty=name == "opening_stock.csv")
        except InputError as exc:
            issues.append(str(exc))
    cfg = load_config()
    try:
        year_keys = ("model_start_year", "planning_start_year", "decision_year", "planning_end_year")
        values = [number(cfg.get(key), key, 1, 9999) for key in year_keys]
        if any(value != int(value) for value in values) or values != sorted(values):
            raise InputError("年份须为整数且满足模型起年≤规划起年≤代表年≤规划末年")
        if date.fromisoformat(cfg["policy_as_of_date"]).year != values[2]:
            raise InputError("政策评估日期须与代表年一致")
    except (InputError, ValueError, KeyError, TypeError) as exc:
        issues.append("时间边界配置错误: "+str(exc))
    scenario_history = cfg.get("analysis_mode") == "exploratory_scenario" and cfg.get("historical_scenario_coverage_complete")
    if not cfg.get("historical_installations_complete") and not cfg.get("use_opening_stock") and not scenario_history:
        issues.append("须确认完整历史安装队列，或提供服役年龄明确的期初存量；禁止默认历史为零")
    if cfg.get("opening_echelon_stock_status") != "documented_zero":
        issues.append("当前版本要求明确证明模型起始年前尚无梯次库存；有存量须从更早完整安装历史起算")
    if cfg.get("battery_migration_boundary") not in {"closed_region_scenario", "net_migration_included_in_cohorts"}:
        issues.append("须明确跨省电池迁移边界；没有迁移数据只能标记封闭区域情景，不能声称观测预测")
    if stage == "all" and not cfg.get("pathways"):
        issues.append("model_config.json中缺少有出处的工艺、财务、产品和政策输入")
    if stage == "mfa" and not cfg.get("baseline_pathway_id"):
        issues.append("须配置baseline_pathway_id以选择明确的有效回收率")
    return issues


def load_inputs(stage="all"):
    issues = check_readiness(stage)
    if issues:
        raise InputError("\n".join(issues))
    cfg = load_config()
    tables = {name: read_csv(name, fields, allow_empty=name == "opening_stock.csv") for name, fields in TABLES.items() if stage != "mfa" or name in MFA_TABLES}
    for name, rows in tables.items():
        for row in rows:
            source(row, name)
    cohorts = tables["installation_cohorts.csv"]
    for row in cohorts:
        if row["record_type"] not in {"observed_installation", "documented_scenario"}:
            raise InputError("安装队列须标明observed_installation或documented_scenario，不能填汽车产量/总保有量")
    collections, diversions, recovery = {}, {}, {}
    for row in tables["collection_rates.csv"]:
        key = (int(row["year"]), row["city"])
        if key in collections:
            raise InputError("正规收集率重复")
        collections[key] = fraction(row["collection_fraction"], "正规收集率")
    for row in tables["echelon_parameters.csv"]:
        key = (int(row["year"]), row["chemistry"])
        if key in diversions:
            raise InputError("梯次参数重复")
        diversions[key] = row
    for row in tables["recovery_parameters.csv"]:
        by_chemistry = recovery.setdefault(row["pathway"], {})
        if row["chemistry"] in by_chemistry:
            raise InputError("有效回收率重复")
        by_chemistry[row["chemistry"]] = {e: fraction(row[e+"_effective_recovery"], e+"有效回收率") for e in ELEMENTS}
    opening = tables["opening_stock.csv"] if cfg["use_opening_stock"] else []
    if cfg["use_opening_stock"] and not opening:
        raise InputError("已启用期初存量，但opening_stock.csv没有记录")
    return cfg, tables, cohorts, collections, diversions, recovery, opening
