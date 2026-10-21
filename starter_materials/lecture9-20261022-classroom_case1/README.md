# 案例一：城市废旧 PET 塑料机械物理再生系统（MFA-LCA-TEA 联合训练）

## 1. 案例定位与教学目标

* **教学定位**：作为《环境规划与管理》第九讲的**入门基石案例**，本案例呈现典型的**单向线性物质流动**系统，无复杂的化学反应与内循环回路，结构清晰直观。
* **教学目标**：
  1. 掌握如何基于**质量守恒定律**构建工业级固废分选再生的物质流分析（MFA）模型；
  2. 掌握如何将 MFA 计算得到的**产率与消耗系数**，直接转化为生命周期评价（LCA）的**基准流（Reference Flow）**；
  3. 掌握如何将 MFA 的物料、水、电、蒸汽消耗转化为技术经济分析（TEA）的**变动运营成本（OPEX）**，并结合设备选型折算**资本投资（CAPEX）**与**平准化生产成本（LCOP）**；
  4. 体验“前端杂质率变化 $\rightarrow$ 分选收率变化 $\rightarrow$ LCA 碳足迹与 TEA 生产成本双重恶化”的参数联动链条。

---

## 2. 目录结构说明

```text
lecture9-20261022-classroom_case1/
├── README.md                      # 本说明文件
├── troubleshooting.md             # 学生 Git 协作与避坑急救全景指南
├── case_files/                    # 案例详细讲义与教学文档
│   ├── case1_documentation.md     # 案例一完整讲义（含导览速查、MFA/LCA/TEA模型、PR提交指南）
│   └── data_cohort/               # 基础数据集（供教学推演与后续代码使用）
│       ├── mfa_mass_balance.csv   # MFA 物质输入输出及工段平衡数据
│       ├── lci_emission_factors.csv # LCA 生命周期清单与背景碳排放因子
│       └── tea_cost_parameters.csv # TEA 投资、公用工程单价与财务指标
└── code_implementation/           # （预留）教师后续随堂与课后 Python/Excel 仿真代码发布区
```

---

## 3. 核心计算基准速查

* **处理规模**：年处理 $20,000\text{ t}$ 废 PET 瓶砖（年产 $16,000\text{ t}$ 瓶级 rPET 颗粒）。
* **功能单位**：生产 $1\text{ t}$（$1000\text{ kg}$）瓶级 renewable PET (rPET) 颗粒。
* **MFA 关键指标**：综合产品收率 $Y = 80.0\%$，单吨产品需原料 $1.25\text{ t}$。
* **LCA 关键指标**：净全生命周期碳足迹 $636.0\text{ kg CO}_2\text{e/t}$（较原生 PET 减碳 $71.7\%$）。
* **TEA 关键指标**：总投资 $2,800\text{ 万元}$，平准化生产成本 $\text{LCOP} = 6,153.4\text{ 元/t}$，投资回收期 $2.6\text{ 年}$。
