# lecture12-lib-recycling-B · 成员 B（LCA 环境维度）

本目录为第十二讲（废弃动力电池锂资源回收）**方向 B：产业园区/工程尺度** 成员 B 的工作空间，
负责全生命周期环境影响（LCA）核算、多情景仿真、敏感性分析与多目标帕累托寻优的环境端，
并生成环境维度出版物级图表。

- **功能单位**：1 t 电池级碳酸锂（Li₂CO₃）当量
- **系统边界**：摇篮到大门（收集运输 → 放电拆解 → 机械破碎分选 → 精炼再生 → 污染治理）
- **规划案例**：宜昌高新区退役动力电池循环经济产业园（本组选定基准，非基地实测数据）
- **主报告模组**：第 5 章 LCA/TEA（环境维度部分）与 `figures_output/` 环境类图表

---

## 1. 目录文件清单

| 路径 | 说明 |
| :--- | :--- |
| `data_cohort/environmental_factors.csv` | 单位活动量 GWP100 与水耗环境因子（电力/热能/试剂/运输/污染治理） |
| `data_cohort/scenario_results.csv` | `scenario_analysis.py` 自动生成的 3267 组工况结果 |
| `data_cohort/README_data_sources.md` | 数据字典与来源声明（必含） |
| `code_implementation/lca_model.py` | LCA 核算器（任务二） |
| `code_implementation/scenario_analysis.py` | 多情景仿真 ≥500 工况（任务三） |
| `code_implementation/optimization.py` | 敏感性分析与帕累托寻优、制图（任务四） |
| `code_implementation/c_interface.py` | 与成员 C 政策/经济引擎、成员 A 数据接口的对接层 |
| `code_implementation/c_annual_interface.py` | 接入成员 C 年度接口 v2（按 case_id + 五参数校验关联 C 逐工况 LCOR/政策/正式资格状态） |
| `code_implementation/c_lcor_conditional.py` | （历史）旧条件演示部分 LCOR 接入，已被年度接口 v2 替换，仅存档 |
| `code_implementation/make_conditional_lcor_demo.py` | （历史）旧纯湿法条件部分 LCOR 演示图，已停止调用，仅存档 |
| `code_implementation/run_all.py` | 一键复现编排（含 `--watch` 文件监听自动重跑） |
| `code_implementation/test_lca_model.py` | LCA 模型与情景/帕累托组件单元测试（8 项） |
| `figures_output/` | 代码自动生成的出版级图表（300 DPI） |
| `report/B_中期建模说明.md` | 成员 B 中期成果说明（方法论、中间结果、阻断清单） |
| `report/drafts/ch05_lca_environment.md` | 第 5 章 LCA 环境维度报告草稿 |

## 2. 环境依赖

- Python 3.10+（`pandas`、`numpy`、`matplotlib`）
- 无联网下载、无 Brightway 运行时依赖；政策/经济接口按路径自动定位成员 C 的
  `lecture12-lib-recycling/code_implementation/`。

## 3. 运行顺序与复现

```powershell
cd groups/group-02/lecture12-lib-recycling-B

# 0. 组件单元测试（LCA 闭合 / 电网水因子同步 / 情景网格 ≥500 / 帕累托排序）
python -m unittest code_implementation/test_lca_model.py -v

# 1~3 一键复现：仿真 + 寻优制图，并汇总 LCOR 就绪状态（推荐）
python code_implementation/run_all.py

# 或分步执行：
python code_implementation/lca_model.py          # LCA 模型自检（打印分项贡献与原生基准对比）
python code_implementation/scenario_analysis.py  # 多情景仿真（重写 data_cohort/scenario_results.csv）
python code_implementation/optimization.py       # 敏感性/寻优制图（读 scenario_results.csv，写 figures_output/）
```

文件监听模式（成员 C 年度接口 v2 `给B_年度接口v2/C_to_B_existing_case_status_v2.json`
变化即自动重跑一次，Ctrl+C 退出）：

```powershell
python code_implementation/run_all.py --watch
```

试用成员 A 候选能量参数（暂替换电/热两项活动量，试剂仍为占位；见
`code_implementation/a_candidate_override.py`）：

```powershell
$env:USE_A_CANDIDATES = "1"   # 启用；删除或置 "0" 恢复占位基准
python code_implementation/run_all.py
```

> 说明：A 的候选能量（ND_SEC 综合能耗 1729.26 kgce/t + LS_STEAM 蒸汽 1.1748 t/t粉料）
> 经黑粉锂品位与回收率换算后落在本功能单位上，可安全作为能量锚点。其试剂系数为
> 「商品吨 × 浓度 = 有效吨」（硫酸98%/液碱32%/氧化钙92%），NaOH 折纯后 ~2.856 t/t
> 量级合理；但 LS 路线进料/分配口径未核（M03/M06/M07/M10），仍不直接拼进全厂正式清单。

启用 A 全部数据并完成全部 B 任务（含 B-4 帕累托前沿，标记为**试算 PROVISIONAL**）：

```powershell
$env:USE_ALL_A_DATA = "1"   # 启用；删除或置 "0" 恢复严格正式口径
python code_implementation/run_all.py
```

