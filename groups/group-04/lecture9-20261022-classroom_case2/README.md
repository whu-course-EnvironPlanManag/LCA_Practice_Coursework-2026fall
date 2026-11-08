# 案例二：CO2 捕集耦合电解水绿氢制甲醇（Power-to-Methanol / CCU）系统（MFA-LCA-TEA 进阶训练）

## 1. 案例定位与教学目标

* **教学定位**：作为《环境规划与管理》第九讲的**进阶实战案例**，本案例呈现工业界前沿的**化工反应-分离内循环反馈（Recycle Loop）**系统，直面“双碳”工业园区规划中最核心的**“环境效益与经济成本权衡（Trade-off）”**难题。
* **教学目标**：
  1. 掌握含循环回路（Recycle Loop）的化学反应分离系统物质流分析（MFA）推演方法，能够准确解耦**单程转化率（Single-pass, 25%）**与**系统总转化率（Overall Conversion, 96%）**；
  2. 深刻理解生命周期评价（LCA）中的**“清洁电力敏感度”**与**“绿电悖论”**（揭示为什么在常规煤电工业电网下，电解水绿氢制甲醇的碳排放比传统煤化工高出近一倍）；
  3. 掌握技术经济分析（TEA）中**重资产高能耗系统的平准化成本（LCOM）**建模与“绿色溢价（Green Premium）”测算；
  4. 综合运用 MFA-LCA-TEA 输出，推导**边际减排成本（MAC）**，探讨碳市场交易价格（ETS）与工业园区空间布局规划（如沙戈荒新能源基地定向消纳）的科学决策。

---

## 2. 目录结构说明

```text
CASE2/
├── README.md                          # 本说明文件（含环境配置与核心指引）
├── case_files/                        # 案例详细讲义与教学文档
│   ├── case2_documentation.md         # 案例二完整讲义（含导览速查、反应平衡/双电网情景/MAC曲线/PR作业指南）
│   └── data_cohort/                   # 核心工程数据集
│       ├── mfa_reaction_recycle_balance.csv # 反应器进出口、循环流与产物物料守恒表
│       ├── lca_grid_scenarios_lci.csv       # 100% 绿电 vs 区域网电情景清单与碳足迹对比
│       └── tea_lcom_sensitivity_data.csv    # 电价对平准化甲醇成本（LCOM）的敏感度曲线数据
└── code_implementation/               # （预留）学生 Python 仿真脚本与流程可视化图表存储目录
```

---

## 3. 核心计算基准速查

* **工厂设计规模**：年产 100,000 t（10 万吨）聚合级绿色精甲醇（年运行 8,000 h，配套 130 MW PEM 电解槽）。
* **功能单位**：生产 1 t（1000 kg）绿色精甲醇（门到门 / Cradle-to-Gate）。
* **MFA 关键指标**：反应器单程转化率 25.0%，循环比 3.8:1，分离气分流比为 99.0% 循环 / 1.0% 驰放，全系统总体碳转化利用率高达 96.0%（全流程碳损耗 4.0%）。吨产品单耗：新鲜 CO₂ 1.423 t，绿氢 H₂ 0.198 t，综合电耗 10,826 kWh。
* **LCA 关键指标**：
  * **100% 绿电情景**：净碳足迹为 **-1,044.1 kg CO₂e/t**（实现显著净负碳捕集，较煤制甲醇减排 140.2%）；
  * **区域电网电情景**：净碳足迹高达 **+4,531.3 kg CO₂e/t**（比煤制甲醇基准高出 74.3%！）。
* **TEA 关键指标**：
  * 总投资 CAPEX：8.20 亿元；
  * 0.35 元/度电价下 LCOM = 5,027.5 元/t（绿色溢价 +2,527.5 元/t，MAC ≈ 693.6 元/吨 CO₂e）；
  * 0.15 元/度电价下 LCOM = 2,862.3 元/t（绿色溢价降至 +362.3 元/t，MAC ≈ 99.4 元/吨 CO₂e，依托国家碳市场可实现收支自平衡）。

---

## 4. 推荐本地 Python 实验环境与第三方依赖包（针对复杂循环流求解与流程图绘制）

为了便于不同编程基础的同学顺利完成**复杂循环流代数联立求解**与**高质量工艺流程可视化**，推荐使用 Conda 搭建独立的 Python 实验环境。

### 4.1 环境快速初始化

