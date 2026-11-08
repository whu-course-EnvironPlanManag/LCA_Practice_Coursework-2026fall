# Lecture 12 · 方向 B：浙江衢州华友循环资源再生产业园退役动力电池再生精炼环境规划方案

> 课程作业：《环境规划与管理》Lecture 12 —— 退役动力电池循环再生（2026 秋季）
> 规划方向：**方向 B（产业园区／工程尺度）**
> 规划对象：**浙江衢州华友循环资源再生产业园**（衢州市智造新城，华友钴业循环板块）
> 功能单位：**1 t 退役动力电池**（LFP 60% / NMC811 35% / NCA 5% 混合来料）
> 设计产能：一期 **20,000 t/a**（2028）→ 远期 **60,000 t/a**（2035）；现状 6.5 万 t/a 电池料处理能力（华友公开口径）

---

## 一、选题简介

园区位于衢州市智造新城（衢州高新技术产业开发区），运营主体为衢州华友钴新材料有限公司与衢州华友资源再生科技有限公司，均进入工信部综合利用规范条件企业名单。华友公开口径具备年处理废旧电池料 **6.5 万 t** 产能；2025 年 2 月衢州市生态环境局智造新城分局受理其“新增年处理 **10,000 t** 电池再生循环利用改造项目”环评（年减废水 43.8 万 t、回收硫酸钠 2.19 万 t）。园区以衢州基地为中心辐射长三角（浙江、江苏、上海、安徽）收集网络，服务半径 200 km，紧邻衢江（钱塘江上游）生态屏障区。

方案以“**水—碳协同 + 合规 + 盈利**”三目标为主线：以工信部《规范条件（2024 年本）》与 EU 2023/1542 为硬约束，在“绿电消纳比例 × LFP 直接再生比例”二维决策空间中寻优，得到推荐拐点（绿电 55%、直再 60%）：碳足迹 1,140 kg CO₂e/t（较原生 −77.2%）、水耗 8.80 m³/t（−67.1%）、LCOR −5,725 元/t（净收益）、NPV 11.24 亿元、回收期 3.83 a。

---

## 二、目录结构

```text
lecture12-lib-recycling/
├── README.md                          # 本文件：选题、运行、图表清单与交付说明
├── data_cohort/                       # 数据层（唯一参数源 + 全部计算结果）
│   ├── ABC_parameters.json                # 单一参数源（园区/来料/工艺/LCA/TEA/情景/远期）
│   ├── A_mfa_results.json               # A 模块：MFA 与守恒核验结果
│   ├── A_mfa_balance_table.csv          # 八元素收支平衡表
│   ├── B_policy_results.json            # B 模块：11 条断言 × 3 工况
│   ├── B_policy_review.json            # B 扩展：逐项全范围法规审查
│   ├── B_policy_review.csv             # B 扩展：法规状态及证据明细
│   ├── B_policy_financial_adjustments.csv # 条件性碳价值与欧盟溢价估算
│   ├── B_policy_route_allocation.csv   # 拐点路线分配与年通量
│   ├── B_policy_parameters.json         # 【补充校验工具】政策规则检查参数
│   ├── B_policy_scenario_results.csv    # 【补充校验工具】政策规则场景校验结果
│   ├── B_policy_decision_grid.csv       # 【补充校验工具】政策决策网格
│   ├── B_process_allocation.csv         # 【补充校验工具】工艺分配旁支分析结果
│   ├── C_lca_tea_results.json           # C 模块：情景/LCA/TEA/帕累托/敏感性/财务/远期
│   ├── C_pareto_front.csv               # 基准锂价 21 组非支配解
│   ├── C_pareto_front_by_price.csv      # 三档锂价 63 组前沿
│   ├── C_sensitivity.csv                # 5×5 电网因子 × 锂价网格
│   ├── C_water_carbon_curve.csv         # 3 电网 × 21 绿电档
│   └── ABC_README_data_sources.md         # 数据字典、来源类型、补充检索记录
├── code_implementation/               # 代码层（01→03→B扩展→04）
│   ├── A_mfa_model.py                   # 工序级 MFA、八元素守恒、年通量
│   ├── B_policy_engine.py               # 主流程：政策断言引擎、三工况单元测试
│   ├── C_lca_tea_pareto.py              # LCA / TEA / 819 组帕累托 / 财务 / 敏感性
│   ├── B_policy_completion.py           # B 扩展核查、政策财务估算与6项测试
│   └── C_integrated_figures.py          # 9 张 300 dpi 图表自动渲染
│   ├── B_policy_rule_checker.py         # 【补充校验工具】政策规则旁支，不属于主流程
│   ├── B_process_allocation.py          # 【补充校验工具】工艺分配旁支，不属于主流程
│   └── C_*_supplement.py（共 7 个）     # 【补充副本】并行对照分析，不属于主流程
├── figures_output/                    # 图件层（fig1—fig9，300 dpi PNG）
└── report/                            # 文字层
    ├── Environmental_Planning_Report.md              # 主报告（模块 0—7）
    ├── B_policy_analysis.md                           # B模块结论摘要（与C拐点对齐）
    ├── B_政策与规制核查补充报告.md                   # B 模块法规、财务与路线核查
    ├── C_环境经济与决策_专题报告.md                  # 【C 模块独立文件】LCA-TEA 与决策分析
    └── 汇报演示稿_Lecture12.pptx                     # 汇报 PPT
```

