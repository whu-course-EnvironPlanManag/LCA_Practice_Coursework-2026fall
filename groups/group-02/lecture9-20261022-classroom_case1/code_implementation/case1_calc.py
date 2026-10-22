# -*- coding: utf-8 -*-
"""
案例一：废弃 PET 塑料瓶机械物理再生系统 MFA-LCA-TEA 联动核算脚本
================================================================

功能单位：生产 1 t（1000 kg）瓶级再生 PET (rPET) 颗粒（Cradle-to-Gate）

本脚本完成三件事：
  1. 读取 MFA 物质平衡表，验证质量守恒并推导综合产品收率与吨产品物耗系数；
  2. 读取 LCI 清单，核算基准情景与“100% 绿电”情景的全生命周期净碳足迹 (GWP)；
  3. 基于 TEA 成本表，核算基准 / 绿电 / 收率下降三个情景的平准化生产成本 (LCOP)。

结果同时打印到控制台，并生成本组目录下的 case1_solution_report.md 计算报告。
"""

from pathlib import Path
import pandas as pd

# ----------------------------------------------------------------------------
# 0. 路径与常量
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "case_files" / "data_cohort"
REPORT_PATH = BASE_DIR / "case1_solution_report.md"

# 原生 PET 基准（Plastics Europe eco-profile）：kg CO2e / t vPET
VIRGIN_PET_BENCHMARK = 2250.0


def load_data() -> dict:
    """读取三个基础数据集（CSV）。"""
    mfa = pd.read_csv(DATA_DIR / "mfa_mass_balance.csv")
    lci = pd.read_csv(DATA_DIR / "lci_emission_factors.csv")
    tea = pd.read_csv(DATA_DIR / "tea_cost_parameters.csv")
    return {"mfa": mfa, "lci": lci, "tea": tea}


# ----------------------------------------------------------------------------
# 1. 模块一：MFA 物质平衡推演
# ----------------------------------------------------------------------------
def mfa_analysis(mfa: pd.DataFrame) -> dict:
    """验证质量守恒，推导收率与物耗系数。"""
    total_in = mfa.loc[mfa["Flow_Type"] == "Raw_Material", "Mass_kg"].sum()
    main_product = mfa.loc[mfa["Flow_Type"] == "Main_Product", "Mass_kg"].sum()
    co_product = mfa.loc[mfa["Flow_Type"] == "Co_Product", "Mass_kg"].sum()
    wastes = mfa.loc[mfa["Flow_Type"] == "Waste", "Mass_kg"].sum()

    total_out = main_product + co_product + wastes
    yield_frac = main_product / total_in                 # 综合产品收率 Y
    condensed_mass = total_in / main_product             # 吨产品物耗系数 (t 瓶砖 / t rPET)

    return {
        "total_in": total_in,
        "total_out": total_out,
        "main_product": main_product,
        "co_product": co_product,
        "wastes": wastes,
        "yield_frac": yield_frac,
        "consumption_per_t": condensed_mass,
    }


# ----------------------------------------------------------------------------
# 2. 模块二：LCA 碳足迹核算（门到门）
# ----------------------------------------------------------------------------
def lca_gwp(lci: pd.DataFrame, elec_ef: float | None = None) -> float:
    """
    汇总净碳足迹 GWP (kg CO2e / t rPET)。

    仅当传入 elec_ef 时，才替换“生产电力”的背景排放因子
    （用于 100% 绿电情景 0.55 -> 0.03 kg CO2e/kWh）。
    其余分项（运输、蒸汽、药剂、水、污水、HDPE 抵扣）保持基准不变。
    """
    # 仅保留实际过程分项（Category 非空），剔除 Net_Total_GWP / Benchmark / Reduction 汇总行
    df = lci.dropna(subset=["Category"]).copy()
    if elec_ef is not None:
        elec_mask = df["Flow_Name"] == "Electricity_Grid"
        # 电力活动水平 850 kWh/t，背景因子替换后重新计算该分项贡献
        amount = df.loc[elec_mask, "Amount_per_t_rPET"].iloc[0]
        df.loc[elec_mask, "Emission_Factor"] = elec_ef
        df.loc[elec_mask, "Carbon_Footprint_kgCO2e"] = amount * elec_ef

    return float(df["Carbon_Footprint_kgCO2e"].sum())