```bash
# 1. 创建专用虚拟环境（推荐 Python 3.10 或 3.11）
conda create -n mfa_lca_tea python=3.10 -y

# 2. 激活虚拟环境
conda activate mfa_lca_tea

# 3. 升级 pip
python -m pip install --upgrade pip
```

### 4.2 核心科学计算与循环流求解依赖包

```bash
# 安装数据处理、数值计算与非线性方程组求解库
pip install numpy scipy pandas matplotlib seaborn openpyxl
```

* **`scipy`（特别推荐模块：`scipy.optimize.fsolve`）**：
  * **用途**：用于联立求解反应器单程转化（25%）、冷凝气液分离与未反应气循环回路（Recycle Loop）的非线性质量守恒代数方程组；
  * **示例**：
    ```python
    import numpy as np
    from scipy.optimize import fsolve

    def recycle_balance(vars):
        F_recycle, F_purge = vars
        # 根据新鲜进料、单程转化率及分流比建立守恒方程
        eq1 = F_recycle - 0.99 * (F_recycle + F_purge)
        eq2 = ... # 补充质量守恒方程
        return [eq1, eq2]

    sol = fsolve(recycle_balance, [4000.0, 40.0])
    ```

### 4.3 工艺流程图与物质流可视化依赖包（自主选型）

本案例要求自主绘制**含未反应气循环回路（Recycle Loop）的高清工艺流程图**，推荐以下三款工具（任选其一或结合使用）：

1. **`schemdraw`（推荐用于轻量级工程流程方框图，纯 Python 零外部 C 依赖）**：

   ```bash
   pip install schemdraw
   ```

   * **优势**：纯 Python 实现，基于 Matplotlib 渲染，支持方框、流向箭头、循环分支回路文本标注，使用简单优雅。
2. **`plotly`（推荐用于物质流分析 MFA 桑基图）**：

   ```bash
   pip install plotly kaleido
   ```

   * **优势**：直接依据 `mfa_reaction_recycle_balance.csv` 的质量通量绘制流宽与质量严格成正比的交互式或高清静态桑基图（Sankey）。
3. **`graphviz`（推荐用于复杂工业方框工艺流程图 / BFD）**：

   ```bash
   # Python 接口库
   pip install graphviz
   ```

   * **⚠️ 注意事项**：`graphviz` Python 包仅为接口封装，操作系统底层必须预装 Graphviz 的 `dot` 可执行程序：
     * **macOS**：`brew install graphviz`
     * **Windows**：通过管理员终端运行 `winget install Graphviz.Graphviz` 或从官网下载安装包并勾选“Add to PATH”；
     * **Linux / Ubuntu**：`sudo apt-get install -y graphviz`。

---

## 5. 课程大仓协同与 PR 提交说明

* 详细随堂对抗演练研讨任务、大作业要求及 Git 分支提交流程见：[case_files/case2_documentation.md](case_files/case2_documentation.md)
* 遇到网络同步、分支命名被拒或 PR 模板问题，请查阅大仓救急指南：[starter_materials/troubleshooting.md](../../troubleshooting.md)

## 6. Python 实施与计算成果

在仓库根目录运行：

```bash
python groups/group-04/lecture9-20261022-classroom_case2/code_implementation/case2_analysis.py
```

脚本读取本目录 `case_files/data_cohort/` 的三份 CSV，执行循环回路求解、LCA/TEA 电价敏感性分析和流程图绘制。结果与图表保存在 `code_implementation/`：

* `case2_analysis_results.txt`：循环比、总转化率、C/H/O 元素平衡差、LCA/TEA 及碳价阈值；
* `case2_economic_sensitivity.png`：LCOM、绿色溢价及 MAC 对电价的响应曲线；
* `case2_process_flow.png`：展示 PEM 电解、甲醇合成、分离和未反应气循环的 300 dpi 流程图。

> **数据核验提示**：脚本按数据表和给定的 25% 单程转化率、99% 回流比例计算，并保留实际元素平衡差。当前 CSV 与讲义中的“循环比 3.8、总碳利用率 96.0%”不完全一致，C/H/O 外部元素平衡也未达到 0.01% 容差。脚本会如实标记差异；在源数据核实修订前，不应将这些差值解释为模型已通过守恒验证。

* 运行命令、结果汇总、已修正的描述字段及未解决的数据差距见：[code_implementation/case2_implementation_report.md](./code_implementation/case2_implementation_report.md)。