---

## 三、环境依赖与运行

**依赖**：Python ≥3.10、numpy、matplotlib（中文需 Microsoft YaHei 字体），PPT 生成需 Node.js + pptxgenjs（可选，不影响数据与图件复现）。

```bash
cd code_implementation
python A_mfa_model.py           # 约 1 s，输出 A_mfa_results.json / A_mfa_balance_table.csv
python B_policy_engine.py       # 约 1 s，输出 B_policy_results.json
python C_lca_tea_pareto.py      # 约 3 s，输出 C_lca_tea_results.json 与 4 个 CSV
python B_policy_completion.py   # B 扩展：读取A/C结果，复核法规并估算条件性政策收益
python C_integrated_figures.py  # 约 15 s，输出 figures_output/fig1—fig9（300 dpi）
```

**可复现性**：分清两类计算。【可复现随机模拟】C 的补充敏感性分析包含蒙特卡洛模拟，固定随机种子 `20261108`，抽样 5,000 次；输入与种子不变时结果可复现，该分析属于并行对照补充，不属于主流程。【零随机确定性模型】主流程的 MFA、政策规则及 LCA/TEA 网格寻优不抽样、不调用随机数，给定输入后重复运行结果一致。主流程 C 分析唯一入口为原版 `C_lca_tea_pareto.py`，其 7 个 `_supplement` 文件仅用于并行对照分析。A/C 主流程以`ABC_parameters.json`为参数源；B 扩展脚本读取`ABC_parameters.json`及MFA、政策和LCA/TEA结果，改动输入后须按上述顺序重跑，才能同步报告和图表。

**旁支文件说明**：【补充校验工具】`B_policy_rule_checker.py`、`B_process_allocation.py` 及其配套 `B_policy_parameters.json`、`B_policy_scenario_results.csv`、`B_policy_decision_grid.csv`、`B_process_allocation.csv` 属于政策扩展旁支分析，不属于主流程。

**脚本头部规范**：每个脚本 docstring 均记录【AI 辅助编程说明】（Prompt 摘要 + 人工校验修正项），符合任务书要求。

---

## 四、图表清单（全部由代码生成，≥300 dpi）

