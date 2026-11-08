# 图表输出与交付目录（Figures Output）

> 本目录为学生执行仿真绘图脚本后的默认图表存储目录。任务 4 会根据锚点 B 的当前模型结果生成 Mermaid ELK 源码；若系统已安装 Mermaid CLI（`mmdc`），同时渲染 PNG。

1. **`fig1_mfa_process_flow.png`**：
   * **生成来源**：运行 `code_implementation/task4_process_sankey_flow.py`；PNG 渲染需要安装 Mermaid CLI；
   * **内容要素**：ELK 左至右主流程、PEM 制氢分支、标注质量通量与分项电耗，并区分气体循环和精馏水回用；
   * **Mermaid 源码**：`fig1_mfa_process_flow.mmd`；
   * **报告嵌入位置**：`report/Environmental_Planning_Report.md` 第 2.2 节（内嵌 Mermaid 图）。

2. **`fig2_pareto_decision_frontier.png`**：
   * **生成来源**：运行 `code_implementation/task3_pareto_frontier_decision.py`；
   * **内容要素**：政策规制约束下的帕累托前沿双子图。左图为目标空间散点分布、法规一票否决区（红色虚线）及有效帕累托前沿曲线，标记锚点 A、锚点 B（Knee Point 拐点）与锚点 C；右图为帕累托解在决策变量空间（绿电比例 vs. 驰放比）的轨迹演化；
   * **报告嵌入位置**：`report/Environmental_Planning_Report.md` 第 5.3 节。

---
*注：请在最终提交前确保两张图片均已成功生成，分辨率不低于 300 DPI。*
