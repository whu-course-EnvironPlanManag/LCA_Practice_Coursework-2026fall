# 六篇预编译文献：模型取舍与参数边界

本文件记录针对方向A的阅读与代码对应关系，不将论文全国/全球预测冒充湖北实测数据。全文PDF仍位于本任务`precompiled_references/`。文章中指向补充资料的参数，在尚未取得具体表格前保留待补状态，不从图形趋势猜数。

| 论文 | 读到的方法/数据边界 | 本代码采用与未采用的部分 |
| :--- | :--- | :--- |
| Peiseler等，2024，*Carbon footprint distributions of lithium-ion batteries and their materials*，Nature Communications 15:10301 | GWP100、原料供应曲线与概率分布、材料和电芯生产边界；Methods与Data/Code availability明确部分原始数据库受许可限制；开放记录DOI 10.5281/zenodo.13936832 | 采用“材料/电芯/整包与单位容量必须区分、因子要有出处”的数据合同；不把电芯kg CO2e/kWh直接用作废电池回收kg CO2e/t，不据此构造湖北概率分布 |
| Yao、Benson与Chueh，2025，*Critically assessing sodium-ion technology roadmaps and scenarios for techno-economic competitiveness against lithium-ion batteries*，Nature Energy 10:404–416 | Methods为组件级、矿产价格底线约束的学习曲线；矿产价格与材料强度会改变技术竞争关系，部分底层商业数据非公开 | 采购价、Li价与SOH由有出处报价表精确配对；本次没有足够时间序列校准学习参数，未补造Wright学习率、底价或CNY汇率 |
| Wu等，2024，*Impact of circular economy on the long-term allocation structure of primary and secondary lithium*，Communications Earth & Environment 5:503，DOI 10.1038/s43247-024-01667-2 | PDF第8页式1为存量变化=流入−流出；第9页式3为双参数Weibull密度。EV安装采用存量驱动并考虑电池与整车寿命不同，材料含量指向Supplementary Table 8、寿命指向Supplementary Table 1；开放记录11160283 | 用CDF差分获得年度退役概率，保存尾部与安装年份材料强度；提供电池容量存量反推函数。未在缺少湖北数据时完整复制其全球EV/BESS耦合预测，也不将正文6—8年滞后当作eta/beta |
| Machala等，2025，*Life cycle comparison of industrial-scale lithium-ion battery recycling and mining supply chains*，Nature Communications 16:988，DOI 10.1038/s41467-025-56063-x | 工业规模循环/原生供应链、过程分项、功能单位为NCA或LCO等效材料。正文193.9 MJ、77.3 L、14.5 kg CO2e等以kg NCA-eq为基准；44.4 MJ等亦需对应原文具体路径和边界 | 采用过程清单分项与同功能基准原则；**没有把这些摘要总值写入原生LCE或废电池整包基准**。电力水-碳因子及试剂负荷独立输入；不将美国Redwood电力条件当作湖北条件 |
| Zhang等，2025，*Lithium-ion battery recycling relieves the threat to material scarcity amid China’s electric vehicle ambitions*，Nature Communications 16:6661，DOI 10.1038/s41467-025-61481-y | 全国多情景dMFA、技术演变、电网因子更新与空间回收网络，Methods和Data availability指向补充数据1—6及来源库；SOH分级与末端去向区分 | 实现市州起点、收集—梯次/精炼候选点、道路OD和容量约束MILP。未把全国2060总量按人口比例分到湖北，也未将全国回收率情景当湖北实际值；当前是费用最小网络内的外层条件前沿，不是其完整GCAM/Bass/GIS复现 |
| Ma等，2024，*Pathway decisions for reuse and recycling of retired lithium-ion batteries considering economic and environmental functions*，Nature Communications 15:7641 | 梯次场景、不同初始/结束SOH与再生路径的全寿命比较；Li2CO3在直接修复中可能是补锂投入，在提锂路径中是产品，价格敏感性方向不能混用；开放代码指向RuifeiMa/Reuse-and-recycling-pathway-of-retired-batteries | 配置显式SOH采购报价和梯次滞后；没有把“direct”工艺简单设为高Li盐收入。直接正极修复需同功能正极/服务模型，本版LCE主比较会阻止错误套价；未声称已经建立完整SOH退化与梯次NPV |

## 阶段性方法选择

1. 主线为湖北省EV动力电池，输入为年度分市州/化学体系的安装kWh队列。资料没有覆盖BESS时不自动追加一套虚构储能规模。
2. 支持Li及Ni/Co/Mn元素流，至少Li收支必须闭合。未知的Cu、Al、F等全量物流不通过差额补成某种化学物质；相关工艺政策可使用独立测量指标筛选。
3. 工艺LCI与物流数据的功能单位统一；原生Li供应链比较需要真实的卤水/锂辉石LCE基准和多产品归属依据。取得同功能参数前不输出减排比例。
4. 寿命、比能量和化学组成支持安装年份变化；区域电力因子支持年度输入，但本次外层寻优用明确的代表年，不声称完成2026—2040逐年投资优化。
5. 有效供应与潜在废弃量不同：正规收集、梯次暂存、实际有效回收率都会影响当年再生Li供给。新电池再生含量是下游材料归属指标，不能直接用收集率替代。

## 尚未采用的待核参数

| 项目 | 原因 |
| :--- | :--- |
| 每体系Weibull eta/beta数值 | 核心论文指向补充表；本地正文不能提供可直接核对的完整取值，未猜设 |
| Li/Ni/Co/Mn kg/kWh及整包比能量 | 需明确体系、年份与整包/电芯边界，不能用“某论文平均值”不加说明地填全省 |
| 湖北历史EV安装、未来渗透率 | 年鉴现有汽车总量和工业产量不足以识别，需要组员区域资料 |
| 湖北工厂LCA清单及建设报价 | 文献工业值有地域和功能单位差异，需要适用性判断、来源及换算 |
| 运输道路OD、候选地容量与许可 | 不从散点示意或行政中心位置推断实际工厂网络 |

公开补充数据入口可供资料组继续取数：

- Peiseler：<https://doi.org/10.5281/zenodo.13936832>
- Wu：<https://zenodo.org/records/11160283>
- Machala：<https://osf.io/zvame/>
- Zhang：<https://zenodo.org/records/15342229>
- Ma：<https://github.com/RuifeiMa/Reuse-and-recycling-pathway-of-retired-batteries>

以上入口不意味着已取得全部受许可限制的数据；填表时仍需注明具体文件、表号/页码、单位、区域年份和适用性。
