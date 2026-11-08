# -*- coding: utf-8 -*-
"""
C_sensitivity.py —— P22 敏感性：四因子单因素 + 蒙特卡洛 90% 情景区间

  · 电网结构：EF 0.314 → 0.749，GWP 843 → 1,424 kg CO₂e/t（+69%）
  · 锂价：10k → 50k USD/t，LCOR −4,207 → −9,271 元/t（净收益扩大 120%）
  · 直再比例：60% → 45%，GWP 1,141 → 1,190（+49），LCOR −5,726 → −5,524（少赚 202）
  · 绿电溢价改为线性（去掉 0.12g²）：拐点左移至 50%，满绿电 LCOR 改善 41 元（−5,767）
  · 蒙特卡洛 5,000 次 90% 情景区间：GWP 826—1,478；LCOR −8,940 ~ −4,335；
    满负荷 NPV 与静态回收期同区间输出（20,000 t 全量口径，非统计置信区间）

输出 data_cohort/sensitivity.json、mc_summary.csv

【AI 辅助编程说明】Prompt："做四因子单因素敏感性，并把电网结构、锂价、直再比例、绿电比例、
绿电溢价五维随机化做 5,000 次蒙特卡洛，输出 5—95 分位情景区间。" 人工校验：与 P22 数字逐项对齐。
"""
import copy

from C_env_econ_core import *

f = simulate(KNEE_D)
base = lca(f, KNEE_G)
ec_base = tea(f, 22000, KNEE_G)


def at(g=KNEE_G, d=None, ef=None, gw=None, price=22000):
    ff = f if d is None else simulate(d)
    e = lca(ff, g, grid_ef=ef, grid_water=gw)
    c = tea(ff, price, g)
    return {"gwp": e["gwp_kg_per_t"], "lcor": c["lcor_yuan_per_t"], "water": e["water_m3_per_t"]}


grid_low = at(ef=LCA_T["grid_ef"]["low"], gw=LCA_T["grid_water_m3_per_kwh"]["low"])
grid_high = at(ef=LCA_T["grid_ef"]["high"], gw=LCA_T["grid_water_m3_per_kwh"]["high"])
li_low = at(price=TEA["li2co3_price_usd_per_t"]["low"])
li_high = at(price=TEA["li2co3_price_usd_per_t"]["high"])
d45 = at(d=0.45)

# ---- 绿电溢价改为线性（去掉 0.12g²），重新找拐点 ----
t_lin = copy.deepcopy(TEA)
t_lin["green_premium"]["quad_yuan_per_kwh"] = 0.0
scan = []
for i in range(21):
    g = i / 20
    scan.append({"green": g, "gwp": lca(f, g)["gwp_kg_per_t"], "lcor": tea(f, 22000, g, t=t_lin)["lcor_yuan_per_t"]})
gw_ = [r["gwp"] for r in scan]
lc_ = [r["lcor"] for r in scan]
lin_knee = min(scan, key=lambda r: ((r["gwp"] - min(gw_)) / (max(gw_) - min(gw_))) ** 2 +
               ((r["lcor"] - min(lc_)) / (max(lc_) - min(lc_))) ** 2)

mc_gwp, mc_lcor, mc_npv, mc_pb = monte_carlo(5000)
pb_finite = mc_pb[np.isfinite(mc_pb)]

out = {
    "base": {"gwp": base["gwp_kg_per_t"], "lcor": ec_base["lcor_yuan_per_t"]},
    "grid_structure": {"low": grid_low, "high": grid_high,
                       "gwp_delta_pct": (grid_high["gwp"] / grid_low["gwp"] - 1) * 100},
    "lithium_price": {"low": li_low, "high": li_high,
                      "lcor_expand_pct": (li_high["lcor"] / li_low["lcor"] - 1) * 100},
    "direct_share": {"d45": d45,
                     "gwp_delta": d45["gwp"] - base["gwp_kg_per_t"],
                     "lcor_delta": d45["lcor"] - ec_base["lcor_yuan_per_t"]},
    "green_premium_linear": {"knee_green": lin_knee["green"], "lcor_at_knee": lin_knee["lcor"],
                             "lcor_at_100": scan[-1]["lcor"],
                             "gain_vs_base": scan[-1]["lcor"] - ec_base["lcor_yuan_per_t"],
                             "curve": scan},
    "monte_carlo": {
        "n": 5000, "seed": 20261108,
        "gwp_p05": float(np.percentile(mc_gwp, 5)), "gwp_p50": float(np.percentile(mc_gwp, 50)),
        "gwp_p95": float(np.percentile(mc_gwp, 95)),
        "lcor_p05": float(np.percentile(mc_lcor, 5)), "lcor_p50": float(np.percentile(mc_lcor, 50)),
        "lcor_p95": float(np.percentile(mc_lcor, 95)),
        "npv_p05": float(np.percentile(mc_npv, 5)), "npv_p50": float(np.percentile(mc_npv, 50)),
        "npv_p95": float(np.percentile(mc_npv, 95)),
        "payback_p05": float(np.percentile(pb_finite, 5)), "payback_p50": float(np.percentile(pb_finite, 50)),
        "payback_p95": float(np.percentile(pb_finite, 95)),
        "payback_over_20_share": float((mc_pb > 20).mean()),
        "note": "90% 情景区间（5—95 分位），非统计置信区间；NPV/回收期按 20,000 t 全量满负荷；参数范围见 ABC_parameters.json 的 source 字段",
    },
    "cascade": cascade_note(),
}

hist, edges = np.histogram(mc_lcor, bins=20)
rows = [[float((edges[i] + edges[i + 1]) / 2), int(hist[i])] for i in range(len(hist))]

print("=" * 80)
print("P22 敏感性（基准：GWP 1,141 kg CO₂e/t、LCOR −5,726 元/t）")
print(f"  电网结构  GWP {grid_low['gwp']:.0f} → {grid_high['gwp']:.0f}（+{out['grid_structure']['gwp_delta_pct']:.0f}%）")
print(f"  锂价      LCOR {li_low['lcor']:.0f} → {li_high['lcor']:.0f}（净收益扩大 {out['lithium_price']['lcor_expand_pct']:.0f}%）")
print(f"  直再 45%  GWP {d45['gwp']:.0f}（+{out['direct_share']['gwp_delta']:.0f}）、LCOR {d45['lcor']:.0f}"
      f"（少赚 {abs(out['direct_share']['lcor_delta']):.0f}）")
print(f"  线性溢价  拐点 g={lin_knee['green']:.2f}，满绿电 LCOR {scan[-1]['lcor']:.0f}"
      f"（改善 {abs(out['green_premium_linear']['gain_vs_base']):.0f} 元）")
print(f"  蒙特卡洛  GWP {out['monte_carlo']['gwp_p05']:.0f}—{out['monte_carlo']['gwp_p95']:.0f}；"
      f"LCOR {out['monte_carlo']['lcor_p05']:.0f} ~ {out['monte_carlo']['lcor_p95']:.0f}")
print(f"            满负荷 NPV {out['monte_carlo']['npv_p05']:.2f}—{out['monte_carlo']['npv_p95']:.2f} 亿元；"
      f"回收期 {out['monte_carlo']['payback_p05']:.1f}—{out['monte_carlo']['payback_p95']:.1f} 年")
save_json("C_11_09_sensitivity.json", out)
save_csv("C_11_09_mc_summary.csv", ["lcor_bin_center", "count"], rows)
