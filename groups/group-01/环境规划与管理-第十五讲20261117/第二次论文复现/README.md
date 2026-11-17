# 第十五讲论文复现：全球人为磷循环 MFA 与可持续策略（Liu et al. 2026, PNAS）

复现文献：Liu et al. (2026) *Future strategies for phosphorus sustainability amid
worsening global cycle imbalances*, PNAS 123(13): e2512673123。

覆盖课程任务书三项核心任务：

1. **任务 1**：数据清洗 + 农田种植子系统（ACS）磷流动模型，输出 2022 年各流向；
2. **任务 2**：PMS/CIS/ACS/LBS/RCS 五子系统 1961–2022 全球磷物质流分析（MFA），
   全系统质量守恒自检（相对误差 < 1e-4），Plotly 交互式桑基图；
3. **任务 3**：2050 年 BAU 外推 + "3R"情景模拟（Reduce/Replace/Recycle/组合），
   66 组品类两两交叉敏感性回归（标准化系数、p 值、协同/拮抗判定）。

所有数值均来自 `source_data` 原始数据文件与论文 SI 系数表，无任何人工编造。

## 目录结构

```
第二次论文复现/
├── run_all.py            # 一键运行入口（任务1→2→3→基准对照）
├── README.md             # 本文件
├── 复现报告.md            # 复现结果、基准对照与偏差分析报告
├── src/
│   ├── config.py         # 路径与常量（全部相对本目录解析，无硬编码盘符）
│   ├── params_si.py      # 论文 SI Table S3/S4 系数（作物吸收/收获系数、β、κ、α 等）
│   ├── data_load.py      # 数据加载与清洗（宽表/化肥/磷矿/耕地/畜禽/人口/贸易/预测）
│   ├── acs_model.py      # 任务1：ACS 种植系统模型类（参考作者 ACSPModel 公式）
│   ├── mfa_model.py      # 任务2：五子系统全球 MFA + 守恒断言
│   ├── sankey.py         # 任务2：2022 年全链条桑基图（Plotly → HTML）
│   ├── scenarios.py      # 任务3：2050 BAU 与 3R 情景
│   └── cross_sensitivity.py  # 任务3：66 组品类组合交叉敏感性回归（vs 论文返修基准表）
└── output/
    ├── csv/              # 运行生成的结果表
    ├── html/             # sankey_2022.html 交互式桑基图
    └── figures/
```

## 运行环境

- Python 3.10+（开发验证环境：Python 3.12，Windows）
- 依赖库：`pandas` `numpy` `plotly` `statsmodels` `scikit-learn` `openpyxl`

```bash
pip install pandas numpy plotly statsmodels scikit-learn openpyxl
```

## 一键运行

在本目录（`groups/group-01/环境规划与管理-第十五讲20261117/第二次论文复现/`）下执行：

```bash
python run_all.py
```

运行约 1–2 分钟，控制台依次输出：

- 任务 1：2022 年 ACS 全部流向（Mt P）与守恒自检结果；
- 任务 2：1961–2022 MFA 关键序列表、全系统守恒断言（rel_err < 1e-4）、桑基图路径；
- 任务 3：2050 情景对比表、66 组合交叉敏感性统计与交互类型计数；
- 核心指标基准对照表（复现值 vs 论文标称值及相对偏差）。

**数据路径约定**：`src/config.py` 以本项目目录的上一级（`环境规划与管理-第十五讲20261117/`）为锚点，
自动定位同级的 `source_data/` 目录。
只要本项目目录与 `source_data/` 保持同级关系即可直接运行，
无需修改任何路径；若单独拷贝本项目，请同步拷贝 `source_data/` 目录并调整
`config.py` 顶部的 `LECTURE_DIR` 锚点。

## 输出清单（`output/`）

| 文件 | 内容 |
| :--- | :--- |
| `csv/acs_annual_flows.csv` | 1961–2022 逐年 ACS 全部流向（吨 P） |
| `csv/mfa_annual_flows.csv` | 1961–2022 全球五子系统年度 MFA 记录（28 个指标列） |
| `csv/scenarios_2050.csv` | 2050 BAU + 4 个 3R 情景指标（Mt P 与相对变化率） |
| `csv/cross_sensitivity_66.csv` | 66 组品类两两回归（2022 单年与全期合计两切片）：标准化主效应/交互系数、p 值、交互类型 |
| `csv/benchmark_comparison.csv` | 核心指标基准对照表 |
| `html/sankey_2022.html` | 2022 年全球磷全链条交互式桑基图（浏览器打开） |

## 口径要点（详见《复现报告.md》）

- 矿物磷肥投入：FAOSTAT Nutrient（P2O5）× 0.4364 折纯磷，国家级加总；
- ACS 作物吸收/收获：SI Table S3 系数 × FAOSTAT 19 类作物产量（作物系数口径）；
- PUE_c 分母为"可利用磷输入"（化肥+粪肥还田+秸秆还田+人粪尿还田+沉降），
  不含 SD（其他磷输入按参考类定义为沉积入土项）；
- LBS 饲料输入因数据集缺草地放牧/工业饲料活动数据，采用平衡闭合估算；
- PMS：USGS 1998–2021 实测，1961–1997 按"约 80% 磷矿用作化肥"（论文 SI）反推；
- 世界农村人口份额 0.43 为 UN WUP 外生假设，用于人粪尿还田城乡加权。
