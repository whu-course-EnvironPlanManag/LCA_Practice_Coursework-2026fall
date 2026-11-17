# -*- coding: utf-8 -*-
"""
C_env_performance_supplement.py —— P16 环境绩效：原生精炼 vs 拐点方案 vs 100% 绿电

输出 data_cohort/env_performance.json：
  · 原生基准 5,000 kg CO₂e/t、26.7 m³/t（文献 [4] 按 0.345 t NCA-eq/t 换算）
  · 拐点方案 1,140.7 kg CO₂e/t、8.80 m³/t（绿电 55%、直再 60%）
  · 100% 绿电 490.0 kg CO₂e/t、7.86 m³/t
  · 再生链年环境效益（16,000 t/a）

【AI 辅助编程说明】Prompt："写一个环境绩效脚本，把原生基准、拐点、100% 绿电三档的
 GWP 与水耗算出来并算降幅，年效益按再生链 16,000 t/a 折算。" 人工校验：与 P16 数字逐项对齐。
"""
from C_env_econ_core import *

f = simulate(KNEE_D)
knee = lca(f, KNEE_G)
green = lca(f, 1.0)
grid = lca(f, 0.0)          # 全网电、直再 60%（改造起点对照）

lce = f["lce_t"]
out = {
    "functional_unit": "1 t 进入再生链的退役电池（LFP 60 / NMC811 35 / NCA 5）",
    "cascade": cascade_note(),
    "primary": {"gwp_kg_per_t": PRIMARY_GWP, "water_m3_per_t": PRIMARY_WATER,
                "source": "文献 [4]：193.9 MJ/kg、77.3 L/kg、14.5 kg CO₂e/kg，×0.345 t NCA-eq/t"},
    "knee": {"green_share": KNEE_G, "direct_share": KNEE_D,
             "gwp_kg_per_t": knee["gwp_kg_per_t"], "water_m3_per_t": knee["water_m3_per_t"],
             "ef": knee["ef"], "lce_t_per_t": lce,
             "gwp_per_t_lce": knee["gwp_kg_per_t"] / lce,
             "breakdown_kg": knee["breakdown"],
             "breakdown_pct": {k: v / knee["gwp_kg_per_t"] * 100 for k, v in knee["breakdown"].items()}},
    "green100": {"green_share": 1.0, "direct_share": KNEE_D,
                 "gwp_kg_per_t": green["gwp_kg_per_t"], "water_m3_per_t": green["water_m3_per_t"]},
    "grid_only": {"green_share": 0.0, "direct_share": KNEE_D,
                  "gwp_kg_per_t": grid["gwp_kg_per_t"], "water_m3_per_t": grid["water_m3_per_t"]},
    "reduction": {
        "gwp_pct": (1 - knee["gwp_kg_per_t"] / PRIMARY_GWP) * 100,
        "water_pct": (1 - knee["water_m3_per_t"] / PRIMARY_WATER) * 100,
        "green100_gwp_pct": (1 - green["gwp_kg_per_t"] / PRIMARY_GWP) * 100,
    },
    "annual_regen_chain": {
        "q_t": REGEN_T,
        "net_co2_t": (PRIMARY_GWP - knee["gwp_kg_per_t"]) * REGEN_T / 1000,
        "water_saved_m3": (PRIMARY_WATER - knee["water_m3_per_t"]) * REGEN_T,
    },
}

print("=" * 78)
print("P16 环境绩效（再生链 16,000 t/a；全园 20,000 t 含 4,000 t 梯次）")
print(f"  原生基准    GWP {PRIMARY_GWP:8.0f} kg CO₂e/t   水 {PRIMARY_WATER:6.2f} m³/t")
print(f"  拐点方案    GWP {knee['gwp_kg_per_t']:8.1f} kg CO₂e/t   水 {knee['water_m3_per_t']:6.2f} m³/t"
      f"   （−{out['reduction']['gwp_pct']:.1f}% / −{out['reduction']['water_pct']:.1f}%）")
print(f"  100% 绿电   GWP {green['gwp_kg_per_t']:8.1f} kg CO₂e/t   水 {green['water_m3_per_t']:6.2f} m³/t")
print(f"  年净减碳 {out['annual_regen_chain']['net_co2_t']/1e4:.2f} 万 t，年节水 "
      f"{out['annual_regen_chain']['water_saved_m3']/1e4:.1f} 万 m³")
save_json("env_performance.json", out)
