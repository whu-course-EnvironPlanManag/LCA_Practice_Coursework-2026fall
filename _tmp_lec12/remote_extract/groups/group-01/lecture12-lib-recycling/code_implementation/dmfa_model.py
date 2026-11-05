"""双参数Weibull年度队列dMFA，不用密度采样值充当年度退役概率。

AI提示词：依据Wu(2024)式1、3和任务书，实现年度安装队列的生存函数、
退役CDF差分、Li/Ni/Co/Mn独立输入输出核查及梯次延迟库存；不得补造参数。
校验状态：自动化单元测试；尚未经组员人工签字确认。数学与边界见README。
约定：每年末新增安装，当年不退役；下一年为服役第1年。
"""
from collections import defaultdict
import math
from common import ELEMENTS, InputError, fraction, number, source


def survival(age, eta, beta):
    age = number(age, "age", 0)
    eta, beta = number(eta, "Weibull eta", 1e-12), number(beta, "Weibull beta", 1e-12)
    return math.exp(-((age / eta) ** beta))


def retirement_probability(age, eta, beta):
    age = number(age, "retirement age", 1)
    return survival(age-1, eta, beta) - survival(age, eta, beta)


def stock_driven_installations(targets, eta, beta, opening=None):
    """由逐年目标电池在用容量反推新增容量；下降过快时拒绝负安装量。

    targets为连续年份->kWh；opening为(截至基准年前一年的存量kWh, 已服役整年)。
    此处电池容量包括替换包，不能直接将车辆保有量差分当作安装量。
    """
    if not targets:
        raise InputError("目标存量序列为空")
    survival(0, eta, beta)
    years = sorted(targets)
    if years != list(range(years[0], years[-1]+1)):
        raise InputError("目标存量年份须连续")
    existing = [(number(q, "opening stock", 0), number(age, "opening age", 0)) for q, age in (opening or [])]
    installed = {}
    for year in years:
        elapsed = year - years[0] + 1
        old = sum(q * math.exp(-(((age+elapsed)/eta)**beta - (age/eta)**beta)) for q, age in existing)
        remaining = old + sum(q * survival(year-vintage, eta, beta) for vintage, q in installed.items())
        target = number(targets[year], "target stock", 0)
        amount = target - remaining
        if amount < -1e-8:
            raise InputError(f"{year}目标低于自然生存库存，需独立的提前退役模型，不能截断负新增")
        installed[year] = max(0.0, amount)
    return installed


