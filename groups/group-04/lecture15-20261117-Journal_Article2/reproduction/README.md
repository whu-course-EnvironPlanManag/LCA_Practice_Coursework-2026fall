# Lecture 15 顶刊复现：全球磷循环失衡与 3R 策略

> 复现对象：Liu et al. (2026), *Future strategies for phosphorus sustainability amid worsening global cycle imbalances*, **PNAS**（starter_materials/lecture15-20261117-Journal_Article2）。
> 复现目录：`reproduction/`｜语言：Python 3.12｜依赖：numpy、pandas、plotly、statsmodels、scikit-learn、matplotlib、openpyxl。

## 1 目录结构

```
reproduction/
├── code/
│   ├── p_config.py            # 路径、单位换算、2022 流量参数与来源标注、2050 锚点
│   ├── p_data.py              # Task 1 真实数据：作物纯磷产出、含磷率字典、化肥施用、人口预测
│   ├── p_acs.py               # ACS 种植子系统类 + 人口驱动的 2050 BAU 外推
│   ├── p_sfa_model.py         # 六个子系统类 + 守恒校验 + 情景引擎 + 交叉敏感性回归
│   └── run_reproduction.py    # 主流程：数据工程 → ACS → BAU → 2022 磷流 → 桑基图 → 情景 → 回归
├── data_processed/            # 运行生成（JSON/CSV）
├── figures/                   # 运行生成（1 个交互式桑基 HTML + 4 张 300 dpi PNG）
└── report/顶刊复现报告.md       # 复现报告（约 2,500 字）
```

## 2 运行方式

```powershell
cd "…/lecture15-20261117-Journal_Article2/reproduction"
& "d:\cxdownload\.venv312\Scripts\python.exe" code\run_reproduction.py
```

脚本按 01→06 顺序无交互执行，约 30 s。控制台依次输出数据工程摘要、ACS 与全局守恒校验、人口外推 BAU、2050 情景对比表、**多元回归统计表（变量/系数/标准误/t/p/交互类型）**与 7 项复现偏差；任一子系统或全局相对误差 >1e-4 会直接抛错终止。

## 3 输出清单

| 文件 | 内容 |
| :--- | :--- |
| `data_processed/crop_p_production_1961_2022.csv` | 全球作物纯磷产出（1961—2022，Mt P/a，来自 `product_P_result (tons)` 的 World 行） |
| `data_processed/crop_p_category_2022.csv` | 2022 年 12 个产品类别的纯磷产出 × 含磷率字典（跨表连接结果） |
| `data_processed/fertilizer_p_1961_2021.csv` | FAOSTAT Agricultural Use 全球化肥施用（P₂O₅→P，Mt P/a） |
| `data_processed/population_projection.csv` | UN WPP 2024 世界人口：2022 估计值与 2050 中方案 |
| `data_processed/acs_2022.json` | ACS 类 2022 年输入、吸收、径流、土壤遗留与 PUE，含守恒误差 |
| `data_processed/bau_2050.json` | 人口驱动的 2050 BAU：人口倍数、膳食系数、食物/化肥需求与损失 |
| `data_processed/global_p_production_1998_2021.csv` | USGS 39 国磷矿石产量 → 折合磷（Mt P） |
| `data_processed/flows_2022.json` | 2022 年七个子系统的输入/输出/库存、29 条链接、闭合误差、PUE 指标 |
| `data_processed/scenario_2050.csv` | 2050 BAU 与 5 个 3R 情景的 NPR／CFR／损失 |
| `data_processed/regression_coefficients.csv` | 300 组拉丁超立方样本的含交互项 OLS 系数、标准误、p 值，`type` 列按任务书 4.4 判定为主效应／协同增强／拮抗削弱／无显著交互／常数项 |
| `data_processed/reproduction_summary.json` | 全部关键结果与复现偏差的机器可读汇总 |
| `figures/sankey_2022_global_p.html` | 2022 年全球磷流桑基图（Plotly 交互版，plot.js 已内嵌，离线双击可交互） |
| `figures/fig_task1_data.png` | Task 1 数据工程：1961—2022 作物纯磷产出、化肥施用与磷矿开采 |
| `figures/fig_global_p_production.png` | 1998—2021 年磷矿石与折合磷产量双轴图 |
| `figures/fig_scenarios_2050.png` | 2050 年情景绝对量与相对 BAU 削减率（正值向上） |
| `figures/fig_regression_interactions.png` | 标准化回归系数、95% 置信区间与显著性 |

## 4 数据来源说明（重要）

`source_data/` 中的原始数据包共 483 个文件，本复现**直接读取、不改数**，用到其中 4 个：

| 用途 | 原始文件 | 处理方式 |
| :--- | :--- | :--- |
| 作物纯磷产出 1961—2022 | `Supplementary_dataset_PNAS_First_Revision/1.*/Agricultural products_P_result_national level（1961-2022）.xlsx` | 只取 `World` 汇总行，避免与 Africa/Asia 等汇总行重复计数；13 个字母类别汇总为 Mt P/a（其中 12 类有含磷率字典） |
| 含磷率字典 | `3.P content coefficient of products_Production.xlsx` | 279 种产品按 A—M 类别聚合，与上表做跨表连接 |
| 化肥施用 1961—2021 | `Origin data/7.*/Nutrient phosphate P2O5 use data at the national level.csv` | `Element=Agricultural Use`、`Unit=t`，按国家求和后 ×0.4364 折合纯磷 |
| 人口预测 | `7.Global population projection data ...xlsx` | `Estimates` 取 2022 年、`Medium variant` 取 2050 年世界值 |

仍需文献口径或工程假设的量（化肥 2022 年 20.5 Mt P、粪肥还田率、污泥回用率、填埋/排放分配）在 `p_config.py` 的 `SOURCE_2022` 中逐项标注；2050 年的一半参数（膳食升级系数、化肥强度改善）在 `p_acs.project_bau` 中显式列出并可一键改值重算。

> 注：仓库 `git clone` 在 Windows 上曾因路径超长（>260 字符）导致 `checkout` 失败，`source_data/` 起初只落盘 1 个短路径文件。以 `git -c core.longpaths=true checkout HEAD -- <path>` 恢复后 483 个文件齐全，Task 1 才得以用真实数据完成。

## 5 主要结果（详见报告）

- Task 1：作物纯磷产出 1961 年 **8.97** → 2022 年 **26.72 Mt P**（约 3.0 倍）；化肥施用 1961 年 **4.81** → 2021 年 **24.63 Mt P**；ACS 类闭合误差 0.00e+00。
- 2022 年体系输入 34.73 Mt P＝终端汇 34.73 Mt P，相对误差 **0.00e+00**；七个节点全部闭合。
- 农田 PUE **31.4%**、化肥占农田输入 **65.1%**、畜禽 PUE **23.1%**，与文献 31%／约 64%／23% 偏差 ≤1.4%。
- 人口驱动 BAU（×1.205 人口、膳食系数 1.34）给出 2050 年食物 **16.0**、化肥 **26.5** Mt P，与论文 16.2／26.9 偏差 ≤1.6%。
- S4.3（粪污还田 75%）使 NPR −22.15%、CFR −76.9%、损失 −77.0%，与论文 Fig. 4A 完全对齐。
- 300 组交叉敏感性回归 R²=**0.960**；`Reduce×Replace` 系数 **−4.60**（p=4.3e-48），呈显著**拮抗**；`Reduce×Recycle` 不显著（p=0.119）。