> 说明：此主开关会一并启用 A 候选能量（含 not_adopted 的 H₂SO₄/NaOH/CaO 试剂系数）、
> 阈值试填分支指标（`USE_PROVISIONAL_BRANCH_METRICS`）与合成 LCOR（`USE_PROVISIONAL_LCOR`），
> 把正式结果资格放宽为「政策可行 + LCOR 非空」，生成 `fig_b4_pareto_frontier.png`
> （标题带「试算 PROVISIONAL」）。**这三类值均为候选/合成占位，非 A 实测、非 C 正式
> TEA，仅用于交付试算图与验证全流水线；最终正式报告须等 A 实测分支指标 + C 正式 LCOR 后
> 关掉本开关重跑。** 试算结果在 `scenario_results.csv` 中 `result_grade=provisional_all_a`
> 与正式结果（`formal`）严格区分。

`optimization.py` 依赖成员 C 的 `policy_engine.py` / `tea_model.py`（经 `c_interface.py`
导入）。每行结果带 `formal_result_eligible` 标记：仅当「政策判定未用阈值试填
（policy_source=formal_engine 且 feasible=1）且 LCOR 来自 C 正式 TEA（lcor_source=formal）」
时才进入帕累托前沿；合成 LCOR（`USE_PROVISIONAL_LCOR`）与阈值试填政策
（`USE_PROVISIONAL_BRANCH_METRICS`）的结果一律排除、仅作演示。正式结果未出现时只输出
环境维度图（fig_b1/fig_b2/fig_b3），帕累托前沿（fig_b4）不生成。

成员 C 年度接口 v2（2026-11-03，`给B_年度接口v2/`，替代旧条件演示包）：`scenario_analysis.py`
经 `c_annual_interface.py` 按 `case_id` + 五参数（process_mix/green_ratio/grid_ef/
lithium_price_usd/energy_efficiency）校验后并入 `c_annual_tea_status` /
`c_annual_policy_status` / `c_annual_lcor_rmb_per_t_LCE` / `c_annual_formal_result_eligible`
等新列。当前 C 侧全部 3267 工况为 `NOT_READY_ANNUAL_V2`（正式 LCOR 为空，不导入为 0、
不进入正式可行前沿）、政策 `UNKNOWN`；正式 `lcor_rmb_per_t` 列仍为空。旧条件演示
`partial_lcor_conditional_CNY_t_LCE`（纯湿法 297 工况）已停止调用，仅存档历史。

## 4. 图表清单与正文对应

| 图 | 文件 | 内容 | 对应报告位置 |
| :--- | :--- | :--- | :--- |
| B-1 | `fig_b1_environmental_contribution.png` | GWP100 / 水耗分项贡献拆解（基准参考工况） | 第 5 章 LCA 分项拆解 |
| B-2 | `fig_b2_water_carbon_tradeoff.png` | 水耗—碳排放权衡（颜色=电网碳强度） | 第 5 章 水-碳权衡分析 |
| B-3 | `fig_b3_sensitivity.png` | GWP100 单因素敏感性摆幅 | 第 5 章 敏感性分析 |
| B-4 | `fig_b4_pareto_frontier.png` | 政策约束下帕累托前沿与拐点标定（`USE_ALL_A_DATA=1` 下为试算 PROVISIONAL） | 第 5 章 多目标决策 |
| B-4-pre | `fig_b4_pareto_frontier_SYNTHETIC_PREVIEW_20261103.png` | 早期合成 LCOR+阈值试填的演示图（仅演示，非正式） | 不进入正文，仅存档演示 |
| B-4c | `fig_b4c_pure_hydro_conditional_lcor.png` | （历史）旧纯湿法条件部分 LCOR 演示图，年度接口 v2 下不再生成 | 不进入正文，仅存档历史 |

## 5. 数据来源声明

环境因子与原生矿产基准的逐条出处见 [README_data_sources.md](data_cohort/README_data_sources.md)。
试剂类因子标注「参考值待自主检索精确化」者，为骨架阶段文献量级取值，正式撰写第 5 章前须
以 Ecoinvent 3.9 或自主检索数据精确化，不作为最终结论引用。

## 6. 当前状态与阻断

- 已完成：LCA 核算、3267 组多情景仿真、环境维度敏感性分析、水碳权衡制图。
- 已完成（2026-11-03，响应成员 A 核查包 `A_BC核查与数据补充_20261103`）：
  * 新增 `formal_result_eligible` 正式结果资格标记，帕累托前沿排除合成 LCOR 与阈值试填政策结果；旧合成 B-4 图改名为 `..._SYNTHETIC_PREVIEW_...` 仅存档演示。
  * 修正 32% 液碱→纯 NaOH 浓度换算（`a_candidate_override.py`，NaOH 折纯 ~2.856 t/t 量级合理）。
  * `lca_model.py` 区分缺失/未映射活动量与「明确为零」，不再 `get(...,0)` 静默补零。
- 待成员 A：工序级活动量与分支回收率实测值（M02/M05/M06/M07/M08/M11），见
  `B发给A_数据需求清单与格式模板_20261103.json`；多产品分配口径 M10（B/C 联合）。
- 待成员 C：正式 TEA（`fu_per_year`、`whole_plant_*` 活动量、试剂/废污价格及可售产品
  篮）→ `evaluate_annual_case` 输出正式 `LCOR`；政策红线阈值 M14。
- 已接入（2026-11-03）：成员 C 年度接口 v2（`给B_年度接口v2/`），经 `c_annual_interface.py`
  逐工况关联；当前 C 侧全部 3267 工况 `NOT_READY_ANNUAL_V2`（LCOR 为空、政策 UNKNOWN），
  正式 `lcor_rmb_per_t` 仍为空，B-4 帕累托前沿待正式结果就绪后生成。