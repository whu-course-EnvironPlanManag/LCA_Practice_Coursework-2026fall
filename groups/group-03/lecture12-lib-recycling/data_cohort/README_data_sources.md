# 数据底座来源声明（data_cohort）

## 一、电池化学体系参数 `battery_chemistry.csv`
- 比能量、含锂系数、碳足迹：文献1 Peiseler et al. (2024) Nat. Commun. 15:10301
- NMC811 含锂 0.068 kg/kg、LFP 含锂 0.039 kg/kg（按化学计量比推导）

## 二、退役量预测 `fleet_parameters.csv`
- Weibull 分布 η=8年, β=3.2：文献3 Wu et al. (2024) Commun. Earth Environ. 5:503
- 收集率 55%→86%：文献3 + 文献5

## 三、SOH 梯次参数 `soh_echelon_parameters.csv`
- SOH>85% LSV / 80-85% ESS / 70-80% CBS：文献5 Zhang et al. (2025)
- 容量衰减率 4-6%/年、梯次寿命 3-5 年：文献6 Ma et al. (2024)

## 四、再生工艺参数 `process_parameters.csv`
- 回收率、能耗、水耗、GWP：文献4 Machala et al. (2025) Nat. Commun. 16:988
- LFP 湿法净收益 -14.35 CNY/kg、直接再生 +9.10 CNY/kg：文献5
- NMC 湿法 +28.07、直接再生 +30.59 CNY/kg：文献5

## 五、LCA 因子 `lca_factors.csv`
- 原生卤水锂 GWP 1.5 kgCO2e/kg LCE：文献1
- 原生硬岩锂 GWP 14.5 kgCO2e/kg LCE：文献4
- 电网碳因子 0.581 kgCO2e/kWh：文献6

## 六、TEA 参数 `tea_parameters.csv`
- WACC 8%、厂寿命 15 年：行业均值
- 碳酸锂价格 ¥70k/¥154k/¥350k：文献2 Yao et al. (2025)（$10k/$22k/$50k × 7）
- EPR 补贴 LFP 10.5 CNY/kg：政策
- CCER 碳价 84 CNY/tCO2e：市场

## 七、政策参数 `policy_parameters.csv`
- 工信部 2024 规范（锂≥90%、镍钴锰≥98%、氟固化≥99.5%、能耗<2200kgce/t、废水≥90%）
- 欧盟 2023/1542（锂回收率 50%/80%、再生锂 6%/12%）
