"""统一入口：一键完成数据处理、建模、守恒校验、桑基图、情景与回归。

用法：
    python run_all.py
    python run_all.py --data-dir "..\\source_data"
    python run_all.py --data-dir "D:\\path\\to\\source_data" --skip-regression
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from src import config  # noqa: E402
from src.data_io import load_bundle  # noqa: E402
from src.params import load_coefficients  # noqa: E402
from src.system_model import PhosphorusSystemModel  # noqa: E402
from src import plot_sankey  # noqa: E402


def stage(msg: str) -> None:
    print("\n" + "=" * 62)
    print(msg)
    print("=" * 62)


def main() -> int:
    ap = argparse.ArgumentParser(description="全球磷物质流分析实训")
    ap.add_argument("--data-dir", default=None, help="source_data 目录")
    ap.add_argument("--extra-dir", default=None,
                    help="补充数据目录（默认 submission_p_sfa/data_extra）")
    ap.add_argument("--skip-regression", action="store_true")
    args = ap.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else config.DEFAULT_DATA_DIR
    extra_dir = Path(args.extra_dir) if args.extra_dir else config.DEFAULT_EXTRA_DIR
    config.ensure_output_dirs()

    stage("阶段 1｜读取数据与系数")
    print(f"数据目录：{data_dir}")
    print(f"补充数据：{extra_dir}")
    bundle = load_bundle(data_dir, extra_dir)
    coefs = load_coefficients()
    print(f"作物收获磷(A–F,H–K)  : {bundle.crop_p:8.2f} Mt P")
    print(f"动物产品磷(G)        : {bundle.animal_p:8.2f} Mt P")
    print(f"活体动物磷(M,仅核对): {bundle.live_animal_p:8.2f} Mt P（不计入流量）")
    print(f"化肥施用({bundle.notes['fertilizer_year']})    : "
          f"{bundle.fertilizer['Agricultural Use']:8.2f} Mt P")
    print(f"课程包磷矿石({bundle.notes['rock_year']})  : {bundle.rock_mt:8.2f} Mt 实物量")
    print(f"耕地面积            : {bundle.cropland_ha/1e9:8.3f} Gha")
    print(f"2022 / 2050 人口    : {bundle.population/1e9:.3f} / {bundle.pop_2050/1e9:.3f} 十亿")

    avail = bundle.notes["extra_available"]
    print("补充数据接入        : " + "，".join(
        f"{k}={'有' if v else '缺'}" for k, v in avail.items()))
    if bundle.seed_p_mt is not None:
        print(f"  种子磷            : {bundle.seed_p_mt:8.3f} Mt P（ESB_2025）")
    else:
        print("  种子磷            : 缺少输入，从 ACS 平衡中排除")
    if bundle.manure_p_mt is not None:
        miss = (bundle.livestock or {}).get("missing_species", [])
        print(f"  粪磷（四畜种）    : {bundle.manure_p_mt:8.3f} Mt P"
              f"（未含 {'/'.join(miss) or '无'}）")
    if bundle.grassland_ha is not None:
        print(f"  永久草地面积      : {bundle.grassland_ha/1e9:8.3f} Gha")
    if bundle.rock_myb:
        print(f"  磷矿含磷(MYB)     : {bundle.rock_myb['p_Mt']:8.3f} Mt P"
              f"（矿石 {bundle.rock_myb['rock_Mt']:.0f} Mt）")

    from src.data_io import load_product_p, world_series
    long = load_product_p(data_dir)
    series = world_series(long)
    series.to_csv(config.RESULTS_DIR / "crop_p_series_1961_2022.csv",
                  encoding="utf-8-sig")
    print(f"1961→2022 作物端纯磷 : {series['作物端(A–F,H–K)'].iloc[0]:.2f} → "
          f"{series['作物端(A–F,H–K)'].iloc[-1]:.2f} Mt P "
          f"（{len(series)} 年，负值 {(series < 0).sum().sum()} 个）")

    stage("阶段 1.5｜含磷率字典交叉校验（任务 1.1）")
    from src.data_io import dictionary_crosscheck
    try:
        dict_df = dictionary_crosscheck(data_dir, year=bundle.notes["product_year"])
    except FileNotFoundError as exc:
        print(f"跳过：{exc}")
    else:
        dict_df.to_csv(config.RESULTS_DIR / "dictionary_check.csv",
                       index=False, encoding="utf-8-sig")
        print(dict_df.to_string(index=False, na_rep="—",
                                float_format=lambda x: f"{x:.4f}"))
        print("说明：官方纯磷表已在吨 P 口径，模型直接采用；上表仅作独立复算核对。")

    stage("阶段 2｜农田 ACS 模型（2022）")
    model = PhosphorusSystemModel(bundle, coefs)
    ledger_2022 = model.build()
    acs = model.acs.run()
    print(f"化肥输入 {acs.fertilizer:8.3f}  粪肥/回收 {acs.manure:8.3f}  "
          f"沉降 {acs.deposition:6.3f}  种子 {acs.seed:6.3f}")
    print(f"作物收获 {acs.harvest:8.3f}  秸秆残留 {acs.residue:8.3f}"
          f"（还田 {acs.residue_returned:.3f} / 废弃 {acs.residue_waste:.3f}）")
    print(f"排水+淋溶 {acs.water_loss:7.3f}  土壤遗留磷(平衡项) {acs.soil_accumulation:8.3f}")
    ok, rel = model.acs.verify_mass_balance()
    print(f"ACS 自平衡：{'通过' if ok else '未通过'}，相对误差 {rel:.3e}")
    if acs.seed_missing:
        print("提示：缺少输入 —— 种子磷（S_m × K_m 逐作物表），已从平衡中排除。")
    note = model.notes
    print(f"LBS 饲料口径：{note['lbs_basis']}；粪污磷 {note['animal_waste_Mt']:.3f} Mt P，"
          f"PUE(输出) {note['lbs_pue_model']*100:.1f}%")
    print(f"草地饲料(平衡项) {note['grass_feed_Mt']:.3f} Mt P")
    if note["grass_uptake_kg_ha"] is not None and bundle.grass_proxy:
        gp = bundle.grass_proxy
        inside = gp["min"] <= note["grass_uptake_kg_ha"] <= gp["max"]
        print(f"隐含草地单产 {note['grass_uptake_kg_ha']:.2f} kg P/ha/yr "
              f"vs proxy {gp['min']}–{gp['max']}（central {gp['central']}）"
              f"：{'落在区间内' if inside else '超出区间，需复核'}")
    print(f"磷矿口径：{note['rock_basis']}，观测输入 {note['rock_obs_Mt']:.3f} Mt P，"
          f"缺口残差 {note['rock_gap_Mt']:.3f} Mt P")

    stage("阶段 2.5｜补充数据锚点核对")
    from src.anchors import build_anchor_table, build_series
    if not any(avail.values()):
        print("补充数据目录为空，跳过锚点核对；模型已回退到原有反算路径。")
    else:
        anchor_df = build_anchor_table(bundle, model.notes, extra_dir, coefs)
        anchor_df.to_csv(config.RESULTS_DIR / "anchor_check.csv", index=False,
                         encoding="utf-8-sig")
        print(anchor_df.to_string(index=False, max_colwidth=46))
        series_df = build_series(extra_dir)
        if not series_df.empty:
            series_df.to_csv(
                config.RESULTS_DIR / "data_extra_series_1961_2022.csv",
                encoding="utf-8-sig")
            print(f"补充数据年度序列：{len(series_df)} 年 → "
                  f"{config.RESULTS_DIR / 'data_extra_series_1961_2022.csv'}")

    stage("阶段 3｜五系统守恒校验")
    chk = ledger_2022.verify(strict=True)
    g = chk["global"]
    print(f"系统边界输入 {g['total_in']:.3f} Mt P | 输出 {g['total_out']:.3f} Mt P "
          f"| 存量变化 {g['stock_change']:.3f} Mt P")
    print(f"全系统相对误差 {g['rel_err']:.3e}（阈值 1e-4）")
    print(f"最差节点相对误差 {chk['worst_node_rel_err']:.3e}")
    for name, v in chk["nodes"].items():
        flag = "OK" if v["rel_err"] < 1e-4 else "!!"
        print(f"  [{flag}] {name:<14} in={v['in']:8.3f} out={v['out']:8.3f} "
              f"res={v['residual']:+.3e}")
    print(f"守恒断言：{'通过' if chk['passed'] else '未通过'}")

    flows = pd.DataFrame([{
        "source": f.source, "target": f.target, "value_MtP": f.value,
        "residual": f.residual, "note": f.note,
    } for f in ledger_2022.flows])
    flows.to_csv(config.RESULTS_DIR / "flows_2022.csv", index=False,
                 encoding="utf-8-sig")
    pd.DataFrame(chk["nodes"]).T.to_csv(
        config.RESULTS_DIR / "node_balance_2022.csv", encoding="utf-8-sig")

    stage("阶段 4｜2022 年桑基图")
    fig = plot_sankey.build_figure(ledger_2022)
    out_html = plot_sankey.export_html(fig, config.FIGURES_DIR / "sankey_2022.html")
    print(f"已导出：{out_html}")
    try:
        out_png = plot_sankey.export_png(fig, config.FIGURES_DIR / "sankey_2022.png",
                                         width=1600, height=900)
        print(f"静态图：{out_png}")
    except Exception as exc:  # 缺 Chrome 时 kaleido 无法出图，不影响主流程
        print(f"静态图导出失败（{type(exc).__name__}），已跳过；HTML 不受影响")
    print(f"节点 {len(ledger_2022.kind)} 个，连线 {len(flows)} 条，"
          f"最小流量 {flows['value_MtP'].min():.4f} Mt P")

    stage("阶段 5｜2050 情景")
    from src.scenario import run_scenarios
    scen, base = run_scenarios(bundle, coefs)
    base_df = pd.DataFrame([base])
    scen.to_csv(config.RESULTS_DIR / "scenarios_2050.csv", index=False,
                encoding="utf-8-sig")
    base_df.to_csv(config.RESULTS_DIR / "baseline_2022.csv", index=False,
                   encoding="utf-8-sig")
    show = ["情景", "化肥施用(Mt P)", "粪肥还田(Mt P)", "磷矿需求(Mt P)",
            "环境流失(Mt P)", "农田PUE", "磷矿需求(Mt P)相对BAU(%)",
            "环境流失(Mt P)相对BAU(%)"]
    print(scen[show].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    sfig = plot_sankey.build_scenario_figure(scen)
    shtml = plot_sankey.export_html(sfig, config.FIGURES_DIR / "scenarios_2050.html")
    print(f"情景对比图：{shtml}")
    try:
        spng = plot_sankey.export_png(sfig, config.FIGURES_DIR / "scenarios_2050.png",
                                      width=1400, height=700)
        print(f"静态图    ：{spng}")
    except Exception as exc:  # 缺 Chrome 时 kaleido 无法出图，不影响主流程
        print(f"静态图导出失败（{type(exc).__name__}），已跳过；HTML 不受影响")

    from src.benchmark import build_comparison
    comp = build_comparison(bundle, scen, data_dir, ledger_2022,
                            extra_dir=extra_dir, coefficients=coefs)
    comp.to_csv(config.RESULTS_DIR / "comparison_table.csv", index=False,
                encoding="utf-8-sig")
    print("\n论文指标对照：")
    print(comp.to_string(index=False, na_rep="—"))

    stage("阶段 6｜参数网格与交互回归")
    reg_summary = {}
    if not args.skip_regression:
        from src.regression import build_sample, fit_interaction, pairwise_table
        sample = build_sample(bundle, coefs)
        sample.to_csv(config.RESULTS_DIR / "regression_sample.csv", index=False,
                      encoding="utf-8-sig")
        print(f"样本量 {len(sample)}（全因子网格 + LHS 补充）")
        reg_rows = []
        for target in ["总环境流失", "农田PUE"]:
            res = fit_interaction(sample, target)
            reg_summary[target] = res
            print(f"\n[{target}] R²={res['r2']:.4f}  adjR²={res['r2_adj']:.4f}  "
                  f"n={res['n']}  残差标准差={res['resid_std']:.3e}")
            if res["degenerate"]:
                print("  注意：拟合近似恒等线性，p 值与交互判定不可靠。")
            for k, v in res["coef"].items():
                if k == "const" or k.startswith("交互_"):
                    continue
                reg_rows.append({"因变量": target, "项": k, "标准化系数": v,
                                 "p值": res["pvalue"][k], "类型": "主效应"})
                print(f"  {k:<28} β={v:+.4e}  p={res['pvalue'][k]:.4g}")
            for k, v in res["interactions"].items():
                reg_rows.append({"因变量": target, "项": k, "标准化系数": v["beta"],
                                 "p值": v["p"], "类型": v["type"]})
                print(f"  交互 {k:<24} β={v['beta']:+.4e} p={v['p']:.4g} -> {v['type']}")
            pw = pairwise_table(sample, target)
            pw.to_csv(config.RESULTS_DIR / f"pairwise_{target}.csv", index=False,
                      encoding="utf-8-sig")
            print(f"  两两交互（{target}，已控制第三个政策变量）：")
            print("  " + pw.to_string(index=False,
                                      float_format=lambda x: f"{x:.4g}")
                  .replace("\n", "\n  "))
        pd.DataFrame(reg_rows).to_csv(
            config.RESULTS_DIR / "regression_coefficients.csv", index=False,
            encoding="utf-8-sig")
    else:
        print("已跳过回归")

    stage("阶段 7｜汇总输出")
    summary = {
        "data_notes": bundle.notes,
        "anchors_MtP": {
            "crop_harvest": bundle.crop_p,
            "animal_product": bundle.animal_p,
            "live_animal_excluded": bundle.live_animal_p,
            "fertilizer_use": bundle.fertilizer["Agricultural Use"],
            "fertilizer_production": bundle.fertilizer["Production"],
        },
        "conservation_2022": g,
        "acs_2022": acs.__dict__,
        "lbs_2022": model.notes,
        "regression": reg_summary,
    }
    with open(config.RESULTS_DIR / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2, default=float)
    print(f"结果表：{config.RESULTS_DIR}")
    print(f"图件  ：{config.FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