| 编号 | 文件 | 内容 | 主导模块 | 引用章节 |
| :--- | :--- | :--- | :---: | :--- |
| 图 1 | `fig1_mfa_process_flow.png` | 园区多工序物质流拓扑（框—箭头结构，避免桑基图在盐类增重时误导） | A | 主报告 2.1—2.4 |
| 图 2 | `fig2_lca_scenarios.png` | 原生基准 vs 三情景碳足迹—水耗双指标对比 | C | 主报告 5.1；C 报告 §2.1 |
| 图 3 | `fig3_gwp_breakdown.png` | 碳足迹分项拆解（电/热/试剂/运输） | C | 主报告 5.2；C 报告 §2.2 |
| 图 4 | `fig4_water_carbon_tradeoff.png` | 三种电网结构下的水—碳权衡曲线 | C | 主报告 5.3；C 报告 §2.3 |
| 图 5 | `fig5_pareto_front.png` | 帕累托前沿（三档锂价）+ 拐点标定 + MACC | C | 主报告 5.5；C 报告 §5 |
| 图 6 | `fig6_sensitivity_heatmap.png` | 锂价 × 电网因子双因素敏感性热图 | C | 主报告 5.6；C 报告 §6.1 |
| 图 7 | `fig7_route_and_scale.png` | 三路线强度对比 + 年通量 + 远期扩容 | A/B | 主报告 2.5、4.4、5.7 |
| 图 8 | `fig8_cashflow_npv.png` | 锂价—LCOR 四配置曲线 + 20 年累计现金流/NPV/回收期 | C | 主报告 5.8；C 报告 §3.4、§4 |
| 图 9 | `fig9_tornado_cost.png` | 单因素龙卷风图 + 成本—收入水平堆叠结构 | C | 主报告 5.9；C 报告 §6.2 |

> 正文与 PPT 中所有图表均按“图 N”编号引用，图下均标注数据来源（`C_lca_tea_results.json` / `A_mfa_results.json`）。

---

## 五、数据—模型—图表—章节映射

| 数据文件 | 生成脚本 | 支撑图表 | 支撑章节 |
| :--- | :---: | :--- | :--- |
| `A_mfa_results.json`、`A_mfa_balance_table.csv` | 01 | 图 1、图 7 | 主报告第 2 章、4.4 节 |
| `B_policy_results.json` | 02 | —（表 3-2、3-3） | 主报告第 3 章 |
| `B_policy_review.json` / `.csv` | b_policy_completion | 逐项合规及待核验证据状态 | 主报告第 3、6 章；B补充报告 |
| `B_policy_financial_adjustments.csv` | b_policy_completion | 碳价值与欧盟溢价条件性估算 | 主报告第 6 章；B补充报告 |
| `B_policy_route_allocation.csv` | b_policy_completion | 拐点三路线分配与年通量 | 主报告第 4 章；B补充报告 |
| `C_lca_tea_results.json` | 03 | 图 2—9 | 主报告第 5 章；C 专题报告全文 |
| `pareto_front*.csv` | 03 | 图 5 | 主报告 5.5；C 报告 §5 |
| `C_sensitivity.csv` | 03 | 图 6 | 主报告 5.6；C 报告 §6.1 |
| `C_water_carbon_curve.csv` | 03 | 图 4 | 主报告 5.3；C 报告 §2.3 |

**关键结论锚点（均取自 `C_lca_tea_results.json`）**：

| 指标 | 数值 |
| :--- | :--- |
| 拐点配置 | 绿电 55% / LFP 直再 60% |
| GWP（kg CO₂e/t） | 1,140（较原生 −77.2%） |
| 水耗（m³/t） | 8.80（较原生 −67.1%） |
| LCOR（元/t） | −5,725（净收益） |
| MAC（元/t CO₂e） | −2,933（负成本减排） |
| NPV / 回收期 | 11.24 亿元 / 3.83 a |
| 政策可行解 / 非支配解 | 819 组 / 21 组（C 模块累计 985 组工况） |
| 年净减碳 / 年节水 | 77,190 t CO₂e / 358,097 m³ |
| 2035 年（60,000 t/a、100% 绿电） | 490 kg CO₂e/t；年减碳 27.06 万 t；年节水 113.0 万 m³ |

