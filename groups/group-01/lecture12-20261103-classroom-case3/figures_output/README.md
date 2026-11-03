# 当前图片与数据状态

本目录已有以下3张基于《湖北统计年鉴2025》的真实背景图，PNG为300 DPI，并提供同名PDF和SVG：

| 图片 | 内容与口径 |
| :--- | :--- |
| [fig0a_yearbook_private_cars.png](fig0a_yearbook_private_cars.png) | 湖北私人汽车拥有量；含各类燃料汽车，不是新能源车或电池装机量 |
| [fig0b_yearbook_electricity.png](fig0b_yearbook_electricity.png) | 2019—2023年电力生产结构与消费量，不直接代表绿电比例或LCA电网因子 |
| [fig0c_yearbook_city_electricity.png](fig0c_yearbook_city_electricity.png) | 2024年原表12个主要城市全年及工业用电量，不代表工厂可用容量 |

每张图的`*_source.csv`保留统计原值、单位、原始表格和单元格；[yearbook_figures_manifest.json](yearbook_figures_manifest.json)记录统计选择及输入哈希，[yearbook_figures_qa.json](yearbook_figures_qa.json)记录图形检查。

在本讲目录重绘：

```powershell
python code_implementation/run_analysis.py --plot-yearbook
```

退役预测、LCA-TEA、帕累托与选址图尚未生成。所需真实参数尚缺，见[data_readiness.json](data_readiness.json)和[补数说明](../data_cohort/README_data_sources.md)。`ready: false`指完整模型输入未就绪，不影响这些年鉴背景图。此前的19张合成测试图仍在仓库外，不作为湖北正式结果。
