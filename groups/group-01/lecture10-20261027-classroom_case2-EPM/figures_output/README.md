# 图表输出与交付目录（Figures Output）

> 本目录为学生执行仿真绘图脚本后的默认图表存储目录。初始状态下仅保留本说明文件，运行代码后将自动生成以下两张出版级 300 DPI 高清图表：

1. **`fig1_mfa_process_flow.png`**：
   * **生成来源**：运行 `code_implementation/task4_process_sankey_flow.py`；
   * **内容要素**：工业园区 10 万吨/年绿色甲醇工程全流程工艺拓扑图，展示碳捕集、PEM 制氢、催化合成、双塔精馏各工段的物料通量、电耗负荷，以及未反应气内循环回路（$51.78\text{ 万吨/年}$）和精馏副产生成水回用流（$5.72\text{ 万吨/年}$）。图中数值均为帕累托拐点（锚点 B：$f_{\text{green}}=100\%$、$r_{\text{purge}}=2.16\%$）工况；
   * **报告嵌入位置**：`report/Environmental_Planning_Report.md` 第 2.2 节。

2. **`fig2_pareto_decision_frontier.png`**：
   * **生成来源**：运行 `code_implementation/task3_pareto_frontier_decision.py`；
   * **内容要素**：政策规制约束下的帕累托前沿双子图。左图为目标空间散点分布、法规一票否决区（橙色叉号，边界 $\text{GWP}_{\text{net}}=+2{,}600\ \text{kg CO}_2\text{e/t}$）、国内合规解（紫色圆点）、欧盟 RFNBO 认证解（绿色圆点）及有效帕累托前沿曲线（粉色实线），标记锚点 A、锚点 B（Knee Point 拐点）与锚点 C；右图为帕累托解在决策变量空间（绿电比例 $0\text{–}105\%$ 定轴 vs. 驰放比）的分布；
   * **报告嵌入位置**：`report/Environmental_Planning_Report.md` 第 5.3 节。

---
*注：请在最终提交前确保两张图片均已成功生成，分辨率不低于 300 DPI。*
