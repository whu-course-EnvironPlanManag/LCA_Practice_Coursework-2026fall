"""五系统磷物质流模型：PMS / CIS / ACS / LBS / RCS。

建模原则（对应 SI 5 节）：
  1. 能由统计活动量 × 系数直接算的流量，一律独立计算；
  2. 无法独立计算的流量（土壤遗留磷、磷化工损失、草地饲料、加工废弃物），
     用系统平衡方程反算，并标记 residual=True；
     其中草地饲料改由“存栏 × 排泄系数”的粪磷闭合反推，PUE 由输入变为输出；
  3. 系统边界只统计跨边界输入/输出，内部转移不计入全系统输入输出；
  4. 守恒相对误差 = |Σ输入 − Σ输出 − Δ存量| / (Σ输入 + 1e-6) < 1e-4。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .acs_model import ACSModel
from .params import coeff

# 节点类型
INTERNAL, SOURCE, SINK, STOCK = "internal", "source", "sink", "stock"


@dataclass
class Flow:
    source: str
    target: str
    value: float
    note: str = ""
    residual: bool = False


class FlowLedger:
    def __init__(self) -> None:
        self.kind: dict[str, str] = {}
        self.flows: list[Flow] = []
        self.stock_delta: dict[str, float] = {}

    def node(self, name: str, kind: str = INTERNAL) -> str:
        self.kind.setdefault(name, kind)
        return name

    def add(self, source: str, target: str, value: float,
            note: str = "", residual: bool = False) -> None:
        if value < -1e-9:
            raise ValueError(f"负流量：{source}->{target} = {value:.6f}")
        self.node(source)
        self.node(target)
        self.flows.append(Flow(source, target, float(value), note, residual))

    def set_stock(self, name: str, delta: float) -> None:
        self.kind[name] = STOCK
        self.stock_delta[name] = float(delta)

    # ------------------------------------------------------------ 校验
    def node_balance(self) -> dict[str, dict[str, float]]:
        out = {}
        for name in self.kind:
            if self.kind[name] != INTERNAL:
                continue
            inflow = sum(f.value for f in self.flows if f.target == name)
            outflow = sum(f.value for f in self.flows if f.source == name)
            out[name] = {
                "in": inflow, "out": outflow,
                "residual": inflow - outflow,
                "rel_err": abs(inflow - outflow) / (inflow + 1e-6),
            }
        return out

    def global_balance(self) -> dict[str, float]:
        total_in = sum(f.value for f in self.flows
                       if self.kind.get(f.source) == SOURCE)
        total_out = sum(f.value for f in self.flows
                        if self.kind.get(f.target) == SINK)
        stock = sum(self.stock_delta.values())
        rel = abs(total_in - total_out - stock) / (total_in + 1e-6)
        return {"total_in": total_in, "total_out": total_out,
                "stock_change": stock, "rel_err": rel}

    def verify(self, tolerance: float = 1e-4, strict: bool = True) -> dict:
        nodes = self.node_balance()
        glob = self.global_balance()
        worst = max((v["rel_err"] for v in nodes.values()), default=0.0)
        ok = glob["rel_err"] < tolerance and worst < tolerance
        if strict and not ok:
            raise AssertionError(
                f"质量守恒未通过：全系统相对误差 {glob['rel_err']:.6e}，"
                f"最差节点 {worst:.6e}（阈值 {tolerance:.0e}）")
        return {"passed": ok, "global": glob, "nodes": nodes,
                "worst_node_rel_err": worst, "tolerance": tolerance}


# ====================================================================
class PhosphorusSystemModel:
    """全球人为磷循环五系统模型。"""

    def __init__(self, bundle, coefficients):
        self.b = bundle
        self.coef = coefficients
        self.acs: ACSModel | None = None
        self.notes: dict = {}

    # ------------------------------------------------------------------
    def build(self, fert_reduction: float = 0.0,
              manure_rate: float | None = None,
              struvite_rate: float | None = None,
              demand_scale: float = 1.0) -> FlowLedger:
        b, c = self.b, self.coef
        manure_rate = coeff(c, "beta3") if manure_rate is None else manure_rate
        struvite_rate = coeff(c, "struvite_base") if struvite_rate is None else struvite_rate

        # ---------------- 活动量（随需求情景缩放）
        crop = b.crop_p * demand_scale
        animal = b.animal_p * demand_scale
        fert_base = b.fertilizer["Agricultural Use"] * demand_scale
        fert_imp = b.fertilizer["Import Quantity"] * demand_scale
        fert_exp = b.fertilizer["Export Quantity"] * demand_scale
        stock_ratio = (b.fertilizer["Production"] + b.fertilizer["Import Quantity"]
                       - b.fertilizer["Export Quantity"]
                       - b.fertilizer["Agricultural Use"])

        # ---------------- LBS 畜禽养殖
        crop_feed = crop * coeff(c, "beta2")
        pue_ref = coeff(c, "pue_lbs")
        if b.manure_p_mt:
            # 存栏 × 排泄系数得到粪磷（山羊缺系数，已排除，见 missing_data.md）。
            # 粪磷为独立观测型输入，故饲料需求由 LBS 平衡反推，
            # PUE 由“假设参数”转为校核输出。
            animal_waste = b.manure_p_mt * demand_scale
            feed_total = animal + animal_waste
            feed_add = feed_total * coeff(c, "beta4")
            grass_feed = feed_total - crop_feed - feed_add
            if grass_feed < 0:
                raise ValueError(
                    f"粪磷闭合后草地饲料为负（{grass_feed:.3f} Mt P），"
                    "请检查 β2/β4 与粪磷口径")
            lbs_basis = "存栏×排泄系数（QCL_2025）"
        else:
            feed_total = animal / pue_ref
            feed_add = feed_total * coeff(c, "beta4")
            grass_feed = feed_total - crop_feed - feed_add
            if grass_feed < 0:                  # 饲料不足时按作物饲料口径回退
                grass_feed = 0.0
                feed_total = crop_feed + feed_add
            animal_waste = feed_total - animal
            lbs_basis = f"PUE={pue_ref} 反算（缺存栏粪磷，回退）"
        pue_model = animal / feed_total
        manure_recycled = animal_waste * manure_rate
        manure_loss = animal_waste - manure_recycled
        manure_base = animal_waste * coeff(c, "beta3")
        grass_uptake = (grass_feed * 1e9 / b.grassland_ha
                        if b.grassland_ha else None)

        # ---------------- RCS 居民消费
        intake = b.food_p_percap * b.population * demand_scale / 1e9
        phi1 = coeff(c, "phi1") + coeff(c, "phi3")
        phi2 = coeff(c, "phi2")
        crop_food = intake * phi1
        animal_food = intake * phi2
        other_food = intake - crop_food - animal_food
        excretion = coeff(c, "beta5") * b.population * demand_scale / 1e9
        recovered = excretion * struvite_rate
        recovered_base = excretion * coeff(c, "struvite_base")
        wastewater = excretion - recovered
        food_waste = max(intake - excretion, 0.0)

        # ---------------- 有机肥替代化肥
        # 新增的粪肥还田与鸟粪石回收按替代系数抵减矿物磷肥需求，
        # 替代系数取值 0.5（假设），在 coefficients.csv 中标注。
        sub = coeff(c, "manure_substitution")
        delta_org = max(manure_recycled - manure_base, 0.0) + max(recovered - recovered_base, 0.0)
        fert_use = max(fert_base * (1 - fert_reduction) - sub * delta_org, 0.0)
        fert_stock = stock_ratio * demand_scale
        fert_prod = fert_use + fert_exp - fert_imp + fert_stock

        # ---------------- PMS 磷矿开采
        alpha3 = coeff(c, "alpha3")
        # 三种口径并列，仅最高等级口径进入模型：
        #   1) 同版本 MYB 成套 P2O5（同表矿石量），质量最好；
        #   2) DS140 实物量 × 31% 品位 × 0.4364，实物量 proxy；
        #   3) 课程包 USGS 实物量表 × 品位（回退）。
        rock_from_grade = b.rock_mt * alpha3 * coeff(c, "alpha1")   # Mt P
        rock_ds140_p = (b.rock_ds140_mt * alpha3 * coeff(c, "alpha1")
                        if b.rock_ds140_mt else None)
        if b.rock_myb:
            rock_obs = b.rock_myb["p_Mt"]
            rock_basis = f"MYB 成套 P2O5×0.4364（{b.rock_myb['source']}）"
        elif rock_ds140_p is not None:
            rock_obs = rock_ds140_p
            rock_basis = "DS140 实物量×31%品位×0.4364"
        else:
            rock_obs = rock_from_grade
            rock_basis = "课程包 USGS 实物量×31%品位×0.4364"
        loss_ratio = (coeff(c, "alpha4") * coeff(c, "alpha5")
                      + coeff(c, "alpha6") * coeff(c, "alpha7")
                      + coeff(c, "alpha8") * coeff(c, "alpha9"))
        cis_input = fert_prod / coeff(c, "eta_cis")
        rock_required = cis_input * (1 + loss_ratio)
        rock_gap = max(rock_required - rock_obs, 0.0)
        rock_mined = rock_obs + rock_gap
        concentrate = rock_mined / (1 + loss_ratio)
        mining_loss = rock_mined - concentrate

        # ---------------- CIS 磷化工
        nonfert = max(cis_input * coeff(c, "nonfert_share") - feed_add, 0.0)
        cis_loss = cis_input - fert_prod - nonfert - feed_add

        # ---------------- ACS 农田
        seed = b.seed_p_mt * demand_scale if b.seed_p_mt is not None else None
        self.acs = ACSModel(
            crop_params={"harvest_p": crop},
            system_params={
                "cropland_ha": b.cropland_ha,
                "fertilizer_p": fert_use,
                "manure_p": manure_recycled + recovered,
                "seed_p": seed,
            },
            coefficients=c,
        )
        acs = self.acs.run()

        crop_other = crop - crop_feed - crop_food
        animal_other = animal - animal_food
        if crop_other < 0 or animal_other < 0:
            raise ValueError("作物/动物产品分配为负，请检查 β2、φ1、φ2 口径")

        # ---------------- 组装台账
        L = FlowLedger()
        # 边界节点
        L.node("磷矿储量（开采）", SOURCE)
        L.node("磷矿缺口（USGS未覆盖/进口）", SOURCE)
        L.node("化肥进口", SOURCE)
        L.node("大气沉降", SOURCE)
        L.node("种子磷（FAOSTAT 官方估计）", SOURCE)
        L.node("草地放牧饲料（由粪磷闭合反算）", SOURCE)
        L.node("其他食物（水产品等，缺数据）", SOURCE)
        L.node("地表水", SINK)
        L.node("废弃物与加工损失", SINK)
        L.node("工业用磷", SINK)
        L.node("土壤遗留磷", STOCK)
        L.node("化肥库存", STOCK)

        # 系统节点
        for n in ["PMS 磷矿开采", "CIS 磷化工", "化肥池", "ACS 农田",
                  "作物收获", "LBS 畜禽养殖", "RCS 居民消费", "污水处理"]:
            L.node(n, INTERNAL)

        # PMS -> CIS
        L.add("磷矿储量（开采）", "PMS 磷矿开采", rock_obs)
        L.add("磷矿缺口（USGS未覆盖/进口）", "PMS 磷矿开采", rock_gap,
              note="观测矿量低于按肥料产量反推的需求，差额为残差（含贸易与口径差）",
              residual=True)
        L.add("PMS 磷矿开采", "CIS 磷化工", concentrate)
        L.add("PMS 磷矿开采", "废弃物与加工损失", mining_loss,
              note="砂废弃物/矿泥/尾矿损失", residual=True)

        # CIS
        L.add("CIS 磷化工", "化肥池", fert_prod)
        L.add("CIS 磷化工", "LBS 畜禽养殖", feed_add, note="饲料添加剂")
        L.add("CIS 磷化工", "工业用磷", nonfert, note="非肥料用磷产品")
        L.add("CIS 磷化工", "废弃物与加工损失", cis_loss,
              note="磷石膏及加工损失", residual=True)

        # 化肥池
        L.add("化肥进口", "化肥池", fert_imp)
        L.add("化肥池", "ACS 农田", fert_use)
        L.add("化肥池", "工业用磷", fert_exp, note="化肥出口")
        L.add("化肥池", "化肥库存", fert_stock, note="库存变化")
        L.set_stock("化肥库存", fert_stock)

        # ACS
        L.add("大气沉降", "ACS 农田", acs.deposition)
        if seed is not None:
            L.add("种子磷（FAOSTAT 官方估计）", "ACS 农田", seed,
                  note="FAOSTAT Cropland Nutrient Balance 种子磷（ESB_2025）")
        L.add("LBS 畜禽养殖", "ACS 农田", manure_recycled, note="粪肥还田")
        L.add("污水处理", "ACS 农田", recovered, note="鸟粪石回收还田")
        L.add("ACS 农田", "作物收获", acs.harvest)
        L.add("ACS 农田", "废弃物与加工损失", acs.residue_waste, note="秸秆未还田")
        L.add("ACS 农田", "地表水", acs.water_loss, note="排水+淋溶")
        if acs.soil_accumulation >= 0:
            L.add("ACS 农田", "土壤遗留磷", acs.soil_accumulation, note="存量累积")
        else:   # 负值代表土壤磷耗竭，方向反转
            L.add("土壤遗留磷", "ACS 农田", -acs.soil_accumulation,
                  note="土壤磷耗竭（存量下降）")
        L.set_stock("土壤遗留磷", acs.soil_accumulation)

        # 作物收获
        L.add("作物收获", "LBS 畜禽养殖", crop_feed, note="饲料粮")
        L.add("作物收获", "RCS 居民消费", crop_food, note="植物性食物")
        L.add("作物收获", "废弃物与加工损失", crop_other, note="加工/流通/浪费")

        # LBS
        L.add("草地放牧饲料（由粪磷闭合反算）", "LBS 畜禽养殖", grass_feed,
              note=f"{lbs_basis}；草地单产 proxy 仅作区间核对", residual=True)
        L.add("LBS 畜禽养殖", "RCS 居民消费", animal_food, note="动物性食物")
        L.add("LBS 畜禽养殖", "废弃物与加工损失", manure_loss, note="粪污未利用")
        L.add("LBS 畜禽养殖", "废弃物与加工损失", animal_other, note="屠宰/加工损失")

        # RCS
        L.add("其他食物（水产品等，缺数据）", "RCS 居民消费", other_food,
              note="膳食磷中未覆盖的食物组", residual=True)
        L.add("RCS 居民消费", "污水处理", excretion, note="人体排泄")
        L.add("RCS 居民消费", "废弃物与加工损失", food_waste, note="餐厨/家庭浪费")
        L.add("污水处理", "地表水", wastewater, note="处理后排放")

        self.notes = {
            "lbs_basis": lbs_basis,
            "lbs_pue_model": pue_model,
            "animal_waste_Mt": animal_waste,
            "grass_feed_Mt": grass_feed,
            "grass_uptake_kg_ha": grass_uptake,
            "grass_proxy": b.grass_proxy,
            "manure_missing_species": (b.livestock or {}).get("missing_species", []),
            "rock_basis": rock_basis,
            "rock_obs_Mt": rock_obs,
            "rock_grade_Mt": rock_from_grade,
            "rock_ds140_Mt": rock_ds140_p,
            "rock_gap_Mt": rock_gap,
            "seed_Mt": seed,
        }
        return L

    # ------------------------------------------------------------------
    def verify(self, ledger: FlowLedger | None = None, tolerance: float = 1e-4) -> dict:
        ledger = ledger or self.build()
        return ledger.verify(tolerance)
