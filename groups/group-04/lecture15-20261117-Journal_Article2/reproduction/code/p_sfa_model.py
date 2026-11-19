# -*- coding: utf-8 -*-
"""磷物质流分析（P_SFA）对象模型：子系统类 + 全局守恒 + 情景引擎 + 回归。

设计要点
1. 每个子系统独立记账（inflow / outflow），库存变化由残差项吸收，保证节点闭合；
2. 全局闭合以「终端汇 = 系统输入」检验，相对误差目标 < 1e-4（本实现可达 1e-15）；
3. 情景引擎以论文 Fig. 4 的锚点为标定，按饱和-耦合形式给出中间强度响应，
   并支持拉丁超立方抽样下的回归识别（含交互项）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from p_config import P_2022, SCEN_2050, SEED


class Subsystem:
    """磷流子系统基类：输入/输出/库存三本账。"""

    def __init__(self, name: str):
        self.name = name
        self.inflow: dict[str, float] = {}
        self.outflow: dict[str, float] = {}

    def add_in(self, key: str, value: float) -> None:
        self.inflow[key] = float(value)

    def add_out(self, key: str, value: float) -> None:
        self.outflow[key] = float(value)

    @property
    def total_in(self) -> float:
        return sum(self.inflow.values())

    @property
    def total_out(self) -> float:
        return sum(self.outflow.values())

    @property
    def stock(self) -> float:
        """净库存变化（正=累积）。闭合子系统应为 0。"""
        return self.total_in - self.total_out

    def check(self, tol: float = 1e-9) -> float:
        rel = abs(self.stock) / max(self.total_in, 1e-12)
        if rel > tol:
            raise AssertionError(f"{self.name} 未闭合：Δ={self.stock:.6e}（相对 {rel:.2e}）")
        return rel


class PFlowModel:
    """2022 年全球磷物质流快照（6 个子系统 + 水环境节点）。"""

    def __init__(self, p: dict | None = None):
        self.p = dict(P_2022 if p is None else p)
        self.sub: dict[str, Subsystem] = {}
        self.links: list[tuple[str, str, float, str]] = []  # (source, target, value, 类别)
        self._build()

    # ---------- 构建 ----------
    def _build(self) -> None:
        p = self.p
        mining = Subsystem("磷矿开采")
        mining.add_in("原矿磷", p["mined"])
        mining.add_out("矿石→磷化工", p["ore_to_cis"])
        mining.add_out("尾矿损失", p["mined"] - p["ore_to_cis"])

        cis = Subsystem("磷化工")
        cis.add_in("矿石磷", p["ore_to_cis"])
        cis.add_out("化肥", p["fert"])
        cis.add_out("工业磷", p["industrial"])
        cis.add_out("磷石膏", p["ore_to_cis"] - p["fert"] - p["industrial"])

        crop = Subsystem("农田")
        for k, v in [("化肥", p["fert"]), ("粪肥还田", p["manure_recycle"]),
                     ("污泥回用", p["sludge_recycle"]), ("秸秆还田", p["straw_return"]),
                     ("大气沉降", p["deposition"]), ("种子", p["seed"])]:
            crop.add_in(k, v)
        crop.add_out("作物收获", p["harvest"])
        crop.add_out("径流流失", p["runoff"])
        crop.add_out("土壤遗留", crop.total_in - p["harvest"] - p["runoff"])  # 残差

        live = Subsystem("畜禽养殖")
        for k, v in [("作物饲料", p["feed_crop"]), ("工业饲料", p["ind_feed"]),
                     ("农副产物", p["byproduct"]), ("牧草", p["forage"])]:
            live.add_in(k, v)
        live.add_out("动物产品", p["animal_products"])
        live.add_out("粪肥还田", p["manure_recycle"])
        live.add_out("牧场土壤", p["pasture_soil"])
        live.add_out("田间流失", p["field_loss"])
        live.add_out("粪污处理", p["manure_waste"])
        manure = live.total_in - p["animal_products"]
        live.outflow["其他粪污损失"] = manure - sum(
            v for k, v in live.outflow.items() if k != "动物产品")

        cons = Subsystem("居民消费")
        cons.add_in("作物食物", p["food"])
        cons.add_in("动物产品", p["animal_products"])
        cons.add_out("人体摄入", p["eaten"])
        cons.add_out("食物浪费", p["food_waste"])

        wts = Subsystem("污水处理")
        wts.add_in("生活污水", p["ww"])
        wts.add_in("粪污", p["manure_waste"])
        wts.add_in("食物垃圾", p["food_waste"])
        wts.add_out("污泥回用", p["sludge_recycle"])
        wts.add_out("填埋", p["landfill"])
        wts.add_out("尾水排放", wts.total_in - p["sludge_recycle"] - p["landfill"])

        water = Subsystem("水环境")
        water.add_in("农田径流", p["runoff"])
        water.add_in("粪肥流失", p["field_loss"])
        water.add_in("农村直排", p["rural_direct"])
        water.add_in("尾水排放", wts.outflow["尾水排放"])
        water.add_out("入海输出", p["outflow"])
        water.add_out("沉积埋藏", water.total_in - p["outflow"])

        self.sub = {s.name: s for s in (mining, cis, crop, live, cons, wts, water)}
        self._make_links()

    def _make_links(self) -> None:
        s = self.sub
        self.links = [
            ("磷矿开采", "磷化工", s["磷化工"].inflow["矿石磷"], "矿石"),
            ("磷矿开采", "尾矿", s["磷矿开采"].outflow["尾矿损失"], "损失"),
            ("磷化工", "农田", s["磷化工"].outflow["化肥"], "化肥"),
            ("磷化工", "工业利用", s["磷化工"].outflow["工业磷"], "工业"),
            ("磷化工", "磷石膏", s["磷化工"].outflow["磷石膏"], "损失"),
            ("大气沉降", "农田", s["农田"].inflow["大气沉降"], "自然输入"),
            ("种子", "农田", s["农田"].inflow["种子"], "自然输入"),
            ("进料(进口)", "畜禽养殖", s["畜禽养殖"].inflow["工业饲料"] + s["畜禽养殖"].inflow["农副产物"], "贸易"),
            ("草地", "畜禽养殖", s["畜禽养殖"].inflow["牧草"], "自然输入"),
            ("农田", "作物收获", s["农田"].outflow["作物收获"], "作物"),
            ("农田", "水环境", s["农田"].outflow["径流流失"], "损失"),
            ("农田", "土壤遗留", s["农田"].outflow["土壤遗留"], "累积"),
            ("作物收获", "居民消费", s["居民消费"].inflow["作物食物"], "食物"),
            ("作物收获", "畜禽养殖", s["畜禽养殖"].inflow["作物饲料"], "饲料"),
            ("作物收获", "农田", s["农田"].inflow["秸秆还田"], "秸秆"),
            ("畜禽养殖", "居民消费", s["畜禽养殖"].outflow["动物产品"], "食物"),
            ("畜禽养殖", "农田", s["畜禽养殖"].outflow["粪肥还田"], "粪肥"),
            ("畜禽养殖", "牧场土壤", s["畜禽养殖"].outflow["牧场土壤"], "累积"),
            ("畜禽养殖", "水环境", s["畜禽养殖"].outflow["田间流失"], "损失"),
            ("畜禽养殖", "污水处理", s["畜禽养殖"].outflow["粪污处理"], "粪污"),
            ("畜禽养殖", "其他损失", s["畜禽养殖"].outflow["其他粪污损失"], "损失"),
            ("居民消费", "污水处理", s["居民消费"].outflow["食物浪费"], "垃圾"),
            ("居民消费", "污水处理", s["污水处理"].inflow["生活污水"], "污水"),
            ("居民消费", "水环境", s["居民消费"].outflow["人体摄入"]
             - s["污水处理"].inflow["生活污水"], "直排"),
            ("污水处理", "农田", s["污水处理"].outflow["污泥回用"], "回用"),
            ("污水处理", "填埋", s["污水处理"].outflow["填埋"], "损失"),
            ("污水处理", "水环境", s["污水处理"].outflow["尾水排放"], "排放"),
            ("水环境", "沉积埋藏", s["水环境"].outflow["沉积埋藏"], "累积"),
            ("水环境", "入海输出", s["水环境"].outflow["入海输出"], "损失"),
            ("工业利用", "工业库存", s["磷化工"].outflow["工业磷"], "存量"),
        ]
        self.links = [l for l in self.links if l[2] > 1e-9]

    # ---------- 校验 ----------
    def mass_balance(self) -> dict:
        sub_err = {k: v.check() for k, v in self.sub.items()}
        inputs = (self.p["mined"] + self.p["deposition"] + self.p["seed"]
                  + self.p["forage"] + self.p["import_feed"])
        sinks = sum(v for _, t, v, _ in self.links
                    if t in {"尾矿", "磷石膏", "土壤遗留", "牧场土壤", "其他损失",
                             "填埋", "沉积埋藏", "入海输出", "工业库存"})
        rel = abs(inputs - sinks) / inputs
        if rel > 1e-4:
            raise AssertionError(f"全局未闭合：输入 {inputs:.4f} vs 汇 {sinks:.4f}（{rel:.2e}）")
        return dict(inputs=inputs, sinks=sinks, rel_error=rel,
                    subsystem_rel_error=max(sub_err.values()))

    def to_json(self) -> dict:
        return dict(
            year=2022, unit="Mt P/a",
            p=self.p,
            subsystems={k: dict(inflow=v.inflow, outflow=v.outflow,
                                stock=round(v.stock, 10)) for k, v in self.sub.items()},
            links=[dict(source=a, target=b, value=round(c, 6), kind=d)
                   for a, b, c, d in self.links],
            mass_balance={k: float(f"{v:.3e}") for k, v in self.mass_balance().items()},
            indicators=dict(
                crop_pue=self.p["harvest"] / self.sub["农田"].total_in,
                fertilizer_share=self.p["fert"] / self.sub["农田"].total_in,
                legacy_share=(self.sub["农田"].total_in - self.p["harvest"]
                              - self.p["runoff"]) / self.sub["农田"].total_in,
                livestock_pue=self.p["animal_products"] / self.sub["畜禽养殖"].total_in,
                water_pue=1 - self.p["outflow"] / self.sub["水环境"].total_in,
            ),
        )


# ---------- 2050 情景引擎 ----------
class ScenarioEngine:
    """以论文锚点标定的饱和-耦合情景模型。

    e_i(x) = e_i,max · x / x_ref      （线性饱和至锚点强度）
    综合损失削减 = 1 − Π(1−e_i) + κ·e_r·e_p （κ 为系统耦合项，由 S5 反演）
    """

    def __init__(self, bau: dict | None = None):
        c = SCEN_2050
        self.bau = dict(bau) if bau else dict(c["bau"])
        self.anchors = c
        self.kappa = c["synergy"]

    def efficacy(self, reduce_pct: float, replace_pct: float, recycle_pct: float,
                 noise: np.ndarray | None = None) -> dict:
        e_r_loss = 0.39 * reduce_pct / 20.0
        e_p_loss = 0.77 * replace_pct / 75.0
        e_c_loss = 0.18 * recycle_pct / 100.0
        e_r_npr = 0.096 * reduce_pct / 20.0
        e_p_npr = 0.2215 * replace_pct / 75.0
        e_c_npr = 0.06 * recycle_pct / 100.0
        e_p_cfr = 0.769 * replace_pct / 75.0
        e_r_cfr = 0.200 * reduce_pct / 20.0
        e_c_cfr = 0.06 * recycle_pct / 100.0   # 鸟粪石回收的磷直接替代矿物磷肥
        e = dict(r_loss=e_r_loss, p_loss=e_p_loss, c_loss=e_c_loss,
                 r_npr=e_r_npr, p_npr=e_p_npr, c_npr=e_c_npr,
                 p_cfr=e_p_cfr, r_cfr=e_r_cfr, c_cfr=e_c_cfr)
        if noise is not None:
            for k in ("r_loss", "p_loss", "c_loss"):
                e[k] *= noise
        return e

    def evaluate(self, reduce_pct: float, replace_pct: float, recycle_pct: float,
                 noise: np.ndarray | None = None) -> dict:
        e = self.efficacy(reduce_pct, replace_pct, recycle_pct, noise)
        loss_cut = 1 - (1 - e["r_loss"]) * (1 - e["p_loss"]) * (1 - e["c_loss"]) \
            + self.kappa * e["r_loss"] * e["p_loss"]
        loss_cut = min(max(loss_cut, 0.0), 0.97)
        npr_cut = min(1 - (1 - e["r_npr"]) * (1 - e["p_npr"]) * (1 - e["c_npr"])
                      + 0.8 * e["r_npr"] * e["p_npr"], 0.97)
        cfr_cut = min(1 - (1 - e["r_cfr"]) * (1 - e["p_cfr"]) * (1 - e["c_cfr"]), 1.0)
        return dict(
            reduce_pct=reduce_pct, replace_pct=replace_pct, recycle_pct=recycle_pct,
            npr=self.bau["npr"] * (1 - npr_cut),
            npr_cut=npr_cut,
            cfr=self.bau["cfr"] * (1 - cfr_cut),
            cfr_cut=cfr_cut,
            loss=self.bau["loss"] * (1 - loss_cut),
            loss_cut=loss_cut,
        )

    def named_scenarios(self) -> pd.DataFrame:
        cases = [("2050 BAU", 0, 0, 0), ("S2.2 减施20%", 20, 0, 0),
                 ("S4.3 粪污还田75%", 0, 75, 0), ("S4.5 鸟粪石回收60%", 0, 0, 60),
                 ("3R 协同", 20, 75, 60), ("3R 全强度", 30, 100, 100)]
        rows = []
        for name, xr, xp, xc in cases:
            row = dict(name=name)
            row.update(self.evaluate(xr, xp, xc))
            rows.append(row)
        df = pd.DataFrame(rows)
        for c in ("npr", "cfr", "loss"):
            df[c + "_vs_bau"] = df[c] / self.bau[c] - 1
        return df


# ---------- 交叉敏感性回归 ----------
def run_regression(n: int = 300, seed: int = SEED) -> tuple[pd.DataFrame, dict]:
    """拉丁超立方抽样 + 含交互项 OLS（标准化系数）。"""
    from scipy.stats import qmc
    import statsmodels.api as sm

    eng = ScenarioEngine()
    rng = np.random.default_rng(seed)
    sampler = qmc.LatinHypercube(d=3, seed=seed)
    u = sampler.random(n)
    reduce_pct = u[:, 0] * 30.0
    replace_pct = u[:, 1] * 100.0
    recycle_pct = u[:, 2] * 100.0
    noise = rng.lognormal(mean=0.0, sigma=0.08, size=n)  # 参数不确定性 ±8%

    rec = []
    for xr, xp, xc, nz in zip(reduce_pct, replace_pct, recycle_pct, noise):
        r = eng.evaluate(xr, xp, xc, noise=nz)
        rec.append(dict(reduce=xr, replace=xp, recycle=xc,
                        npr_cut=r["npr_cut"], loss_cut=r["loss_cut"]))
    df = pd.DataFrame(rec)

    # 中心化后构造交互项
    z = (df[["reduce", "replace", "recycle"]] - df[["reduce", "replace", "recycle"]].mean()) \
        / df[["reduce", "replace", "recycle"]].std(ddof=0)
    X = pd.DataFrame({
        "Reduce": z["reduce"], "Replace": z["replace"], "Recycle": z["recycle"],
        "Reduce×Replace": z["reduce"] * z["replace"],
        "Reduce×Recycle": z["reduce"] * z["recycle"],
        "Replace×Recycle": z["replace"] * z["recycle"],
    })
    y = df["loss_cut"] * 100
    model = sm.OLS(y, sm.add_constant(X)).fit()
    out = pd.DataFrame({
        "term": model.params.index,
        "coef": model.params.values,
        "std_err": model.bse.values,
        "t": model.tvalues.values,
        "p": model.pvalues.values,
    })
    # 任务书 4.4 要求输出「交互类型」：p<0.05 时 β>0 协同、β<0 拮抗，否则不显著
    is_inter = out["term"].str.contains("×")
    out["type"] = "主效应"
    out.loc[is_inter, "type"] = np.where(
        out.loc[is_inter, "p"] >= 0.05, "无显著交互",
        np.where(out.loc[is_inter, "coef"] > 0, "协同增强", "拮抗削弱"))
    out.loc[out["term"] == "const", "type"] = "常数项"
    summary = dict(r2=float(model.rsquared), r2_adj=float(model.rsquared_adj),
                   f_stat=float(model.fvalue), f_pvalue=float(model.f_pvalue), n=n,
                   y_mean=float(y.mean()), y_std=float(y.std(ddof=0)))
    return out, summary


def predict_curve(eng: ScenarioEngine, reduce_pct: float, n: int = 101) -> pd.DataFrame:
    """固定减施强度，扫描粪肥还田与回收强度，用于二维响应面。"""
    xs = np.linspace(0, 100, n)
    rows = []
    for xp in xs:
        r0 = eng.evaluate(reduce_pct, xp, 0)
        r1 = eng.evaluate(reduce_pct, xp, 60)
        rows.append(dict(replace=xp, loss_cut_no_recycle=r0["loss_cut"],
                         loss_cut_with_recycle=r1["loss_cut"]))
    return pd.DataFrame(rows)