# ----------------------------------------------------------------------------
# 3. 模块三：TEA 平准化生产成本 (LCOP) 核算
# ----------------------------------------------------------------------------
# 基准情景单位成本表（元/t rPET），与讲义【四.3】一致；单位费率可由 tea CSV 交叉核对。
BASE_TEA = {
    "原料废瓶砖费用": 5250.0,     # 1.25 t × 4200 元/t
    "电力动力费用": 552.5,        # 850 kWh × 0.65 元/kWh
    "天然气蒸汽热力": 170.0,      # 2.0 GJ × 85 元/GJ
    "新鲜水与烧碱药剂": 115.0,    # 综合定额
    "焚烧杂质固废处置费": 20.3,   # 0.081 t × 250 元/t
    "人工编制成本": 218.8,        # 35 人 × 10 万/年 ÷ 16000 t
    "设备维护保修费": 52.5,       # 2800 万 × 3% ÷ 16000 t
    "管理保险与折旧": 196.4,      # 直线折旧 + 摊销
}
HDPE_CREDIT_BASE = -422.1        # 0.0938 t × 4500 元/t 副产抵扣
ELECTRICITY_KWH = 850.0          # 吨产品电耗 (kWh/t)


def tea_lcop(elec_price_delta: float = 0.0) -> float:
    """
    计算 LCOP。elec_price_delta 为每 kWh 电价增量（元/kWh）。
    绿电情景：+0.05 元/kWh；基准：0.0。
    """
    cost = dict(BASE_TEA)
    cost["电力动力费用"] = ELECTRICITY_KWH * (0.65 + elec_price_delta)
    return sum(cost.values()) + HDPE_CREDIT_BASE


# ----------------------------------------------------------------------------
# 4. 收率下降敏感度分析（80% -> 70%）
# ----------------------------------------------------------------------------
def sensitivity(yield_new: float = 0.70) -> dict:
    """
    前端杂质率上升 -> 综合产品收率下降 -> LCA 与 TEA 的连锁恶化。

    缩放系数 r：单吨 rPET 所需原料由 1.25 t 增至 1/Y_new t。
       r = (1/Y_new) / (1/Y_old) = Y_old / Y_new
    在“年处理规模（20,000 t 瓶砖）固定”假设下，所有随进料量变化的
    变动成本（原料、公用工程、药剂、固废、HDPE 抵扣）均乘以 r。
    """
    Y_old = 0.80
    r = Y_old / yield_new                       # 缩放比 = 0.80 / 0.70 = 1.1429
    new_input_per_t = 1.0 / yield_new           # 吨产品原料需求 (t)

    # --- LCA：每分项均为进料量线性函数，整体按 r 缩放 ---
    gwp_base = 636.0
    gwp_new = gwp_base * r
    reduction_base = (VIRGIN_PET_BENCHMARK - gwp_base) / VIRGIN_PET_BENCHMARK * 100
    reduction_new = (VIRGIN_PET_BENCHMARK - gwp_new) / VIRGIN_PET_BENCHMARK * 100

    # --- TEA：变动部分按 r 缩放（年处理规模固定，产量下降导致固定成本摊薄） ---
    cost_new = {k: v * r for k, v in BASE_TEA.items()}
    loot = cost_new["原料废瓶砖费用"]
    lcop_new = sum(cost_new.values()) + HDPE_CREDIT_BASE * r

    return {
        "yield_new": yield_new,
        "r": r,
        "input_per_t_base": 1.25,
        "input_per_t_new": new_input_per_t,
        "gwp_base": gwp_base,
        "gwp_new": gwp_new,
        "reduction_base": reduction_base,
        "reduction_new": reduction_new,
        "feedstock_cost_new": loot,
        "lcop_base": 6153.4,
        "lcop_new": lcop_new,
    }


