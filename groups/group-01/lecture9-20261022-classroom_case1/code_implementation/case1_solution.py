# -*- coding: utf-8 -*-
"""
第九讲 案例一 任务1：MFA-LCA-TEA 跨维联动与绿电溢价核算
运行环境: conda env `mfa_lca_tea` (pandas/numpy)
运行命令: python case1_solution.py
输出: 控制台结果 + case1_solution_report.md
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "case1_solution_report.md")

# ============ 基准参数（讲义模块二/三，基准情景：80% 收率 + 常规电网） ============
Y_BASE = 0.80          # 基准主产品收率
VIRGIN_PET = 2250.0    # kg CO2e/t 原生PET基准

# LCA 清单（kg CO2e / t rPET，随瓶砖通量线性缩放的项目）
LCI_BASE = {           # 名称: (基准贡献 kg CO2e, 是否随瓶砖量缩放)
    "原料瓶砖运输":        (150.0, True),
    "生产电力消耗":        (467.5, True),   # 850 kWh x 0.55
    "热洗蒸汽能耗":        (130.0, True),
    "氢氧化钠药剂":        (31.5, True),
    "新鲜水消耗":          (0.95, True),
    "污水处理负荷":        (6.05, True),
    "副产HDPE替代信用":    (-150.0, True),  # -93.75 kg x 1.60
}
ELEC_KWH = 850.0       # kWh / t rPET（基准通量下）
EF_GRID = 0.55         # kg CO2e/kWh 华中电网
EF_GREEN = 0.03        # kg CO2e/kWh 绿电

# TEA 成本构成（元/t rPET，基准情景）
TEA_BASE = {           # 名称: (基准成本, 是否随瓶砖通量缩放)
    "原料废瓶砖费用":      (5250.0, True),   # 1.25 t x 4200
    "电力动力费用":        (552.5, True),    # 850 kWh x 0.65
    "天然气蒸汽热力":      (170.0, True),
    "新鲜水与烧碱药剂":    (115.0, True),
    "焚烧杂质固废处置费":  (20.3, True),
    "人工编制成本":        (218.8, False),   # 固定，按产量摊销
    "设备维护保修费":      (52.5, False),
    "管理保险及折旧":      (196.4, False),
    "副产物外售收入抵扣":  (-422.1, True),   # 0.0938 t HDPE x 4500
}
PRICE_ELEC_BASE = 0.65
PRICE_ELEC_GREEN = 0.70
PRICE_RPET = 7600.0
ANNUAL_OUTPUT = 16000.0  # t/年


def lca_scale_factor(yield_rate: float) -> float:
    """瓶砖通量缩放系数: 吨产品物耗 = 1/Y，相对基准 1/0.8"""
    return (1.0 / yield_rate) / (1.0 / Y_BASE)


def calc_lca(yield_rate: float, ef_elec: float):
    """返回 (总GWP, 明细dict)。电力贡献按给定排放因子重算，其余随通量缩放"""
    f = lca_scale_factor(yield_rate)
    detail = {}
    for name, (val, scales) in LCI_BASE.items():
        if name == "生产电力消耗":
            detail[name] = ELEC_KWH * f * ef_elec
        else:
            detail[name] = val * f if scales else val
    return sum(detail.values()), detail


def calc_tea(yield_rate: float, price_elec: float):
    """返回 (LCOP, 明细dict)。电价与瓶砖通量联动，固定成本不随收率变化"""
    f = lca_scale_factor(yield_rate)
    detail = {}
    for name, (val, scales) in TEA_BASE.items():
        if name == "电力动力费用":
            detail[name] = ELEC_KWH * f * price_elec
        else:
            detail[name] = val * f if scales else val
    return sum(detail.values()), detail


def fmt(detail, unit):
    return "\n".join(f"| {k} | {v:+.1f} |" for k, v in detail.items())


# ==================== 情景计算 ====================
# 0) 基准复核
gwp0, d_lca0 = calc_lca(Y_BASE, EF_GRID)
lcop0, d_tea0 = calc_tea(Y_BASE, PRICE_ELEC_BASE)

# 1) 任务1-(1) 绿电 LCA
gwp_g, d_lca_g = calc_lca(Y_BASE, EF_GREEN)
red_g = (VIRGIN_PET - gwp_g) / VIRGIN_PET * 100

# 2) 任务1-(2) 绿电 TEA
lcop_g, d_tea_g = calc_tea(Y_BASE, PRICE_ELEC_GREEN)
d_cost = lcop_g - lcop0
d_pct = d_cost / lcop0 * 100
margin_base = PRICE_RPET - lcop0
margin_g = PRICE_RPET - lcop_g
# 溢价定价: 绿电产品增量减排成本 vs 品牌方愿意支付的绿色溢价
green_premium_needed = d_cost          # 覆盖成本所需最低溢价 元/t
annual_extra = d_cost * ANNUAL_OUTPUT  # 年增成本

# 3) 任务1-(3) 收率降至70%（常规电网）
Y_LOW = 0.70
gwp_y, d_lca_y = calc_lca(Y_LOW, EF_GRID)
lcop_y, d_tea_y = calc_tea(Y_LOW, PRICE_ELEC_BASE)
red_y = (VIRGIN_PET - gwp_y) / VIRGIN_PET * 100
margin_y = PRICE_RPET - lcop_y

# ==================== 输出 ====================
lines = []
lines.append("# 案例一 任务1 计算报告：绿电溢价与收率敏感度（MFA-LCA-TEA 联动）\n")
lines.append("## 0. 基准情景复核\n")
lines.append(f"- 净碳足迹 GWP = **{gwp0:.1f} kg CO2e/t**（讲义基准 636.0）")
lines.append(f"- 平准化成本 LCOP = **{lcop0:.1f} 元/t**（讲义基准 6,153.4）\n")

lines.append("## 1. 绿电情景 LCA 再核算\n")
lines.append("边界变更：电力排放因子 0.55 -> 0.03 kg CO2e/kWh，其余活动水平不变。\n")
lines.append("| 清单分项 | kg CO2e/t |")
lines.append("| :--- | ---: |")
lines.append(fmt(d_lca_g, "kg"))
lines.append(f"| **净碳足迹 GWP_green** | **{gwp_g:.1f}** |\n")
lines.append(f"- 较基准减排：{gwp0:.1f} -> {gwp_g:.1f}，下降 **{gwp0-gwp_g:.1f} kg CO2e/t（-{(gwp0-gwp_g)/gwp0*100:.1f}%）**")
lines.append(f"- 相对原生 PET（2,250）减碳幅度：**{red_g:.1f}%**（基准情景为 71.7%）\n")

lines.append("## 2. 绿电情景 TEA 再核算\n")
lines.append("边界变更：购电单价 0.65 -> 0.70 元/kWh（绿色溢价 0.05 元/kWh）。\n")
lines.append("| 成本分项 | 元/t |")
lines.append("| :--- | ---: |")
lines.append(fmt(d_tea_g, "元"))
lines.append(f"| **LCOP_green** | **{lcop_g:.1f}** |\n")
lines.append(f"- LCOP 增加额：**+{d_cost:.1f} 元/t**，增幅 **+{d_pct:.2f}%**")
lines.append(f"- 吨毛利：{margin_base:.1f} -> {margin_g:.1f} 元/t；年增成本 {annual_extra/1e4:.1f} 万元\n")
lines.append("### 绿色低碳溢价定价与营销策略建议")
lines.append(f"1. **成本传导底线**：绿电产品售价至少应为 {PRICE_RPET + green_premium_needed:.0f} 元/t（在原 7,600 元/t 上加约 {green_premium_needed:.0f} 元/t 绿色溢价），即可完全覆盖绿电采购增量成本；")
lines.append(f"2. **价值锚定**：绿电 rPET 碳足迹 {gwp_g:.0f} kg/t，较原生 PET 净减排 {VIRGIN_PET-gwp_g:.0f} kg/t。按全国碳市场约 100 元/tCO2e 计，每吨产品环境价值约 {(VIRGIN_PET-gwp_g)/1000*100:.0f} 元，绿色溢价空间远大于 {green_premium_needed:.0f} 元/t 的成本上升，建议以 3%-8% 品牌溢价（约 230-600 元/t）面向国际饮料品牌签订绿色长单；")
lines.append("3. **认证与叙事**：配套 RE100/绿色电力证书溯源与 PCR 含量认证（食品级 rPET），以'碳足迹标签'切入品牌 Scope 3 减排采购清单，采用量价绑定阶梯合同锁定溢价。")
lines.append("")

lines.append("## 3. 源头敏感度：收率 80% -> 70%（常规电网）\n")
lines.append(f"吨产品瓶砖物耗由 1.25 t 升至 {1/Y_LOW:.3f} t，通量放大系数 f = {lca_scale_factor(Y_LOW):.4f}。\n")
lines.append("| 指标 | 基准(80%) | 扰动(70%) | 变化 |")
lines.append("| :--- | ---: | ---: | ---: |")
lines.append(f"| LCA 净碳足迹 kg CO2e/t | {gwp0:.1f} | {gwp_y:.1f} | +{(gwp_y/gwp0-1)*100:.1f}% |")
lines.append(f"| 较原生PET减碳幅度 | {(VIRGIN_PET-gwp0)/VIRGIN_PET*100:.1f}% | {red_y:.1f}% | -{(VIRGIN_PET-gwp0)/VIRGIN_PET*100-red_y:.1f} pp |")
lines.append(f"| TEA LCOP 元/t | {lcop0:.1f} | {lcop_y:.1f} | +{(lcop_y/lcop0-1)*100:.1f}% |")
lines.append(f"| 吨毛利 元/t | {margin_base:.1f} | {margin_y:.1f} | -{(margin_base-margin_y)/margin_base*100:.1f}% |\n")
lines.append("**连锁效应解读**：分类纯度下降使 MFA 物耗系数放大 14.3%，前端运输/清洗/分选的全部变动投入（含 HDPE 副产信用）同比例放大，LCA 碳足迹与 TEA 原料成本同步恶化；原料成本占 LCOP 近九成，故吨毛利被严重挤压。结论：**源头垃圾分类质量是 LCA 与 TEA 共同的第一敏感参数**，规划上应优先保障瓶砖分选纯度而非末端工艺优化。")
lines.append("")

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("\n".join(lines))
print(f"[saved] {REPORT}")
