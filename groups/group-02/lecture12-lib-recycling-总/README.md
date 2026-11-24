# lecture12-lib-recycling（成员C最终版，2026-11-04）

本目录是成员C在R1物料流上的最终交付，覆盖第3—6章经济与管理部分、LCOR/MAC、960组情景、图表与复现脚本。原始A/B数据未被覆盖；本目录中的`data_cohort/final_20261104/`、`code_implementation/lcor_mac_model.py`、`figures_output/final_20261104/`、`report/final_20261104/`为新增。

## 运行顺序

```powershell
cd code_implementation
python build_final_data.py      # 物料流/环境清单/费用/960组情景
python make_figures.py          # 8幅300dpi PNG+SVG
python -m unittest test_policy_engine test_tea_model test_lcor_mac_model -v
python build_report.py          # 合并章节并生成DOCX
```

依赖：Python 3.10+；模型与测试仅标准库；制图matplotlib；DOCX用python-docx。

## 目录

- `data_cohort/final_20261104/`
  - `material_flow_R1.csv`：33条物料去向
  - `environmental_inventory_R1.csv`：同工况环境清单
  - `product_credits_R1.csv`：联产品原生抵扣
  - `economic_parameters_final.csv`：价格、费用、因子
  - `cost_breakdown_base.csv`、`revenue_breakdown_base.csv`
  - `scenarios_final.csv`：960组工况
  - `key_cases.csv`、`sensitivity_final.csv`、`summary.json`
  - `source_register.csv`、`policy_parameters.json`
- `code_implementation/`
  - `tea_model.py`、`policy_engine.py`、`test_policy_engine.py`（原清单）
  - `lcor_mac_model.py`、`test_lcor_mac_model.py`、`build_final_data.py`、`make_figures.py`、`build_report.py`
- `figures_output/final_20261104/`：图3-1、3-2、5-1—5-6
- `report/final_20261104/`：执行摘要、第3—6章、附录、完整MD/DOCX

## 关键口径

- 功能单位：1 t LCE-eq；边界：`R1_2026_gate`（到厂至出厂）。
- 采购价：组内5,200/8,800元/t仅作低价情景；推荐按可回收金属价值80%联动（LFP 11,414.52、NMC 23,560.15元/t）。
- 收入：参考价×实现系数，均为情景结算价值，不是已核实合同收入。
- 政策：基准R1为FAIL（Li 88.88%、Cu/Al 90%、研发0.336%）；合规改进为PASS（Li 92%、Cu/Al 98%、研发3%）。
- 未计：税费、建设期利息、营运资金、补贴、碳信用；不得把LCOR当会计利润。

## 与旧版的关系

旧`report/final_integration_20261103/`、`outputs/C接入R1_20261104/`保留为历史版本；本目录的R1数量（60,579.5 t/a再生、3,064.34 t LCE-eq）优先，不与旧59,500 t/a工况混用。旧“未列费用U=5,000万元/a”已由显式费用替代，不再叠加。

## 人工复核

AI辅助生成代码、计算与文字；成员C需逐项核对价格、政策条款、产品口径和贡献声明后签认。自动化测试通过不等于企业实测或法律合规。
