# 退役动力锂离子电池锂资源循环利用园区 —— 环境规划与管理综合实训交付包

> 《环境规划与管理》第十二讲 · 小组协同提交（成员 A/B/C 三方整合）
> 系统边界 `R1_2026_gate` · 功能单位 1 t 碳酸锂当量（LCE-eq） · 规划情景 **R1**（再生入口 60,579.50 t/a）

本目录是三方最终交付项目的**物理整合**：数据集、代码、图表与结果全部归入任务书 §6.1 规定的四目录结构中，可一键复现；数据与图均逐项溯源。

---

## 一、目录结构（任务书 §6.1）

```
lecture12-lib-recycling/
├── data_cohort/                 # 三方输入/输出数据集（含合并 README_data_sources.md）
├── code_implementation/         # 三方脚本（顶层 run_all.py 一键串行 A→B→C）
├── figures_output/              # 全部图（≥300 DPI，README_figures.md 为图清单）
├── report/                      # 最终报告 + drafts/ 分章草稿
│   ├── Environmental_Planning_Report.md
│   └── drafts/                  # A_*/B_*/C_* 分章草稿与来源备注
└── README.md                    # 本文件
```

## 二、三方成果映射

| 目录 / 文件 | 成员 A | 成员 B | 成员 C |
| :--- | :--- | :--- | :--- |
| **数据** `data_cohort/` | 市域 dMFA `dmfa_*`、物质流 `feedstock.csv`/`process_parameters.csv`/`mfa_*`、工程清单 `engineering_project_catalog.csv`、R1 `a_group_r1_scenario_20261104.json`；交接包 `A_*_20261103/` 已归入本目录 | 环境因子 `environmental_factors.csv`、文献迁移 `literature_override.json`/`parameter_override.json`、情景结果 `scenario_results.csv`；C 接口包 `给B_年度接口v2/`、`C发给B_LCOR接口包_20261103/` | 政策/经济参数 `policy_parameters.json`、`tea_case_template.json`；最终结果 `final_20261104/` |
| **代码** `code_implementation/` | `mfa_model.py`、`dmfa_yichang.py`、`plant_case.py`、`plant_case_r1.py`、`engineering_plan.py`、`plot_*.py`、`A_run_all.py` | `lca_model.py`、`scenario_analysis.py`、`optimization.py`、`literature_override.py`、`c_interface.py`、`c_annual_interface.py`、`c_lcor_conditional.py`、`B_run_all.py` | `policy_engine.py`、`tea_model.py`、`lcor_mac_model.py`、`build_final_data.py`、`make_figures.py`、`build_report.py`、`test_*.py` |
| **图** `figures_output/` | `fig1_*`~`fig6_*`（物质流 / dMFA / 工程 / R1） | `fig_b1`~`fig_b4`（环境维度） | `final_20261104/fig01~08`（物质平衡 / 情景 / 政策 / LCOR·MAC） |
| **报告** `report/` | 第 1/2 章、物质流与工程 | 第 5 章环境维度（`B_*` 草稿） | 第 3/4/5/6 章指标/投资/经济/管理（`C_*` 草稿） |

## 三、一键复现顺序

```bash
cd code_implementation
python run_all.py
```

内部顺序：**成员 A**（物质流+元素平衡、市域 dMFA、工程清单、R1、6 图）→ **成员 B**（LCA 情景仿真与优化，环境图）→ **成员 C**（最终数据表 `final_20261104/` + 政策判定 + 8 图）→ **单元测试**。

关键“产出→下游”依赖（复现前必读）：

1. A 的 `mfa_model.py` / `dmfa_yichang.py` / `plant_case.py` 读取归入 `data_cohort/` 的三个交接包：`A前期数据_IDE交接包_20261103/`、`A_dMFA数据交接包_20261103/`、`A_BC补充数据_20261103/`（已随包改路径，勿再移动）。
2. B 的 `c_interface.py` / `c_annual_interface.py` / `c_lcor_conditional.py` 对接 C 的引擎与接口包，路径已指向 `code_implementation/` 与 `data_cohort/`。
3. C 的 `policy_engine.py` / `tea_model.py` 由 B 的 `c_interface.py` 以裸名 import（两成员代码同目录共置），最终数据以 `data_cohort/final_20261104/` 为准。

## 四、自检要点（任务书 §八）

- **Li 守恒**：`mfa_model.py` 输出质量平衡校验；相对误差 < 0.05%（页面内 `README_data_sources.md` 与报告附录取值）。
- **政策单测**：`python test_policy_engine.py` → ≥3 PASS。
- **图 ≥300 DPI**：见 `figures_output/README_figures.md` 图清单，全部由脚本生成。
- **工程清单咬合**：`engineering_project_catalog.csv` 与第 2 章 MFA、第 5 章推荐方案口径一致（R1）。

## 五、环境依赖

- Python 3.10+；`pip install pandas numpy matplotlib`
- 报告 .docx 再生成（可选）另需 `python-docx`（`code_implementation/build_report.py`）。

## 六、口径与局限

- 三方统一 R1 口径：再生入口 **60,579.50 t/a**、LCE-eq 产量基数一致；未分配 Li 损耗拆分口径差异见 `report/Environmental_Planning_Report.md` 附录第 7 项（需组长裁定统一）。
- 价格为规划参考价、未取得成交原件；缺省值保持 UNKNOWN，不代填。
- 分工/贡献声明表中的姓名、GitHub 账号与贡献度为任务书强制必填项，须小组人工填写签认（报告模块 0.1）。