# ----------------------------------------------------------------------------
# 5. 生成 Markdown 计算报告
# ----------------------------------------------------------------------------
def render_report(mfa_res: dict, gwp_base: float, gwp_green: float,
                  lcop_base: float, lcop_green: float, sens: dict) -> str:
    y = mfa_res["yield_frac"]

    # 绿电 TEA 增量
    delta_lcop = lcop_green - lcop_base
    delta_ratio = delta_lcop / lcop_base * 100
    # 绿电 LCA 减排率
    red_green = (VIRGIN_PET_BENCHMARK - gwp_green) / VIRGIN_PET_BENCHMARK * 100
    # 基准减排率
    red_base = (VIRGIN_PET_BENCHMARK - gwp_base) / VIRGIN_PET_BENCHMARK * 100

    # 毛利率相关
    price = 7600.0
    margin_base = price - lcop_base
    margin_green = price - lcop_green
    margin_sens = price - sens["lcop_new"]

    report = f"""# 案例一解决方案报告：MFA-LCA-TEA 跨维联动与绿电溢价核算

> 组别：group-02 ｜ 功能单位：生产 1 t 瓶级再生 PET (rPET) 颗粒
> 本报告由 `case1_calc.py` 自动生成，所有数值可由脚本复现。

---

## 一、模块一：MFA 物质平衡校验（Baseline）

| 指标 | 数值 |
| :--- | :--- |
| 系统总进料（废 PET 瓶砖） | {mfa_res['total_in']:.1f} kg |
| 主产品瓶级 rPET | {mfa_res['main_product']:.1f} kg |
| 副产品 HDPE 瓶盖碎料 | {mfa_res['co_product']:.1f} kg |
| 各类杂质/固废输出 | {mfa_res['wastes']:.1f} kg |
| 质量守恒校验（入 = 出） | {mfa_res['total_in']:.1f} = {mfa_res['total_out']:.1f} kg ✔ |
| **综合产品收率 Y** | **{y * 100:.1f}%** |
| **吨产品物耗系数** | **{mfa_res['consumption_per_t']:.4f} t 瓶砖 / t rPET** |

---

## 二、模块二：LCA 净碳足迹（基准 vs 100% 绿电）

### 1. 基准情景净碳足迹
$$GWP_{{base}} = 150.0 + 467.5 + 130.0 + 31.5 + 0.95 + 6.05 - 150.0 = {gwp_base:.1f}\\ \\text{{kg CO₂e/t}}$$

相对原生 PET（{VIRGIN_PET_BENCHMARK:.0f} kg CO₂e/t）减排 **{red_base:.1f}%**。

### 2. 绿电情景净碳足迹再核算（任务 1-1）

仅“生产电力”分项的背景排放因子由 0.55 降为 0.03 kg CO₂e/kWh：

$$850\\ \\text{{kWh}} \\times 0.03 = 25.5\\ \\text{{kg CO₂e}} \\quad (基准为 467.5)$$

清单调整后的其他分项不变，重新加总：

$$GWP_{{green}} = 150.0 + 25.5 + 130.0 + 31.5 + 0.95 + 6.05 - 150.0 = {gwp_green:.1f}\\ \\text{{kg CO₂e/t}}$$

相对原生 PET 的减碳幅度达 **{red_green:.1f}%**（基准为 {red_base:.1f}%，提升 {red_green - red_base:.1f} 个百分点）。

---

## 三、模块三：TEA 平准化生产成本（基准 vs 100% 绿电）

### 1. 基准 LCOP
$$LCOP_{{base}} = {lcop_base:.1f}\\ \\text{{元/t}}$$

### 2. 绿电 LCOP 再核算（任务 1-2）

绿电购电单价由 0.65 升至 0.70 元/kWh（+0.05 元/kWh），仅电力成本变化：

$$\\Delta C_{{elec}} = 850\\ \\text{{kWh}} \\times 0.05 = 42.5\\ \\text{{元/t}}$$

$$LCOP_{{green}} = {lcop_base:.1f} + 42.5 = {lcop_green:.1f}\\ \\text{{元/t}}$$

| 指标 | 基准 | 绿电 | 变化 |
| :--- | ---: | ---: | ---: |
| 吨电耗成本（元/t） | 552.5 | 595.0 | +42.5 |
| LCOP（元/t） | {lcop_base:.1f} | {lcop_green:.1f} | **+{delta_lcop:.1f}（+{delta_ratio:.2f}%）** |
| 吨产品毛利（元/t） | {margin_base:.1f} | {margin_green:.1f} | -{margin_base - margin_green:.1f} |

**绿色溢价定价与营销建议：**
- 绿电带来的成本增量仅 **{delta_lcop:.1f} 元/t（+{delta_ratio:.2f}%）**，涨价约 **{delta_lcop / price * 100:.2f}%**（{delta_lcop:.1f}/7600）即可完全覆盖。
- 但排放侧大幅受益（减排率由 {red_base:.1f}% 跃升至 {red_green:.1f}%），可借“100% 绿电制备、碳中和 rPET”定位，向国际饮料品牌索取远超成本增量的**绿色低碳溢价**，作为品牌可持续采购的核心卖点。

---

## 四、源头敏感度分析：收率 80% → 70%（任务 1-3）

前端垃圾分类不完善 → 瓶砖杂质率上升 → 综合产品收率由 80% 降至 70%。

### 1. 物耗系数连锁上升
$$单吨 rPET 原料需求：1.25\\ \\text{{t}} \\longrightarrow {sens['input_per_t_new']:.4f}\\ \\text{{t}} \\quad (r = {sens['r']:.4f})$$

### 2. LCA 碳足迹连锁恶化
所有分项（运输、预处理公用工程及 HDPE 抵扣）均为进料量的线性函数，整体按 r 缩放：

$$GWP_{{70\\%}} = 636.0 \\times {sens['r']:.4f} = {sens['gwp_new']:.1f}\\ \\text{{kg CO₂e/t}} \\quad (+{sens['gwp_new'] - sens['gwp_base']:.1f})$$

相对原生 PET 减排率由 **{sens['reduction_base']:.1f}%** 滑落至 **{sens['reduction_new']:.1f}%**。

### 3. TEA 成本连锁冲击
在“年处理规模 20,000 t 瓶砖固定”假设下，产量由 16,000 t 降至 14,000 t，变动成本与摊薄的固定成本均按 r 缩放：

$$LCOP_{{70\\%}} = {sens['lcop_new']:.1f}\\ \\text{{元/t}} \\quad (+{sens['lcop_new'] - sens['lcop_base']:.1f},\\ +{(sens['lcop_new'] / sens['lcop_base'] - 1) * 100:.1f}\\%)$$

其中原料采购成本由 5,250 元/t 升至 **{sens['feedstock_cost_new']:.1f} 元/t**（单一最大冲击项）。

| 指标 | 收率 80% | 收率 70% | 变化 |
| :--- | ---: | ---: | ---: |
| 吨产品原料需求（t） | 1.2500 | {sens['input_per_t_new']:.4f} | +{sens['input_per_t_new'] - 1.25:.4f} |
| GWP（kg CO₂e/t） | {sens['gwp_base']:.1f} | {sens['gwp_new']:.1f} | +{sens['gwp_new'] - sens['gwp_base']:.1f} |
| LCOP（元/t） | {sens['lcop_base']:.1f} | {sens['lcop_new']:.1f} | +{sens['lcop_new'] - sens['lcop_base']:.1f} |
| 吨产品毛利（元/t） | {margin_base:.1f} | {margin_sens:.1f} | -{margin_base - margin_sens:.1f}（利润腰斩 {margin_base / price * 100:.1f}% → {margin_sens / price * 100:.1f}%） |

### 教学提炼
前端固废源头分类纯度（MFA 输入质量）同时决定末端环境足迹（LCA）与回收企业生存能力（TEA）：不建立在物质平衡之上的绿色规划只能是纸上谈兵。
"""
    return report


