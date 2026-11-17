"""课程筛选条件和欧盟阶段性数值检查；不输出真实认证或行政许可结论。

模块说明：依据任务书和核对的正式政策文本，实现工艺适用性、严格/非严格
边界、日期生效、缺失参数状态及至少3类测试。税费/收益单价不得自行给定。
校验状态：自动化测试；未代替团队人工复核。来源及课程/法规差异见参数文件。
"""
from datetime import date
from common import InputError, fraction, number


def evaluate_policy(case, rules):
    failed, missing, checks = [], [], []
    pathway = case.get("pathway")
    if pathway not in {"hydro", "pyro", "direct"}:
        raise InputError("pathway须为hydro、pyro或direct")
    when = date.fromisoformat(str(case["as_of_date"]))

    def compare(key, threshold, operation="ge", active=True):
        if not active:
            return
        value = case.get(key)
        if value is None or value == "":
            missing.append(key)
            checks.append({"field": key, "threshold": threshold, "operator": operation, "result": "missing"})
            return
        value = number(value, key, 0)
        if key.endswith("_fraction") and value > 1:
            raise InputError(f"{key}须为0—1比例")
        ok = value >= threshold if operation == "ge" else value < threshold if operation == "lt" else value <= threshold
        checks.append({"field": key, "value": value, "threshold": threshold, "operator": operation, "result": "pass" if ok else "fail"})
        if not ok:
            failed.append(key)

    p = rules["course_screening"]
    compare("powder_recovery_fraction", p["powder_recovery_min"])
    compare("al_impurity_fraction", p["al_impurity_max_exclusive"], "lt")
    compare("cu_impurity_fraction", p["cu_impurity_max_exclusive"], "lt")
    compare("cu_recovery_fraction", p["copper_aluminium_recovery_min"])
    compare("al_recovery_fraction", p["copper_aluminium_recovery_min"])
    compare("wastewater_reuse_fraction", p["wastewater_reuse_min"])
    compare("fluorine_fixation_fraction", p["fluorine_fixation_min"])
    compare("rd_revenue_fraction", p["rd_revenue_min"])
    compare("design_capacity_t_y", p["recycling_capacity_min_t_y"])
    if pathway == "direct":
        compare("material_restoration_fraction", p["material_restoration_min"])
    else:
        compare("li_smelting_recovery_fraction", p["li_smelting_recovery_min"])
        compare("lce_energy_kgce_per_t", p["lce_energy_max_exclusive_kgce_t"], "lt", case.get("produces_lce") is True)
        if "produces_lce" not in case:
            missing.append("produces_lce")
        present = case.get("present_elements")
        if present is None:
            missing.append("present_elements")
        else:
            for element in ("Ni", "Co", "Mn"):
                compare(element.lower()+"_recovery_fraction", p["ncm_recovery_min"], active=element in present)

    export = case.get("export_eu")
    if not isinstance(export, bool):
        missing.append("export_eu")
    if export is True:
        eu = rules["eu"]
        eu_present = case.get("eu_present_elements")
        if eu_present is None:
            missing.append("eu_present_elements")
            eu_present = []
        recovery_target = 0
        for rule in eu["li_material_recovery"]:
            if when >= date.fromisoformat(rule["effective_date"]):
                recovery_target = rule["minimum"]
        if recovery_target:
            compare("li_material_recovery_fraction", recovery_target)
        other_recovery = 0
        for rule in eu["other_material_recovery"]:
            if when >= date.fromisoformat(rule["effective_date"]):
                other_recovery = rule["minimum"]
        if other_recovery:
            for element in ("Co", "Cu", "Pb", "Ni"):
                compare(element.lower()+"_material_recovery_fraction", other_recovery, active=element in eu_present)
        recycled_target = 0
        for rule in eu["li_recycled_content"]:
            if when >= date.fromisoformat(rule["effective_date"]):
                recycled_target = rule["minimum"]
        if recycled_target:
            compare("li_recycled_content_fraction", recycled_target)
        active_rule = None
        for rule in eu["other_recycled_content"]:
            if when >= date.fromisoformat(rule["effective_date"]):
                active_rule = rule
        if active_rule is not None:
            for element, target in active_rule["minimum"].items():
                compare(element.lower()+"_recycled_content_fraction", target, active=element in eu_present)
        # 欧盟碳足迹阈值依电池类别/授权法案适用；不得编一个统一阈值。
        if "export_carbon_limit_applicable" not in case:
            missing.append("export_carbon_limit_applicable")
        elif case["export_carbon_limit_applicable"]:
            if case.get("export_carbon_limit") is None:
                missing.append("export_carbon_limit")
            else:
                compare("export_carbon_footprint", number(case["export_carbon_limit"], "出口同功能单位碳阈值", 0), "le")
        if when >= date.fromisoformat(eu["battery_passport_effective_date"]):
            value = case.get("passport_ready")
            if not isinstance(value, bool):
                missing.append("passport_ready")
            elif not value:
                failed.append("passport_ready")
    status = "Redline_Vetoed" if failed else "Data_Incomplete" if missing else "EU_Numerical_Screen_Passed" if export else "Domestic_Numerical_Screen_Passed"
    return {"status": status, "failed": sorted(set(failed)), "missing": sorted(set(missing)), "checks": checks,
            "scope": "课程方案筛选及已配置的数值规则，不构成真实认证或完整法律合规证明"}


