# 单元过程 LCI 与原生 LCE 证据对照（2026-11-03）

本文件只汇总可用于核对量级的公开证据，不替换 `lci.csv` 与 `primary_lce_baselines.csv` 的输入值。原因是这些来源的功能单位、边界与用能方式不同，直接替换会改变 4000 组情景结果与输入哈希。

## 一、原生 LCE

### 1. 模拟 LCA（盐湖与锂辉石）

- 文献：Mas-Fons A, Horta Arduin R, Loubet P, et al. Carbon and water footprint of battery-grade lithium from brine and spodumene: A simulation-based LCA. *Journal of Cleaner Production*, 2024, 142108.
- DOI：<https://doi.org/10.1016/j.jclepro.2024.142108>
- 摘要页：<https://scispace.com/papers/carbon-and-water-footprint-of-battery-grade-lithium-from-22h2dc2w6n>
- 方法：HSC Chemistry 流程模拟 + LCA；盐湖取 Salar de Atacama，锂辉石取 Greenbushes；考虑矿石品位下降。

| 路线 | 气候变化（kgCO₂e/kg LCE） | 水耗（m³/kg LCE） | 折合每吨 LCE |
| --- | --- | --- | --- |
| 盐湖卤水 | 5.0—25.0 | 0.2—7.7 | GWP 5.0—25.0 t；水 200—7 700 m³ |
| 锂辉石 | 17.1—22.3 | 0.2—0.5 | GWP 17.1—22.3 t；水 200—500 m³ |

原文结论：品位下降可使盐湖碳足迹增至 5 倍、锂辉石增至 1.3 倍；能源脱碳是主要改善路径。

### 2. 硬岩精炼的独立量级

- *Science*（2026）“Closing the loop on lithium refining”指出硬岩精炼每吨碳酸锂约产生 **20 t CO₂e**，并伴随大量化学废液与铝硅酸盐残渣。
- 链接：<https://www.science.org/doi/10.1126/science.aei1181>
- 该值与 Mas-Fons 的锂辉石 17.1—22.3 t 区间一致，可交叉印证。

### 3. 与模型现用值的对照

| 路线 | 模型 GWP（t CO₂e/t LCE） | 证据区间 | 模型水耗（m³/t） | 证据区间 | 判断 |
| --- | --- | --- | --- | --- | --- |
| 盐湖 | 13.3 | 5.0—25.0 | 200 | 200—7 700 | 碳值在区间中部；水耗取绝对下限 |
| 锂辉石 | 13.9 | 17.1—22.3 | 60 | 200—500 | 碳值低于下限约 19%；水耗仅为下限的 30% |

含义：

1. 按新证据，模型对**锂辉石**基准的碳与水负荷偏低，再生路线相对锂辉石的减排与节水优势被低估，属保守结果。
2. 盐湖基准的结论取决于品位：低品位 5.0 kgCO₂e/kg 时，再生 B 的 6.87 t CO₂e/t LCE 反而更高，**不存在减排**；高品位 25.0 时才显著减排。因此不能笼统宣称"再生一定减排"。
3. 成本参考 4.0/6.67 万元/t 未找到可替代的新证据，仍沿用原来源，不能与水碳区间混为一谈。
4. 本组未改 `primary_lce_baselines.csv`，因此正文的 MAC 与帕累托结果仍基于旧基准；若采用上述区间，MAC、前沿与排序都会变化，须整体重跑并更新图与全部数值。

## 二、单元过程 LCI（湿法）

### 1. 湖北本厂实测：骆驼襄阳 5 万 t/年节能审查

- 文件：鄂发改审批服务〔2023〕344 号，2023-12-13，湖北省发改委。
- 存档：[hubei_drc_2023_camel_50kt_energy_review.md](hubei_drc_2023_camel_50kt_energy_review.md)
- 原文：<http://fgw.hubei.gov.cn/fbjd/xxgkml/xkfw/xzxkjg/xmspqk/202401/t20240103_5027618.shtml>
- 工艺：放电拆解—破碎—浸出—萃取—结晶，湿法全链；LFP 与三元混合来料。

| 指标 | 单位废电池 | 说明 |
| --- | --- | --- |
| 电力 | 810.17 kWh/t | 与模型 hydro 900/1 100 kWh/t 同量级 |
| 天然气 | 160.84 m³/t | 热解、焚烧与锅炉用能 |
| 氮气 | 23.04 m³/t | 保护气 |
| 新水 | 2.08 m³/t | 厂区直接取水 |
| 综合能耗（等价值） | 439.58 kgce/t | 当量值 294.88 kgce/t |

