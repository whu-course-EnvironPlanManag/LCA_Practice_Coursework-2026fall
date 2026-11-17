# 磷循环作业运行说明

进入本目录运行（数据路径由脚本位置解析，脚本也支持从其他目录调用）：

```powershell
python -m pip install -r requirements.txt
python run_analysis.py
python self_check.py
```

输入默认读取上一级 `source_data`；可用 `--source-data PATH` 指定目录。无需网络即可分析，HTML 已内嵌绘图库。

第一轮补充资料目录无文件，无法严格复现作者所有部门和分国情景。本实现提供历史表自动清洗、SI 产品系数提取、2022 实物生产与贸易换算、17 种核心作物 ACS、五系统守恒、课堂 3R 和交互回归；完整边界和假设见 [报告](report.md)。人口与化肥仅有至 2021 年的历史数据，默认外推结果不冒充正式预测。

取得正式人口预测后，准备包含 `Year,Population` 两列的 CSV（人口单位为人，必须含 2022、2050 年），再运行：

```powershell
python run_analysis.py --population-projection population_projection.csv
```

主要交付：

- `report.md`：自动生成的中文报告，含计算数值、限制及量规核对。
- `outputs/sankey_2022.html`：2022 年五系统桑基图。
- `outputs/scenarios_2050.html`：2050 年情景对比。
- `outputs/history_1961_2022.html`：历史分类曲线。
- `outputs/benchmark_comparison.csv`：文献标称值与实际计算的完整清单，未复算值留空。
- `outputs/policy_regression.csv`：标准化系数、HC3 p 值和交互类型。
- `outputs/audit.json`、`input_sha256.csv`、`self_check.json`：来源及自检证据。

`.deps` 为本机运行时额外依赖缓存，已加入忽略规则，不提交版本库。`audit` 下 PDF 全文仅作阅读中间文件，不是作业计算结果。报告数值均由代码生成；需要修改模型时，请修改代码再运行，避免报告与结果失配。