---

## 六、A/B/C 分工与交付边界

| 角色 | 负责模块 | 代码/文件 | 报告章节 | 贡献度 |
| :--- | :--- | :--- | :--- | :---: |
| A 数据与物质流（邱自强，组长） | 组内统筹；编制、核验并维护[A_数据手册](report/A_数据手册.md)；基础数据与来源、MFA/dMFA 与守恒核验、规模与组成参数 | `A_mfa_model.py`、`data_cohort/A_mfa_*`、`report/A_数据手册.md` | 第 1、2 章 | 32% |
| B 选题与政策规划（彭冬明） | 选题、法规标准参数、政策合规引擎、指标与工程实施方案、最终报告统稿 | `B_policy_engine.py`、`B_policy_completion.py`、B政策结果文件 | 第 3、4、6 章及最终报告 | 30% |
| C 环境经济与决策（边久加措） | 环境与成本清单、LCA/TEA、≥500 组情景、方案比选、自动制图、财务 | `C_lca_tea_pareto.py`、`C_integrated_figures.py` | 第 5 章 + `C_环境经济与决策_专题报告.md` | 38% |

协同约定：B 负责选题与最终报告统稿，A 负责组内统筹与物料规模核验，B 负责合规与工程规划，C 负责环境经济评价；摘要、缩写表、参考文献与一致性检查纳入 B 的最终报告统稿，全员交叉审阅。

> **提交前请确认**：PPT 封面“汇报人：______”及全员分工确认状态。

---

## 七、数据来源与缺失数据补充

- 预编译文献 6 篇（`starter_materials/.../precompiled_references`）提供来料组成、回收率、能耗/水耗/碳强度、价格情景与政策阈值。
- 官方统计/标准：生态环境部《2022 年电力二氧化碳排放因子》、工信部《规范条件（2024 年本）》、EU 2023/1542、GB/T 33598 系列、IPCC (2006)、GREET 2021。
- **园区公开数据（补充检索，4 条可核实来源）**：华友钴业 e 互动 6.5 万 t/a 产能答复（2021-07-23）；衢州华友 1 万 t/a 改造项目环评受理（2025-02）；华友循环“衢州基地辐射长三角”与年回收 5,783 t 钴（2019-09-18）；华友官网循环产业闭环。检索路径与命中要素详见 `data_cohort/ABC_README_data_sources.md` §8。
- **未取得数据**：浙江省级电网因子（保守取全国平均 0.5366，敏感性 0.314—0.749）；衢州本地精确水价（量级取值 3.6／6.0 元/m³）；来料 SOH 分布（60% 直再上限为工程假设）。全部在参数文件中标注类型并给出影响方向，**未编造任何实测值**。

---

## 八、交付清单

| 类别 | 文件 | 状态 |
| :--- | :--- | :---: |
| 数据 | `data_cohort/*.json`、`*.csv`（9 个结果文件 + 参数源 + 数据字典） | ✅ |
| 代码 | `code_implementation/A_*.py`、`B_*.py`、`C_*.py`（含 AI Prompt 记录与人工校验说明） | ✅ |
| 图件 | `figures_output/fig1—fig9`（300 dpi，全部被正文引用） | ✅ |
| 报告 | `report/Environmental_Planning_Report.md`（模块 0—7） | ✅ |
| 报告（B 摘要） | `report/B_policy_analysis.md` | ✅ |
| 报告（B 独立） | `report/B_政策与规制核查补充报告.md` | ✅ |
| 报告（C 独立） | `report/C_环境经济与决策_专题报告.md` | ✅ |
| 汇报 | `report/汇报演示稿_Lecture12.pptx` | ✅ |

**提交要求**：按任务书在指定分支提交 Pull Request，PR 描述中附组号、A/B/C 分工与复现命令；不提交 `figures_output` 以外的大体积中间文件。
