# 第十五讲磷循环实训作业审阅版

本目录供审阅，课程提交版本。先打开 [完整作业.html](完整作业.html)，可查看报告、表格、图件及交互桑基图。纯文本版本为 [报告.md](报告.md)。

## 计算范围

- 1961—2022 年全球、中国大陆、美国、印度的农产品磷产出与贸易序列。
- 2022 年水稻、小麦、玉米的原始产量与含磷率连接换算。
- 2022 年全球五子系统简化预算，含明确标记的文献参数及残差估计。
- 2050 年 BAU、Reduce、Replace、Recycle、3R 五个典型情景。
- 三变量 125 点交互回归；谷物与动物产品的历史回归方法复算。

**本作业是典型案例复算及简化情景分析，不是论文完整八子系统、全部国家和全部情景的精确复现。** 老师允许缩减计算范围；本次没有用这一要求掩盖模型假设。请结合 [方法与数据核查.md](方法与数据核查.md) 审阅。

## 一键运行

```bash
python -m pip install -r requirements.txt
python model.py
python enhancements.py
python build_report.py
```

Python 3.11 或以上。无硬编码绝对路径；模型运行无需网络。清洗后的输入随包提供；原始文件路径、Git blob SHA 与筛选口径见数据说明。用于从下载的原始资料重建输入的脚本为 `build_inputs.py`，默认自动向上查找课程仓库的 `starter_materials/lecture15-20261117-Journal_Article2/source_data/`；原始材料较大，未重复塞入审阅包。

## 成果

- [完整报告](报告.md)：正文与必要结果表、参考文献。
- [方法与数据核查](方法与数据核查.md)：参数来源、边界、缺失值、偏差和材料覆盖范围。
- [模型代码](model.py) 与 [模型假设](data/assumptions.json)。
- [2022 年守恒表](results/mass_balance_2022.csv)、[2050 年情景表](results/scenarios_2050.csv)、[政策回归](results/policy_regression.csv)。
- [交互桑基图](figures/sankey_2022.html)：已内嵌 Plotly，可离线查看。
- 图 1 为历史趋势，图 2 为情景比较，图 3 为联合响应；PNG 均以 300 DPI 导出。

## 已验证及限制

验证包括单位换算、连接唯一性、非负流量、子系统与外边界守恒、共享流量一致性、注入错误后的守恒断言、情景产出不变约束、图表交互。输入印度进口数据 1961、1962 年存在 26 个空单元格，保留缺失，未补零。

守恒通过只说明预算自洽。饲草边界输入、消费加工残余与土壤净积累中含残差估计，不构成独立实测验证。政策回归是确定性模型响应面，其 p 值不能作为现实政策因果证据。论文完整模型的 S4.3、S2.3、S5 和 35 国达标数量仅作阅读基准，未冒充本次重算结果。

## 提交前

请先确认正文和计算口径。确认后再按课程分支规则整理 PR，不在本次审阅阶段上传或提交。

## v2 修订

新增[量规逐项对照](量规逐项对照.md)、[独立基准](results/benchmark_comparison.csv)、[国家PUE上界筛查](results/country_PUE_screening.csv)。主回归改为农田PUE。原始数据重建和清洗输入的模型重跑是不同层次；审阅包可离线完成后者。

新增输入的原始数据抽取脚本为 [prepare_additional_inputs.py](prepare_additional_inputs.py)，默认读取课程仓库的source_data目录。已清洗输入随包提供，常规复跑无需下载原始大文件。


## 从课程仓库原始数据重新生成输入

提交位于个人分支 `dev-group-02-帕娜尔-lecture15`。分支名不会成为文件系统路径；本程序不依赖分支名或个人文件夹名称。将整份作业放在课程仓库内的个人作业目录，保留仓库已有的 `starter_materials/`，即可自动发现原始资料。无需再上传原始论文和大体量数据。

```bash
python build_inputs.py
python prepare_additional_inputs.py
python model.py
python enhancements.py
python build_report.py
```

上例在作业目录运行；也可以从任意工作目录用脚本路径调用，原始数据自动定位依据脚本位置。原始文件名及相对路径由 [source_index.json](data/source_index.json) 与 [production_2022_source.json](data/production_2022_source.json) 映射；编号仅作内部标识，仓库中不需要015.xlsx等短文件名。

如果作业目录在仓库外，为前两个脚本增加 `--source-data "课程仓库路径/starter_materials/lecture15-20261117-Journal_Article2/source_data"`。该参数指向source_data本身，不是仓库根目录。旧下载缓存只有显式指定 `--legacy-sources "缓存目录"` 才会读取，不会自动掩盖缺失的课程文件。`--output-dir "输出目录"` 可用于不覆盖随包输入的独立核验；后续模型默认读取本目录data，不会自动跟随该测试输出目录。

所有必需原始文件均在开始写出前检查；缺失时报告具体路径。附带清洗数据的常规复跑不需要原始资料。原始抽取需要pandas、openpyxl，均已列入依赖。
