# 案例一：城市废旧 PET 塑料机械物理再生系统（MFA-LCA-TEA 联合训练）

## 1. 案例定位与教学目标

* **教学定位**：作为《环境规划与管理》第九讲的**入门基础案例**，本案例呈现典型的**单向线性物质流动**系统，无复杂的化学反应与内循环回路。
* **教学目标**：
  1. 掌握如何基于**质量守恒定律**构建工业级固废分选再生的物质流分析（MFA）模型；
  2. 掌握如何将 MFA 计算得到的**产率与消耗系数**，转化为生命周期评价（LCA）的**基准基础**；
  3. 掌握如何将 MFA 的物料、水、电、蒸汽消耗转化为技术经济分析（TEA）的**变动运营成本（OPEX）**，并结合设备选型折算**资本投资（CAPEX）**与**平准化生产成本（LCOP）**；
  4. 整体感受“前端杂质率变化 $\rightarrow$ 分选收率变化 $\rightarrow$ LCA 碳足迹与 TEA 生产成本双重恶化”的参数联动完整链条。

---

## 2. 目录结构说明

```text
lecture9-20261022-classroom_case1/
├── README.md                      # 本说明文件
├── case_files/                    # 案例详细讲义与教学文档
│   ├── case1_documentation.md     # 案例一完整讲义（含导览速查、MFA/LCA/TEA模型、PR提交指南）
│   └── data_cohort/               # 基础数据集（供教学推演与后续代码使用）
│       ├── mfa_mass_balance.csv   # MFA 物质输入输出及工段平衡数据
│       ├── lci_emission_factors.csv # LCA 生命周期清单与背景碳排放因子
│       └── tea_cost_parameters.csv # TEA 投资、公用工程单价与财务指标
└── code_implementation/           # （预留）教师后续随堂与课后 Python/Excel 仿真代码发布区
```

> 💡 **全班 Git 协作与排错救急手册**：遇到网络克隆慢、分支隔离与创建、拉取最新 main 防覆盖、代码误改 stash/reset 救急或 PR 提交问题，请查阅大仓公共指南：[starter_materials/troubleshooting.md](../troubleshooting.md)。

---

## 3. 核心计算基准速查（Baseline Benchmark）

> ⚠️ **【注】**：以下为基准情景（常规工业电网）的教学示范基准数据；随堂与课后作业请计算“100% 绿电驱动”的全新优化情景（参见讲义第六部分）。

* **处理规模**：年处理 20,000 t 废 PET 瓶砖（年产 16,000 t 瓶级 rPET 颗粒）。
* **功能单位**：生产 1 t（1000 kg）瓶级 recycled PET (rPET) 颗粒。
* **MFA 关键指标**：综合产品收率 $Y = 80.0\%$，单吨产品需原料 1.25 t。
* **LCA 关键指标**：净全生命周期碳足迹 636.0 kg CO₂e/t（较原生 PET 减碳 71.7%）。
* **TEA 关键指标**：总投资 2,800 万元，平准化生产成本 $\text{LCOP} = 6,153.4\text{ 元/t}$，投资回收期 2.6 年。

---

## 4. 随堂 Python 环境准备与推荐第三方包 (Environment Setup)

为照顾不同编程基础的同学，本次实践任务推荐以下环境依赖（根据作业需要选择即可）：

### 4.1 基础计算与数据处理（全员必装，零系统依赖）
适用于完成 MFA 物质平衡、LCA 碳足迹计算与 TEA 经济平准化成本核算：
```bash
pip install pandas numpy matplotlib
```

### 4.2 工艺流程图绘制推荐选型（按个人基础三选一）：
* **选项 A（零基础/新手最推荐 · 纯 Python 零系统底层依赖）**：
  使用 `schemdraw` 绘制方框工艺流程图（BFD），绝不会因缺少系统底层软件而报错：
  ```bash
  pip install schemdraw
  ```
* **选项 B（进阶首选 · 交互式物质流桑基图）**：
  使用 `plotly` 绘制与物质质量流量成比例的高清 MFA 桑基图：
  ```bash
  pip install plotly kaleido
  ```
* **选项 C（工业标准有向图 · 需特别注意避坑）**：
  使用 `graphviz` 绘制有向图。⚠️ **特别提醒**：`pip install graphviz` 仅安装了 Python 接口，电脑本地还必须预先安装系统级 Graphviz 软件（如 Windows 的 `graphviz-install.exe` 或 Mac 的 `brew install graphviz`）并配置系统 PATH，否则代码运行时会报错 `ExecutableNotFound: failed to execute dot`。新手建议优先选用选项 A 或 B。
