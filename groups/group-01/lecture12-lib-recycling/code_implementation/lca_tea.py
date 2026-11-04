"""可追溯LCI、资本年金、CNY成本与同功能单位比较。

模块说明：按任务书实现1 t进入再生环节整包电池边界；区分LCE与NCA-eq，
不把论文的正极材料排放因子直接用作整包回收因子。所有数量/单价从表读取。
自动测试校验单位、CRF、收益及质量分配；待团队人工审核输入与适用性。
"""
from common import InputError, fraction, number, source

# CIAAW标准原子量简写值（Li 6.94，C 12.011，O 15.999）；仅作化学计量换算。
LI_TO_LCE = (2*6.94+12.011+3*15.999)/(2*6.94)


def capital_recovery_factor(rate, years):
    rate = number(rate, "WACC", 0)
    years = number(years, "运营年数", 1)
    if years != int(years):
        raise InputError("运营年数须为整数")
    return 1/years if rate == 0 else rate*(1+rate)**years/((1+rate)**years-1)


def evaluate_inventory(inventory, green_share, factors):
    """quantity统一为每吨进入精炼环节的整包电池，运输量单位t·km。

    electricity_mix行由绿电份额混合碳、水、价格三类因子，其余行使用独立单位因子。
    treatment行可计治理负荷，但不自动计环保税或将未知排放设零。
    """
    green_share = fraction(green_share, "green_share")
    contributions = []
    if not inventory:
        raise InputError("LCI不能为空")
    for row in inventory:
        source(row, "LCI")
        quantity = number(row["quantity_per_t_battery"], "LCI数量", 0)
        name = row["component"]
        if name == "electricity_mix":
            if row["unit"] != "kWh":
                raise InputError("electricity_mix单位须为kWh")
            intensity = {}
            for item in ("gwp_kg_per_kwh", "water_l_per_kwh", "price_cny_per_kwh"):
                grid = number(factors.get("grid_"+item), "grid_"+item, 0)
                green = number(factors.get("green_"+item), "green_"+item, 0)
                intensity[item] = grid*(1-green_share)+green*green_share
            gwp, water, cost = quantity*intensity["gwp_kg_per_kwh"], quantity*intensity["water_l_per_kwh"], quantity*intensity["price_cny_per_kwh"]
        else:
            gwp = quantity*number(row["gwp_kg_per_unit"], "LCI碳因子", 0)
            water = quantity*number(row["water_l_per_unit"], "LCI耗水因子", 0)
            cost = quantity*number(row["cost_cny_per_unit"], "LCI单价", 0)
        contributions.append({"component": name, "quantity": quantity, "unit": row["unit"],
                              "gwp_kg_per_t_battery": gwp, "water_l_per_t_battery": water,
                              "cost_cny_per_t_battery": cost})
    names = {row["component"] for row in inventory}
    for required in ("electricity_mix", "pretreatment", "process_heat", "reagents", "pollution_control"):
        if required not in names:
            raise InputError(f"LCI缺少{required}，确认为零也须显式提供证据行")
    return {"gwp": sum(r["gwp_kg_per_t_battery"] for r in contributions),
            "water": sum(r["water_l_per_t_battery"] for r in contributions),
            "variable_cost": sum(r["cost_cny_per_t_battery"] for r in contributions),
            "contributions": contributions}


def find_procurement_quote(quotes, chemistry, lce_price, soh):
    """查找有证据的收购价格/情景函数结果，不自造SOH线性系数或默认外推。"""
    selected = [r for r in quotes if r["chemistry"] == chemistry
                and abs(float(r["lce_price_cny_t"])-lce_price) < 1e-7
                and abs(float(r["soh_fraction"])-soh) < 1e-10]
    if len(selected) != 1:
        raise InputError(f"缺少唯一采购报价: {chemistry}, Li价={lce_price}, SOH={soh}")
    source(selected[0], "procurement quotes")
    return number(selected[0]["purchase_cny_per_t_battery"], "收购价", 0)


