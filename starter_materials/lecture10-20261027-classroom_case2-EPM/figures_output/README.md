# 图表输出与交付目录（Figures Output）

> 本目录为学生执行仿真绘图脚本后的默认图表存储目录。初始状态下仅保留本说明文件，运行代码后将自动生成以下两张出版级 300 DPI 高清图表：

1. **`fig1_mfa_process_flow.png`**：
   * **生成来源**：运行 `code_implementation/task4_process_sankey_flow.py`；
   * **内容要素**：工业园区 10 万吨/年绿色甲醇工程全流程工艺拓扑图，按锚点 B（绿电 100%、驰放比约 2.16%）展示碳捕集、PEM 制氢、催化合成、双塔精馏各工段的物料通量与电耗负荷，以及未反应气内循环流（约 $45.87\text{ 万吨/年}$）和精馏副产水回用流（$5.75\text{ 万吨/年}$）；
   * **报告嵌入位置**：`report/Environmental_Planning_Report.md` 第 2.2 节。

2. **`fig2_pareto_decision_frontier.png`**：
   * **生成来源**：运行 `code_implementation/task3_pareto_frontier_decision.py`；
   * **内容要素**：政策规制约束下的帕累托前沿双子图。左图为目标空间散点分布、法规阈值及有效帕累托前沿，标记锚点 A、锚点 B（归一化乌托邦距离拐点）与锚点 C；右图为帕累托解在决策变量空间（绿电比例与驰放比）的轨迹；
   * **报告嵌入位置**：`report/Environmental_Planning_Report.md` 第 5.3 节。

---
*注：请在最终提交前确保两张图片均已成功生成，分辨率不低于 300 DPI。*
