# 广州退役动力电池二次锂资源供应与回收网络规划

方向A；基准2025年，规划期2026—2040年。课程第十二讲项目。

优先阅读：

- [完整规划报告](report/Environmental_Planning_Report.md)
- [数据与假设依据](data_cohort/README_data_sources.md)

## 主要口径

功能单位为产出含1kg锂元素的合格再生产品。A为规划期折现净成本最低，B为双目标前沿范围归一化后距理想点最近，C为累计实际再生锂最多。第双目标为累计净碳减排。ABC统一采用电网供电，优化变量为正规收集率与冶炼锂回收率；供电结构仅作独立敏感性分析。价格分别寻优，未来需求场景不作为可选择的工程决策。

模型含双队列退役、11区物流分配、国内/EU政策、LCA—TEA、分期能力与现金流、2346工况及压力测试。投资、周转资金与EPR服务费分别计算。成员分工及贡献比例见报告模块0，签名由本人确认。

## 从头复现

Python 3.14已验证；创建环境后安装固定依赖。在本目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r code_implementation/requirements.txt
.venv/bin/python code_implementation/run_all.py
```

运行数据模型不需要联网；安装依赖需要网络。需要重新检索时单独执行`refresh_sources.py`。`run_all.py`会覆盖生成的报告、图表及结果表，人工编辑应先另存或修改报告生成模板。

## 文件索引与运行顺序

| 路径 | 用途 |
| --- | --- |
| data_cohort/raw/、raw_current/、literature_raw/、course_references/ | 原始统计、政策、研究归档和课程论文 |
| data_cohort/vehicle_observations.csv | 观测值、口径、来源及页码 |
| data_cohort/parameter_evidence.csv | 文献数组/单元格证据 |
| data_cohort/assumptions_register.csv | 设计假设、依据和检验范围 |
| data_cohort/planning_assumptions.json、plan_parameters.json | 输入配置 |
| data_cohort/current_source_manifest.json、references.bib | 检索状态、哈希及论文元数据 |
| code_implementation/extract_inputs.py | 1. 从研究原件提取参数 |
| code_implementation/planning.py、model.py、policy_engine.py | 2. 预测、清单、逐年规划、政策与双目标寻优 |
| code_implementation/feasibility.py | 3. 委托/分期比较、空间能力、用地贮存与事故池 |
| code_implementation/test_models.py | 4. 政策、守恒、支配关系、工程与现金流测试 |
| code_implementation/document_sources.py | 5. 假设及来源索引 |
| code_implementation/figures.py | 6. 320DPI与矢量图 |
| code_implementation/report.py | 7. 报告和自包含HTML |
| code_implementation/validate_delivery.py | 8. 交付检查 |
| data_cohort/model_results/all_scenarios.csv、pareto_front.csv、anchors.json | 全部工况、非支配方案和ABC |
| data_cohort/model_results/anchor_annual.csv、recommended_inventory.csv | ABC逐年现金流及B清单 |
| data_cohort/model_results/projects.csv、implementation_comparison.csv | 工程清单与实施方式比较 |
| data_cohort/model_results/*balance.csv、tests.csv | 守恒和测试结果 |
| report/validation_run.log、delivery_checks.json、delivery_manifest.csv | 从头复现日志和交付核验 |

## 图表—正文对应

| 图 | 内容 | 正文章节 |
| --- | --- | --- |
| fig01_dmfa | 观测、车辆存量与退役量 | 1 |
| fig02_lithium | 退役化学结构与锂去向 | 2 |
| fig03_network | 区级物流网络与单元数比较 | 4.2 |
| fig04_carbon | 毛排放、信用及原生基准 | 5.1 |
| fig05_water_energy | 水—碳权衡、水与能量对照 | 5.1 |
| fig06_finance | 投资与年度服务费 | 5.2 |
| fig07_pareto | 双目标前沿及ABC | 5.3 |
| fig08_sensitivity | 固定B压力测试/分价格寻优 | 5.4 |
| fig09_capacity | 预测假设范围与分期能力 | 5.4 |
| fig10_pathways | 再利用延迟和材料修复探索 | 5.4 |

建厂前按报告列出的合同、性能保证和地块条件核查。未取得本地原件的EU法规保留下载失败状态，采用官方检索文本核查；不生成虚假归档或已获许可声明。

图11：成本—净减排辅助前沿与ABC单位锂碳足迹，对应报告7.4。数据为`environment_pareto_front.csv`。