def compare_pathway(lci, finance, throughput_t, purchase_cny_t, products, baseline, policy_cost_cny_t=0, network_cost_cny=0):
    """baseline同为1 t LCE；本实现使用Li产品单独比较，其他产品环境信用不自动叠加。

    products必须明确实际产出LCE，论文NCA-eq/LCO-eq不能作为该量。
    全部产品收入作为系统扩展经济收入，但环境指标采用Li专用比较或用户明示的分配边界。
    若多产品工艺缺少可比环境分配依据，拒绝LCE比较，避免夸大减排。
    """
    throughput_t = number(throughput_t, "实际处理量", 1e-12)
    capacity = number(finance.get("design_capacity_t_y"), "设计产能", 1e-12)
    if throughput_t > capacity*(1+1e-9):
        raise InputError("实际处理量超过所配置产能")
    capex = number(finance.get("capex_cny"), "CAPEX", 0)
    fixed = number(finance.get("fixed_opex_cny_y"), "固定OPEX", 0)
    annual = capex*capital_recovery_factor(finance.get("wacc"), finance.get("life_years"))
    lce = number(products.get("lce_t_per_t_battery"), "LCE实际产品收率", 1e-12)
    allocation = fraction(products.get("lce_environment_allocation_fraction"), "Li产品环境分配比例")
    if not products.get("allocation_source"):
        raise InputError("LCE环境分配需方法/证据，不默认把混合正极盐当纯LCE")
    main_revenue = number(products.get("lce_price_cny_t"), "Li产品价格", 0)*lce
    coproduct_revenue = 0.0
    for item in products.get("coproducts", []):
        source(item, "coproducts")
        coproduct_revenue += number(item["quantity_per_t_battery"], "副产物数量", 0)*number(item["price_cny_per_unit"], "副产物同单位价格", 0)
    required = {"functional_unit": "t_LCE", "system_boundary": "cradle_to_gate"}
    for key, expected in required.items():
        if baseline.get(key) != expected:
            raise InputError(f"原生基准{key}必须为{expected}")
    if not baseline.get("source"):
        raise InputError("原生基准缺少出处")
    gwp = lci["gwp"]*allocation/lce
    water = lci["water"]*allocation/lce
    avoided = number(baseline.get("gwp_kg_per_t_lce"), "原生LCE GWP", 0)-gwp
    saved_water = number(baseline.get("water_l_per_t_lce"), "原生LCE水耗", 0)-water
    gross = annual/throughput_t+fixed/throughput_t+purchase_cny_t+lci["variable_cost"]+network_cost_cny/throughput_t
    revenue = main_revenue+coproduct_revenue
    net = gross+policy_cost_cny_t-revenue
    # LCOR仅抵扣副产品，不能先减去Li产品销售收入再与原生生产成本比较。
    lcor = (gross+policy_cost_cny_t-coproduct_revenue)/lce
    benchmark_cost = number(baseline.get("cost_cny_per_t_lce"), "同边界原生净成本", 0)
    mac = (lcor-benchmark_cost)/(avoided/1000) if avoided > 0 else None
    return {"gwp_kg_per_t_lce": gwp, "water_l_per_t_lce": water,
            "avoided_gwp_kg_per_t_lce": avoided, "water_saved_l_per_t_lce": saved_water,
            "lcor_cny_per_t_lce": lcor, "mac_cny_per_t_co2e": mac,
            "annual_net_cost_cny": net*throughput_t, "annual_avoided_gwp_kg": avoided*lce*throughput_t,
            "annual_lce_t": lce*throughput_t, "capex_cny": capex, "annual_capital_cny": annual,
            "gross_cost_cny_per_t_battery": gross, "revenue_cny_per_t_battery": revenue,
            "net_cost_cny_per_t_battery": net}