def main() -> None:
    data = load_data()

    # 1. MFA
    mfa_res = mfa_analysis(data["mfa"])
    assert abs(mfa_res["total_in"] - mfa_res["total_out"]) < 1e-6, "质量不守恒！"
    assert abs(mfa_res["yield_frac"] - 0.80) < 1e-6, "基准收率应为 80%"

    # 2. LCA：基准 + 绿电
    gwp_base = lca_gwp(data["lci"])
    gwp_green = lca_gwp(data["lci"], elec_ef=0.03)

    # 3. TEA：基准 + 绿电
    lcop_base = tea_lcop(0.0)
    lcop_green = tea_lcop(0.05)

    # 4. 敏感度 80% -> 70%
    sens = sensitivity(0.70)

    # 5. 生成报告
    report = render_report(mfa_res, gwp_base, gwp_green, lcop_base, lcop_green, sens)
    REPORT_PATH.write_text(report, encoding="utf-8")

    # 控制台速览
    print("=" * 60)
    print("MFA-LCA-TEA 联动核算结果速览")
    print("=" * 60)
    print(f"[MFA] 收率 {mfa_res['yield_frac']*100:.1f}% / 物耗 {mfa_res['consumption_per_t']:.4f} t/t")
    print(f"[LCA] 基准 GWP = {gwp_base:.1f} kg CO2e/t")
    print(f"[LCA] 绿电 GWP = {gwp_green:.1f} kg CO2e/t  (减排 91.4%)")
    print(f"[TEA] 基准 LCOP = {lcop_base:.1f} 元/t")
    print(f"[TEA] 绿电 LCOP = {lcop_green:.1f} 元/t  (+{lcop_green - lcop_base:.1f})")
    print(f"[SENS] 收率70% -> GWP = {sens['gwp_new']:.1f} / LCOP = {sens['lcop_new']:.1f} (+14.3%)")
    print("-" * 60)
    print(f"报告已生成：{REPORT_PATH}")


if __name__ == "__main__":
    main()