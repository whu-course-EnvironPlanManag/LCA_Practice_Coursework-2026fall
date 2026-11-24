"""论文关键指标与课程计算结果的对照表。

文献值来自任务书 5.1–5.4 节（Liu et al. 2026）；课程值来自本模型输出。
偏差仅作技术对照，不为了对齐而修改模型参数。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .anchors import cumulative_rock_p
from .data_io import load_fertilizer


def _pct(model, paper):
    if paper in (None, 0) or model is None:
        return None
    return (model / paper - 1.0) * 100.0


def build_comparison(bundle, scenarios: pd.DataFrame, data_dir: Path,
                     ledger_2022=None, extra_dir: Path | None = None,
                     coefficients=None) -> pd.DataFrame:
    fert_1961 = load_fertilizer(data_dir, 1961)["Agricultural Use"]
    bau = scenarios.set_index("情景").loc["2050 BAU"]
    reduce_row = scenarios.set_index("情景").loc["2050 化肥减施20%"]
    combined = scenarios.set_index("情景").loc["2050 综合3R"]
    base = scenarios.set_index("情景").loc["2050 BAU"]

    acs = bundle.fertilizer["Agricultural Use"]
    if ledger_2022 is not None:
        acs_in = sum(f.value for f in ledger_2022.flows if f.target == "ACS 农田")
        fert_in = sum(f.value for f in ledger_2022.flows
                      if f.target == "ACS 农田" and f.source == "化肥池")
        lbs_in = sum(f.value for f in ledger_2022.flows
                     if f.target == "LBS 畜禽养殖")
        pue_model = bundle.animal_p / lbs_in * 100.0 if lbs_in else None
    else:
        acs_in, fert_in = acs + 12.736 + 0.629, acs
        pue_model = None
    acs_share = fert_in / acs_in * 100.0

    cum = (cumulative_rock_p(extra_dir, coefficients)
           if extra_dir is not None and coefficients is not None else {})
    rock_note, rock_value = "未复现", None
    if cum:
        rock_value = round(cum["partial_Mt_P"], 1)
        rock_note = (
            f"DS140 仅覆盖 {cum['covered_years']}/62 年（缺 1999–2020），"
            f"夹逼区间 {cum.get('bracket_low_Mt_P', float('nan')):.0f}–"
            f"{cum.get('bracket_high_Mt_P', float('nan')):.0f} Mt P；"
            "不与 1153 Mt P 直接比较")

    rows = [
        {
            "指标": "1961 年全球矿物磷肥施用",
            "文献值": 4.9, "单位": "Mt P", "课程计算值": round(fert_1961, 2),
            "相对偏差(%)": round(_pct(fert_1961, 4.9), 1),
            "可比性": "可比", "说明": "FAOSTAT 与论文基准一致（偏差 <3%）",
        },
        {
            "指标": "2022 年全球矿物磷肥施用",
            "文献值": 20.5, "单位": "Mt P", "课程计算值": round(acs, 2),
            "相对偏差(%)": round(_pct(acs, 20.5), 1),
            "可比性": "口径差异",
            "说明": "FAOSTAT 最新为 2021 年 24.64；论文值偏低，未做人为调整",
        },
        {
            "指标": "农田化肥占 ACS 总输入比例",
            "文献值": 64.0, "单位": "%", "课程计算值": round(acs_share, 1),
            "相对偏差(%)": round(acs_share - 64.0, 1),
            "可比性": "可比",
            "说明": f"论文表述为“64% 以上”，模型为 {acs_share:.1f}%",
        },
        {
            "指标": "LBS 磷利用效率",
            "文献值": 23.0, "单位": "%",
            "课程计算值": round(pue_model, 1) if pue_model is not None else 23.0,
            "相对偏差(%)": round(pue_model - 23.0, 1) if pue_model is not None else 0.0,
            "可比性": "可比（模型输出）" if pue_model is not None else "不可独立复现",
            "说明": ("由存栏×排泄系数得到粪磷后闭合饲料需求，PUE 为输出而非输入；"
                     "山羊缺系数使该值偏高约 2 个百分点，按绵羊系数估算为 23.3%"
                     if pue_model is not None
                     else "0.23 作为饲料反算参数输入，非独立观测结果"),
        },
        {
            "指标": "化肥减施 20% 对 2050 磷矿需求的影响",
            "文献值": -17.0, "单位": "%",
            "课程计算值": round(reduce_row["磷矿需求(Mt P)相对BAU(%)"], 1),
            "相对偏差(%)": None, "可比性": "情景相近",
            "说明": "论文 S2.3 为综合效率情景；课程仅减施化肥，数值接近但不等价",
        },
        {
            "指标": "粪便循环情景对 2050 磷矿需求的影响",
            "文献值": -22.1, "单位": "%",
            "课程计算值": round(
                (scenarios.set_index("情景").loc["2050 粪便堆肥利用率75%", "磷矿需求(Mt P)"]
                 / base["磷矿需求(Mt P)"] - 1) * 100, 1),
            "相对偏差(%)": None, "可比性": "不可比",
            "说明": "论文 S4.3 为全链条粪便循环；课程仅把利用率由 67% 提至 75%",
        },
        {
            "指标": "综合管理情景对 2050 磷矿需求的影响",
            "文献值": -97.0, "单位": "%",
            "课程计算值": round(combined["磷矿需求(Mt P)相对BAU(%)"], 1),
            "相对偏差(%)": None, "可比性": "不可比",
            "说明": "论文 S5 含饲料效率、饮食结构等全部措施；课程仅 3R 三项",
        },
        {
            "指标": "1961–2022 累计磷矿开采输入",
            "文献值": 1153.0, "单位": "Mt P", "课程计算值": rock_value,
            "相对偏差(%)": None,
            "可比性": "部分覆盖" if cum else "未复现",
            "说明": rock_note,
        },
    ]
    return pd.DataFrame(rows)
