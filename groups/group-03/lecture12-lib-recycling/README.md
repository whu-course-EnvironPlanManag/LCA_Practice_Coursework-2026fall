# 第十二讲 退役动力锂离子电池锂资源回收环境规划与管理综合实训（方向 C）

## 选题方向
**方向 C：全生命周期路径尺度——基于退役电池健康状态（SOH）分级的"梯次利用—再生提锂"协同优化与政策激励规划**

## 目录结构
```
lecture12-lib-recycling/
├── README.md
├── code_implementation/
│   ├── 00_config.py              # 全局参数/路径
│   ├── 01_dmfa_model.py          # 模块1a：dMFA 时序 + 守恒
│   ├── 02_process_mfa.py         # 模块1b：工序 MFA + 元素守恒
│   ├── 03_policy_engine.py       # 模块2：政策合规 + 激励核算
│   ├── 04_echelon_tea.py         # 模块3a：梯次 TEA + 回收 TEA + 价格反转
│   ├── 05_lca.py                 # 模块3b：LCA GWP/水耗
│   ├── 06_pareto_sensitivity.py  # 模块3c：帕累托寻优 + 敏感性
│   ├── 07_make_figures.py        # 模块4：8 张图（含 fig5b）
│   └── tests/test_policy_engine.py
├── data_cohort/                  # 输入数据
├── results_output/               # 计算结果
├── figures_output/               # 图表（≥300 DPI）
└── report/Environmental_Planning_Report.md
```

## 运行顺序
```bash
cd code_implementation
python 00_config.py
python 01_dmfa_model.py
python 02_process_mfa.py
python tests/test_policy_engine.py
python 04_echelon_tea.py
python 05_lca.py
python 06_pareto_sensitivity.py
python 07_make_figures.py
```

## 功能单位
1 kWh 电池全寿命周期交付电量

## 核心结论
1. 2026–2040 年区域退役电池量与锂流量持续增长
2. SOH 三级分流决定梯次与再生比例
3. 碳酸锂价格波动导致湿法/火法与直接再生经济性排序反转
4. 直接再生 + 绿电方案是帕累托拐点方案
5. EPR 补贴 + CCER 碳信用可实现 LFP 回收商业闭环