def financial_adjustments(avoided_gwp_kg, water_m3, pollutants, finance, export_eligible):
    """显式政策情景；缺省没有自动补贴。所有金额统一CNY。

    carbon_mode必须为none或scenario_credit；后者须单独说明方法学/权属，
    它不是因“技术减排”为正就自动获得的CCER。污水处理费用不得替代应税排放量。
    """
    mode = finance.get("carbon_mode")
    if mode not in {"none", "scenario_credit"}:
        raise InputError("须明确carbon_mode，不默认存在碳收益")
    carbon = 0.0
    if mode == "scenario_credit":
        price = number(finance.get("carbon_price_cny_t"), "碳价", 0)
        eligible = finance.get("carbon_credit_eligible")
        if not isinstance(eligible, bool):
            raise InputError("须明确碳信用方法学/权属适用性")
        if eligible:
            carbon = -max(0, avoided_gwp_kg)/1000*price
        if avoided_gwp_kg < 0 and finance.get("excess_emissions_fee_cny_t") is not None:
            carbon = -avoided_gwp_kg/1000*number(finance["excess_emissions_fee_cny_t"], "超排价格", 0)
    water_tax = water_m3*number(finance.get("water_tax_cny_m3"), "适用取水税额", 0)
    environmental = 0.0
    rates = finance.get("pollutant_tax_cny_per_unit")
    if not isinstance(rates, dict):
        raise InputError("须提供污染物应税计量与税额配置；无应税排放亦须明确空字典")
    for name, amount in pollutants.items():
        if name not in rates:
            raise InputError(f"缺少{name}应税单价")
        environmental += number(amount, name, 0)*number(rates[name], name+"税额", 0)
    premium_mode = finance.get("export_premium_mode")
    if premium_mode not in {"none", "contract_scenario"}:
        raise InputError("须明确溢价情景，不默认法规规定有固定补贴")
    premium = 0.0
    if premium_mode == "contract_scenario" and export_eligible:
        premium = -number(finance.get("export_premium_cny_per_fu"), "合同溢价", 0)
    return {"carbon_adjustment_cny": carbon, "water_tax_cny": water_tax,
            "environment_tax_cny": environmental, "export_premium_cny": premium,
            "total_cny": carbon+water_tax+environmental+premium}


def hubei_industrial_water_tax(withdrawal_m3, permitted_m3, water_source, unauthorized=False):
    """湖北2024-12-24通知：工业地表水0.15、地下水0.2元/m³。

    超许可水量按30%、50%分段对超量部分征2/3/5倍；未批准取水3倍。
    仅适用于已明确直接取水税义务的场景；购自公共供水不能机械套税。
    来源：https://czj.wuhan.gov.cn/FBJD/ZCWJ/GFWJ/202412/t20241231_2511060.html
    """
    amount = number(withdrawal_m3, "直接取水量", 0)
    permitted = number(permitted_m3, "许可取水量", 0)
    if water_source not in {"surface", "groundwater"}:
        raise InputError("须明确地表水surface或地下水groundwater")
    rate = 0.15 if water_source == "surface" else 0.2
    if unauthorized:
        return amount*rate*3
    if permitted <= 0:
        raise InputError("合法直接取水情景须提供正的许可取水量")
    excess = max(0, amount-permitted)
    return rate*(min(amount, permitted)+2*min(excess, .3*permitted)
                 +3*min(max(0, excess-.3*permitted), .2*permitted)
                 +5*max(0, excess-.5*permitted))
