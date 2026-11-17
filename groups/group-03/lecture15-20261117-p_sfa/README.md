# 第十五讲实训：全球人为磷循环 SFA 复现（lecture15-20261117）

复现文献：Liu et al. (2026) *Future strategies for phosphorus sustainability amid worsening global cycle imbalances*, PNAS 123(13): e2512673123。

## 运行方式

```bash
cd groups/group-03/lecture15-20261117-p_sfa
python3 main.py   # 一键复现任务1/2/3与基准对照
```

依赖：`pandas numpy plotly statsmodels scikit-learn openpyxl`

## 数据说明

原始数据（`source_data/`，含 FAOSTAT 补充数据集与论文附录）体积较大，**不随仓库分发**。运行前任选其一：

1. 设置环境变量指向数据目录：
   ```bash
   export P_SFA_DATA_DIR=/path/to/环境规划与管理-第十五讲20261117/source_data
   ```
2. 或在项目目录内创建名为 `source_data` 的软链接指向数据目录。

数据目录需包含：`Supplementary_dataset_PNAS_First_Revision/`、`Origin data/`、`Supplementary Data_PNAS Second Revision/`。

## 产物

- `output/sankey_2022.html` — 2022 年全系统磷流交互式桑基图（19 节点）
- `output/scenario_levers.html` — 2050 情景杠杆对比图
- `output/*.csv` — ACS 流向、历史序列、全系统流清单、情景对比、回归统计、基准对照
- `复现报告.docx / 复现报告.md` — 复现报告
- 守恒自检：全系统相对误差 0.00（< 10⁻⁴）；核心指标与文献偏差均 < 0.2%