按天然气 2.16 kgCO₂/m³ 估算，160.84 m³/t 约对应 **347 kgCO₂/t**。模型 `process_heat` 的 LFP 80、NCM 100 kgCO₂/t 只相当于约 37—46 m³ 天然气，**热量排放可能低估约 3.5—4.3 倍**。B 的 6 868 kgCO₂e/t LCE 若按本厂热量强度对齐，量级约增加 250 kgCO₂e/t LCE（约 +3.6%），具体值取决于热量与电力的划分，不能直接相加。

同时，本厂实测综合能耗 439.58 kgce/t 远低于模型政策筛选用的 1 900 kgce/t LCE 阈值；两者分母不同（每吨电池 vs 每吨 LCE），不能相互替代，只能说明 1 900 是阈值情景而非本厂实测。

### 2. 国际湿法清单：每 kWh 电池的物耗与电耗

- 文献：Maritz R F, Akdogan G, Dorfling C. Life cycle assessment of hydrometallurgical lithium-ion battery recycling processes – evaluating geographical location sensitivity. SAIMM Hydrometallurgy 2024, pp. 211—216.
- 原文 PDF：<https://www.saimm.co.za/Conferences/files/Hydrometallurgy-2024/17_700-Maritz.pdf>
- 功能单位：1 kWh 混合退役电池（NMC111 43%、LCO 21%、LFP 36%，进料合计 7.29 kg/kWh）。
- 三种浸出体系：HCl、H₂SO₄、柠檬酸；两种回收策略：混合 NMC 沉淀、沉淀+溶剂萃取。

混合 NMC 沉淀路线（每 kWh）：

| 项目 | HCl 体系 | H₂SO₄ 体系 | 柠檬酸体系 |
| --- | --- | --- | --- |
| 浸出剂 | HCl 55.4 kg | H₂SO₄ 37.3 kg | 柠檬酸 72.9 kg |
| NaOH | 60.5 kg | 30.4 kg | 44.9 kg |
| H₂O₂ | — | 21.9 kg | 22.0 kg |
| Na₂CO₃ | 3.1 kg | 3.0 kg | — |
| 电力 | 190.2 kWh | 131.0 kWh | 185.3 kWh |
| 工艺水 | 184.7 kg | 270.9 kg | 391.5 kg |

按 1 t ≈ 137 kWh 折算（由原文 7.29 kg/kWh 反推），H₂SO₄ 体系每吨电池约需 H₂SO₄ 5.1 t、NaOH 4.2 t、H₂O₂ 3.0 t、电力 17 970 kWh、工艺水 37 m³。该电耗采用电加热（power-to-heat）假设，与湖北本厂的天然气锅炉+余热路线不同，**不能把 17 970 kWh/t 当作湖北基准**；但它说明试剂量级远高于模型中"试剂 900—1 300 元/t"的聚合值，后者缺单耗与品种。

### 3. 沉淀工序电力交叉核对

- ACS *Environmental Science & Technology* 2025 补充材料给出沉淀工序电力 6.956 kWh、并按 242.29 kWh/t Li 计算。
- 链接：<https://pubs.acs.org/doi/suppl/10.1021/acs.est.4c13838/suppl_file/es4c13838_si_001.pdf>
- 该值只覆盖沉淀段，不能与全链电耗直接比较；用于说明单元过程拆分后量级仍以 kWh/t 为主。

## 三、结论与使用规则

1. **电力**：湖北本厂 810 kWh/t 与模型 900—1 100 kWh/t 一致，保留模型值有本地证据；不采用 Maritz 的 17 970 kWh/t（电加热假设，边界不同）。
2. **热量**：模型 `process_heat` 的 80—100 kgCO₂/t 低于本厂天然气对应的约 347 kgCO₂/t，B 的 GWP 属低端值，报告须明确标注。
3. **试剂**：Maritz 给出每 kWh 的品种与单耗，但未给出湖北到厂价格；模型仍只有聚合费用，不能拆分品种碳足迹。
4. **原生 LCE**：锂辉石 13.9 t CO₂e/t 低于 17.1—22.3 的证据区间，60 m³/t 低于 200—500 m³/t；盐湖 13.3 在 5.0—25.0 内，但低品位时无减排。MAC 与帕累托结果须随基准修订重跑，本文不手工推算。
5. 以上证据不改变 `data_cohort/results/` 的既有结果与哈希；报告只把新证据作为校核区间与结论边界。
