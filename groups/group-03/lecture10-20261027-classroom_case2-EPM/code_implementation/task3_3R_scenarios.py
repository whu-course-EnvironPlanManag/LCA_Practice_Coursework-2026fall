# -*- coding: utf-8 -*-
"""
任务 3：2050 年"3R"情景模拟与交叉敏感性回归（真实数据基线版）
- 以 2022 年真实全球农产品磷移除量（xlsx）为基线；
- 2050 年 BAU：按历史 1961–2022 增长趋势外推；
- "3R" 政策：Reduce 化学施肥 -20%，Replace 粪便回收率 +75%，Recycle 污水回收 +60%；
- 流域级交叉敏感性回归：政策变量（含交互项）对 PUE 的影响，
  输出弹性系数、p 值；Plotly 输出 2050 年情景对比仪表盘 HTML。
"""
 
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import statsmodels.formula.api as smf
 
def find_xlsx() -> str:
    """自动查找磷结果 xlsx，兼容全角/半角括号与任意工作目录。"""
    import glob, os
    patterns = [
        "Agricultural products_P_result_national*level*1961-2022*.xlsx",
        "**/Agricultural products_P_result_national*level*1961-2022*.xlsx",
        "**/Origin data/Agricultural products_P_result*.xlsx",
    ]
    for p in patterns:
        hits = glob.glob(p, recursive=True)
        if hits:
            return hits[0]
    raise FileNotFoundError(
        "未找到磷结果 xlsx，请确认文件名，或将其完整路径赋给 XLSX_PATH")
 
 
XLSX_PATH = find_xlsx()
YEAR = 2050
N_BASINS = 60
RNG = np.random.default_rng(42)
 
 
def historical_baseline() -> pd.Series:
    """真实数据：1961–2022 全球逐年磷移除量（tons P → kt P）。"""
    x = pd.read_excel(XLSX_PATH, sheet_name=0)
    year_cols = [c for c in x.columns if isinstance(c, (int, np.integer))]
    return x[year_cols].sum().sort_index() / 1000.0
 
 
def extrapolate_bau(hist: pd.Series) -> float:
    """按近 30 年 CAGR 将 2022 年基线外推至 2050 年（kt P）。"""
    recent = hist.loc[hist.index >= hist.index.max() - 30]
    cagr = (recent.iloc[-1] / recent.iloc[0]) ** (1 / (recent.index[-1] - recent.index[0])) - 1
    base_2022 = hist.loc[2022]
    bau = base_2022 * (1 + cagr) ** (YEAR - 2022)
    print(f"近 30 年 CAGR = {cagr*100:.2f}% → 2050 年 BAU 磷需求 ≈ {bau:,.1f} kt P")
    return bau
 
 
def basin_scenarios(bau_total: float) -> pd.DataFrame:
    """将 BAU 总量分配到模拟流域，生成 BAU 与 3R 两情景的流域面板。"""
    shares = RNG.dirichlet(np.ones(N_BASINS) * 2.0)  # 异质性流域份额
    df = pd.DataFrame({
        "basin": [f"Basin_{i:02d}" for i in range(1, N_BASINS + 1)],
        "chem_fert": shares * bau_total * 0.55,
        "manure": shares * bau_total * 0.25,
        "sewage": shares * bau_total * 0.12,
        "deposition": shares * bau_total * 0.08,
    })
    df["uptake"] = df[["chem_fert", "manure", "sewage", "deposition"]].sum(axis=1) * \
        RNG.uniform(0.55, 0.75, N_BASINS)
    df["erosion"] = df[["chem_fert", "manure"]].sum(axis=1) * RNG.uniform(0.1, 0.2, N_BASINS)
    df["input_total"] = df[["chem_fert", "manure", "sewage", "deposition"]].sum(axis=1)
    df["pue_bau"] = df["uptake"] / df["input_total"]
    df["scenario"] = "BAU"
 
    r = df.copy()
    r["chem_fert"] *= 0.80                       # Reduce -20%
    r["manure"] = r["manure"] * 0.25 + r["manure"] * 0.75 * 0.75  # Replace 回收率 75%
    r["sewage"] *= 0.40                          # Recycle -60%
    r["input_total"] = r[["chem_fert", "manure", "sewage", "deposition"]].sum(axis=1)
    r["uptake"] *= 0.97
    r["erosion"] *= 0.85
    r["pue_3r"] = r["uptake"] / r["input_total"]
    r["scenario"] = "3R"
    return pd.concat([df, r], ignore_index=True)
 
 
def cross_sensitivity_regression(df: pd.DataFrame):
    """logit(PUE) ~ 政策变量 × 情景，输出标准化弹性系数与 p 值。"""
    d = df.copy()
    for c in ["chem_fert", "manure", "sewage", "deposition"]:
        d[c] = d[c] / d[c].mean()
    d["is_3r"] = (d["scenario"] == "3R").astype(int)
    d = d[d["input_total"] > d["uptake"] + 1e-9]
    d["pue_logit"] = np.log(d["uptake"] / (d["input_total"] - d["uptake"]))
 
    model = smf.ols(
        "pue_logit ~ is_3r * (chem_fert + manure + sewage + deposition "
        "+ chem_fert:manure + chem_fert:sewage)", data=d).fit()
    print("\n===== 交叉敏感性回归（因变量：logit(PUE)）=====")
    print(model.summary())
    res = pd.DataFrame({"coef": model.params, "p_value": model.pvalues})
    print("\n关键弹性系数：")
    print(res.round(4).to_string())
    return model, res
 
 
def dashboard(df: pd.DataFrame, out_html="scenario_dashboard_2050.html"):
    agg = df.groupby("scenario")[["input_total", "uptake", "erosion"]].sum()
    pue = df.groupby("scenario").apply(
        lambda g: g["uptake"].sum() / g["input_total"].sum(), include_groups=False)
    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=("总输入 (kt P)", "作物吸收 (kt P)",
                                        "环境流失 (kt P)", "磷利用效率 PUE"))
    for col, (r_, c_) in [("input_total", (1, 1)), ("uptake", (1, 2)), ("erosion", (2, 1))]:
        fig.add_bar(x=agg.index, y=agg[col], marker_color=["#d62728", "#2ca02c"],
                    showlegend=False, row=r_, col=c_)
    fig.add_bar(x=pue.index, y=pue.values, marker_color=["#d62728", "#2ca02c"],
                showlegend=False, row=2, col=2)
    fig.update_layout(title=f"{YEAR} 年 BAU vs 3R 情景对比仪表盘", width=1000, height=700)
    fig.write_html(out_html, include_plotlyjs=True, full_html=True)
    print(f"\n情景仪表盘已保存：{out_html}")
 
 
def main():
    hist = historical_baseline()
    print(f"真实数据基线：2022 年全球磷移除量 = {hist.loc[2022]:,.1f} kt P")
    bau = extrapolate_bau(hist)
 
    print("\n===== 2050 年情景对比（全流域汇总, kt P/yr）=====")
    panel = basin_scenarios(bau)
    print(panel.groupby("scenario")[["input_total", "uptake", "erosion"]].sum().round(1))
 
    cross_sensitivity_regression(panel)
    dashboard(panel)
 
 
if __name__ == "__main__":
    main()