def run_dmfa(cohorts, materials, start_year, end_year, collections, diversions, recovery, opening=None):
    """队列输入为安装kWh，材料参数按安装年份固定；年输出按化学体系分组。

    collections[(year,city)]为正规收集率；diversions[(year,chem)]含梯次比例与整年延迟。
    recovery[chem]为各元素从进入精炼环节到再生产品的总有效回收率，不等于单工序回收率。
    opening仅供显式初始存量：base_year=start_year-1，age_years、surviving_kwh。
    全历史安装队列与opening方式不得在同一城市/体系混用。
    """
    if int(start_year) != start_year or int(end_year) != end_year or end_year < start_year:
        raise InputError("预测年份区间错误")
    years = range(int(start_year), int(end_year)+1)
    definitions = {}
    for row in materials:
        source(row, "materials")
        key = (row["chemistry"], int(row["vintage_year"]))
        if key in definitions:
            raise InputError(f"材料参数重复: {key}")
        definitions[key] = {"eta": number(row["eta_years"], "eta_years", 1e-12),
                            "beta": number(row["beta"], "beta", 1e-12),
                            "density": number(row["pack_specific_energy_kwh_per_kg"], "整包比能量", 1e-12),
                            **{e: number(row[e+"_kg_per_kwh"], e+"_kg_per_kwh", 0) for e in ELEMENTS}}
        if sum(definitions[key][e] for e in ELEMENTS) > 1/definitions[key]["density"]:
            raise InputError("材料中的Li/Ni/Co/Mn总质量超过整包质量，检查电芯/整包比能量口径")
    annual = defaultdict(lambda: defaultdict(float))
    opening_groups = {(r["city"], r["chemistry"]) for r in (opening or [])}
    seen = set()
    for row in cohorts:
        source(row, "cohorts")
        city, chemistry, vintage = row["city"], row["chemistry"], int(row["year"])
        if not city or not chemistry:
            raise InputError("城市与化学体系不得为空")
        key = (city, chemistry, vintage)
        if key in seen:
            raise InputError(f"安装队列重复: {key}；请先合并车型或使用不同队列标识")
        seen.add(key)
        if vintage < start_year and (city, chemistry) in opening_groups:
            raise InputError("同一城市/体系的完整历史安装与初始存量重复")
        params = definitions.get((chemistry, vintage))
        if params is None:
            raise InputError(f"缺少安装年份材料参数: {(chemistry, vintage)}")
        quantity = number(row["installed_kwh"], "installed_kwh", 0)
        for year in years:
            age = year-vintage
            if age < 0:
                continue
            a = annual[(year, city, chemistry)]
            prob = retirement_probability(age, params["eta"], params["beta"]) if age >= 1 else 0
            before = survival(age-1, params["eta"], params["beta"]) if age >= 1 else 0
            after = survival(age, params["eta"], params["beta"])
            _add_cohort(a, quantity, params, before, after, prob, age == 0)
    for row in opening or []:
        source(row, "opening cohorts")
        if int(row["base_year"]) != start_year-1:
            raise InputError("初始存量基准年必须等于预测起始年前一年")
        city, chemistry = row["city"], row["chemistry"]
        age = number(row["age_years"], "opening age", 0)
        if age != int(age) or int(row["vintage_year"]) != int(row["base_year"])-int(age):
            raise InputError("期初存量的安装年份、基准年与已服役整年数不一致")
        params = definitions.get((chemistry, int(row["vintage_year"])))
        if params is None:
            raise InputError("缺少初始存量队列的原安装年份材料参数")
        quantity = number(row["surviving_kwh"], "opening surviving kWh", 0)
        for year in years:
            elapsed = year-start_year
            conditional = lambda k: math.exp(-(((age+k)/params["eta"])**params["beta"]-(age/params["eta"])**params["beta"]))
            before, after = conditional(elapsed), conditional(elapsed+1)
            _add_cohort(annual[(year, city, chemistry)], quantity, params, before, after, before-after, False)
    if not annual:
        raise InputError("没有可计算队列")
    # 为历史梯次库存释放建立连续年份，不把尚未退役的尾部强行塞入末年。
    groups = {(city, chemistry) for _, city, chemistry in annual}
    rows, balances = [], []
    queue = defaultdict(lambda: defaultdict(float))
    echelon_stock = defaultdict(float)
    for year in years:
        for city, chemistry in sorted(groups):
            a = annual[(year, city, chemistry)]
            rate = fraction(collections.get((year, city)), f"{year}/{city}正规收集率") if a["retired_kg"] > 0 else 0.0
            diversion = diversions.get((year, chemistry))
            if diversion is None and a["retired_kg"]*rate > 0:
                raise InputError(f"缺少{year}/{chemistry}梯次分流配置；没有梯次也须明确填0")
            if diversion is None:
                diversion = {"echelon_share": 0, "delay_years": 0}  # 零入流下不适用，不代表观测比例。
            share = fraction(diversion["echelon_share"], "梯次比例")
            delay = number(diversion["delay_years"], "梯次延迟", 0)
            if delay != int(delay) or (share > 0 and delay < 1):
                raise InputError("梯次延迟须为正整数年；零梯次比例允许0")
            row = {"year": year, "city": city, "chemistry": chemistry,
                   "installed_kwh": a["installed_kwh"], "stock_kwh": a["stock_kwh"],
                   "retired_kwh": a["retired_kwh"], "retired_battery_t": a["retired_kg"]/1000,
                   "collected_battery_t": a["retired_kg"]*rate/1000,
                   "echelon_input_t": a["retired_kg"]*rate*share/1000,
                   "direct_recycling_t": a["retired_kg"]*rate*(1-share)/1000}
            mass_key = (city, chemistry, "battery_kg")
            queue[(year+int(delay), city, chemistry)]["battery_kg"] += a["retired_kg"]*rate*share
            returned_mass = queue[(year, city, chemistry)]["battery_kg"]
            row["echelon_return_t"] = returned_mass/1000
            row["refining_input_t"] = row["direct_recycling_t"]+row["echelon_return_t"]
            echelon_stock[mass_key] += row["echelon_input_t"]*1000-returned_mass
            row["echelon_stock_t"] = echelon_stock[mass_key]/1000
            for element in ELEMENTS:
                if chemistry not in recovery:
                    raise InputError(f"缺少{chemistry}的全链有效回收率")
                recovered_fraction = fraction(recovery[chemistry][element], chemistry+element+"总有效回收率")
                inflow, before, stock, retired = (a[f"{element}_{suffix}"] for suffix in ("in", "before", "stock", "retired"))
                collected = retired*rate
                into_echelon = collected*share
                queue[(year+int(delay), city, chemistry)][element] += into_echelon
                released = queue[(year, city, chemistry)][element]
                old_echelon = echelon_stock[(city, chemistry, element)]
                new_echelon = old_echelon+into_echelon-released
                echelon_stock[(city, chemistry, element)] = new_echelon
                refinery = collected*(1-share)+released
                product, residue = refinery*recovered_fraction, refinery*(1-recovered_fraction)
                uncollected = retired-collected
                total_in = before+inflow+old_echelon
                total_out = stock+new_echelon+product+residue+uncollected
                error = abs(total_in-total_out)/max(abs(total_in), 1e-30)
                if error >= 0.0005:
                    raise ArithmeticError(f"{year}/{city}/{element}守恒误差超过0.05%")
                balances.append({"year": year, "city": city, "chemistry": chemistry, "element": element,
                                 "opening_in_use_kg": before, "new_input_kg": inflow,
                                 "opening_echelon_kg": old_echelon, "closing_in_use_kg": stock,
                                 "closing_echelon_kg": new_echelon, "recovered_product_kg": product,
                                 "refining_residue_kg": residue, "outside_formal_system_kg": uncollected,
                                 "total_input_kg": total_in, "total_output_kg": total_out,
                                 "relative_error": error, "passed": True})
                row.update({element+"_stock_kg": stock, element+"_retired_kg": retired,
                            element+"_collected_kg": collected, element+"_secondary_kg": product,
                            element+"_refining_input_kg": refinery})
            rows.append(row)
    return rows, balances


def _add_cohort(a, quantity, params, before, after, prob, is_new):
    a["installed_kwh"] += quantity if is_new else 0
    a["stock_kwh"] += quantity*after
    a["retired_kwh"] += quantity*prob
    a["retired_kg"] += quantity*prob/params["density"]
    for element in ELEMENTS:
        mass = quantity*params[element]
        for suffix, value in (("in", 1 if is_new else 0), ("before", before), ("stock", after), ("retired", prob)):
            a[f"{element}_{suffix}"] += mass*value
