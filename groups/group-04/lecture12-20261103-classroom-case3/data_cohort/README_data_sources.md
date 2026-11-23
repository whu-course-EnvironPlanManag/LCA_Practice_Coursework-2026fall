# 数据底座来源声明（成员 A：数据与物质流）

> 场景：浙江衢州华友循环资源再生产业园，设计年处理退役动力电池 20,000 t/a（锚定衢州华友资源再生科技有限公司设计利用能力 2 万吨/年 [7]）。
> 约定：每张表的 `source` 列标注参数出处，编号对应本文件末尾参考文献列表。

## 文件索引

| 文件 | 内容 | 主要用途 |
|---|---|---|
| `feedstock_composition.csv` | 进厂退役电池包/电芯/材料三级质量组成与元素含量 | MFA 输入 |
| `process_parameters.csv` | 各工序回收率、分配系数、能耗、水耗 | MFA 解算 + 政策判定输入 |
| `policy_thresholds.csv` | 工信部 2024 年本与欧盟 (EU) 2023/1542 量化红线 | 移交 B（政策引擎） |
| `site_baseline.csv` | 衢州园区场景参数（产能、运距、电网因子等） | 报告第 1 章 + C 的 LCA |

## 关键数据溯源说明

1. **园区产能与现状**：衢州华友资源再生科技有限公司设计利用能力 2 万吨/年、2024 年实际利用 0.44 万吨 [7]；华友循环衢州基地 2018 年投产、年处理退役电池 6.47 万吨 [8]，央视报道"年处理废旧电池材料 6.5 万吨、全球首家梯次+再生零碳工厂" [9]。本规划以 2 万吨/年为设计产能、以 0.44→2 万吨产能爬坡为现状诊断依据。
2. **SOH 三级分流**（>85% 直接梯次、80–85% 间接梯次、<80% 再生）取自 Zhang et al. 2025 [3]；分流比例 10%/10%/80% 为规划设定值（待与 C 协商敏感性）。
3. **LFP/NMC 电芯质量组成**：以 EverBatt/GREET 电池材料清单体系 [4][5] 为基准，LFP 电芯正极活性物 28%、NMC811 电芯 35%，经工业拆解数据校核 [4]。
4. **元素含量**：LFP 含 Li 4.40%（按 LiFePO₄ 分子量计算）；NMC811 含 Li 7.16%、Ni 48.6%、Co 9.1%、Mn 2.8%（按 LiNi₀.₈Co₀.₁₅Mn₀.₀₅O₂ 分子量计算）；电解液按 12.5% LiPF₆ 计 [4]。
5. **工序回收率与能耗水耗**：Ni/Co 95%、Li 92%、全流程能耗 44.4 MJ/kg、水耗 21.5 L/kg、碳排放 6.1 kg CO₂e/kg，取自 Machala et al. 2025（Redwood Materials 工业级实测）[4]；原生路径基准 193.9 MJ/kg、77.3 L/kg、14.5 kg CO₂e/kg 同出处。原生锂盐湖/锂辉石碳足迹分布取 Peiseler et al. 2024 [1]。
6. **碳酸锂价格情景** 10,000/22,000/50,000 USD/t 取自 Yao et al. 2025 [2]；历史波动区间 5,496–84,942 USD/t 取自 Ma et al. 2024 [6]。
7. **LFP 湿法亏损 −2.05 $/kg、直接再生 +1.30 $/kg、NMC/NCA +4.01~4.37 $/kg** 取自 Zhang et al. 2025 [3]，是工艺配比设定（LFP 一半走直接再生）的依据。
8. **法规红线**：工信部《新能源汽车废旧动力电池综合利用行业规范条件（2024 年本）》[10]；欧盟 Regulation (EU) 2023/1542 [11]。
9. **浙江电网排放因子**：约 0.55 kg CO₂e/kWh（华东区域电网，生态环境部 2021 年全国电网平均 0.5568 kg CO₂e/kWh [12]），精确值由 C 在 LCA 清单中校核。

## 参考文献

- [1] Peiseler, L. et al. (2024). Carbon footprint distributions of lithium-ion batteries and their materials. *Nature Communications*, 15:10301. 数据：https://doi.org/10.5281/zenodo.13936832
- [2] Yao, A., Benson, S. M., & Chueh, W. C. (2025). Critically assessing sodium-ion technology roadmaps and scenarios for techno-economic competitiveness against lithium-ion batteries. *Nature Energy*, 10, 404–416.
- [3] Zhang, X. et al. (2025). Lithium-ion battery recycling relieves the threat to material scarcity amid China's electric vehicle ambitions. *Nature Communications*, 16:6661. 数据：https://zenodo.org/records/15342229
- [4] Machala, M. L. et al. (2025). Life cycle comparison of industrial-scale lithium-ion battery recycling and mining supply chains. *Nature Communications*, 16:988. 数据：https://osf.io/zvame/
- [5] Wu, H. et al. (2024). Impact of circular economy on the long-term allocation structure of primary and secondary lithium. *Communications Earth & Environment*, 5:503. 数据：https://zenodo.org/records/11160283
- [6] Ma, R. et al. (2024). Pathway decisions for reuse and recycling of retired lithium-ion batteries considering economic and environmental functions. *Nature Communications*, 15:7641. 代码：https://github.com/RuifeiMa/Reuse-and-recycling-pathway-of-retired-batteries
- [7] 衢州市生态环境局. 关于 2025 年衢州市固体废物信息的公告. http://www.qz.gov.cn/col/col1229039395/art/2026/art_9d4f739cfa194a928117eb962770598d.html
- [8] 36 氪 (2022). 动力电池回收企业白名单扩容，千亿市场角逐开始. https://m.36kr.com/p/2022017262644480
- [9] 浙江华友钴业股份有限公司. 央视《新闻直播间》关注报道华友循环. https://www.huayou.com/news/corporate-news/312.html
- [10] 工业和信息化部. 《新能源汽车废旧动力电池综合利用行业规范条件（2024 年本）》（2024 年第 42 号公告，2025-01-01 施行）.
- [11] European Parliament and Council. Regulation (EU) 2023/1542 concerning batteries and waste batteries.
- [12] 生态环境部. 2021 年电力二氧化碳排放因子公告（全国电网平均 0.5568 kg CO₂e/kWh）.
- [13] 衢州市智造新城管委会. 华友绿能年产 1.2 万吨高性能磷酸铁锂再生料项目节能报告公示. http://zzxc.qz.gov.cn/col/col1229278095/art/2026/art_14d02677980a41178c61af6952525d6c.html
