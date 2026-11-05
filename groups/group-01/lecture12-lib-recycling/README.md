# 湖北省退役动力电池锂资源回收：方向A

本项目按第十二讲任务书6.1整合陈海滨原代码与组员新增数据，正文为有证据边界的**条件情景规划报告**。数据存在未核实的安装队列、寿命、工艺与费用代理，不能称为湖北实证预测、全省最优选址或完整工程可研。来源和16项审查发现分别见[data_cohort/README_data_sources.md](data_cohort/README_data_sources.md)和[report/Data_and_Code_Audit.md](report/Data_and_Code_Audit.md)。

## 目录与交付

```text
lecture12-lib-recycling/
├── data_cohort/          # CSV/JSON输入、raw/原始资料、audit/输入审查、results/计算表和日志
├── code_implementation/  # 一键入口、计算模型、制图、报告生成和核验
├── figures_output/      # 仅PNG，300 DPI；每张图都在报告中引用
├── report/              # 完整报告、组员原框架及数据代码核查说明
└── README.md
```

[完整报告](report/Environmental_Planning_Report.md)含模块0—7、三人成员分工、指标矩阵、五项工程组成、A/B/C比选与全部图片。贡献比例按用户指示为33.33%、33.33%、33.34%；签字及GitHub账号仍由本人确认。原有讲义保留在相邻课程文件夹，原论文、17份拓展来源文件与年鉴统一移至`data_cohort/raw/`，不保留多套源码。

## 运行

Python 3.10以上。在本目录执行：

```powershell
python -m pip install -r code_implementation/requirements.txt
python code_implementation/run_project.py --exploratory
```

`--exploratory`明确接受使用未完全核验的研究情景；省略时阻止运行，以避免误称实证预测。运行不联网，不自动add、commit、push。`build_report.py`会按当前结果重建报告，人工修改正文后不要无意重建。

逐步运行顺序：

```powershell
python code_implementation/run_analysis.py --self-test
python code_implementation/run_analysis.py --check-inputs
python code_implementation/run_analysis.py --plot-yearbook
python code_implementation/run_analysis.py --run --exploratory
python code_implementation/postprocess.py
python code_implementation/build_report.py
python code_implementation/validate_submission.py
```

需要重新提取.xls时，单独运行`run_analysis.py --extract-yearbook`；依赖xlrd。该动作会更新提取CSV，随后须重新运行完整计算。已有提取结果随项目保存，不需要每次重新读取原件。

## 脚本索引

| 文件 | 职责 |
| --- | --- |
| `run_project.py` | 按顺序测试、检查、计算、绘图、生成报告并跨文件核验 |
| `common.py` / `input_data.py` | 路径、单位、来源、数值和接口校验；数据结果与图片分开 |
| `extract_yearbook.py` / `plot_yearbook_context.py` | 只读提取20表并绘制真实背景统计 |
| `dmfa_model.py` | Weibull年度CDF差分、安装年参数、梯次库存及Li/Ni/Co/Mn收支 |
| `policy_engine.py` | 课程数值筛选、欧盟日期、显式税费/信用及湖北直接工业取水累进税示例 |
| `lca_tea.py` | LCI、LCE换算、CRF、收益与MAC，区分主产品售价和成本 |
| `network_model.py` | 容量约束MILP；当前仅一精炼点，不能证明全省最优选址 |
| `decision.py` | 容差内等价保留、非支配排序、归一化理想点A/B/C |
| `run_analysis.py` | 4000组合、1800规划目标不满足工况、2200可用条件情景 |
| `plot_results.py` | 从数值结果自动制图，合并两种原生基准的重复图 |
| `postprocess.py` | 年度与物流汇总、已计费用拆解、可复现资本敏感性 |
| `plot_dmfa.py` | 汇总逐年锂流并校验去向，绘制二次锂供应与代表年比例流图 |
| `build_report.py` | 数值驱动报告、成员分工及图表引用 |
| `test_models.py` / `validate_submission.py` | 27项模型测试及跨文件一致性、原始哈希、图文引用等核验 |

## 图片与正文对应

| PNG文件 | 正文 |
| --- | --- |
| `fig0a_yearbook_private_cars`、`fig0b_yearbook_electricity`、`fig0c_yearbook_city_electricity` | 第1章真实年鉴背景 |
| `fig1_stock_and_retirement` | 第2章在用锂与分体系首次退役锂 |
| `fig11_dmfa_lithium_flows` | 第2章年度二次锂供应及2030年B的锂流去向，新增图2-2 |
| `fig6_network_brine` | 第4章固定目的地运输示意；不是全省最优选址 |
| `fig7_primary_comparison_brine` | 第5章两种原生参考与B，同一图中展示 |
| `fig5_breakdown_0_brine`、`fig5_breakdown_1_brine` | 第5章碳影响/水耗分项 |
| `fig3_water_carbon_brine` | 第5章水—碳情景关系 |
| `fig5_breakdown_2_brine`、`fig9_cost_revenue` | 第5章过程/物流费用及全部已计费用与收入 |
| `fig10_capital_sensitivity` | 第5章资本与利用率代理敏感性 |
| `fig2_pareto_brine`、`fig4_sensitivity_brine`、`fig8_price_profit_brine` | 第5章前沿、双因素敏感性及匹配报价后的价格敏感性 |

文件名中的`brine`是保留的计算索引。绝对GWP/水耗/LCOR相同而只改变原生比较基准的重复图已合并；两种基准的MAC、减排及节水差异仍在CSV和正文中分别列示。

## 数值文件与边界

`data_cohort/results/`保存基准物质流、元素收支、全部情景、两套前沿、锚点、与锚点同工况的网络/工程/LCI/物质流表、年度/物流汇总、资本敏感性、输入哈希和核验记录。工程表中的已计CAPEX=0代表漏项/本次未计，不是零投资概算；完整项目总预算仍缺。

环境分配已由无匹配副产品证据的0.32改为1。省级电力CO₂与其他生命周期代理存在边界差异，故结果称筛查值。未把NCA-equivalent原论文值用作LCE；直接正极修复不冒充碳酸锂。模型只优化2030年代表工况；2040年容量不足已写入报告，不提供未算出的远期最优扩建方案。

界面`ready`或字段通过不能证明原始证据完整，数据审查是独立限制。自动验证不会替代成员人工签字或真实厂址、许可和投资审查。
