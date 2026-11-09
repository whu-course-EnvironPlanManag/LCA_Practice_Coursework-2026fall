> 历史提取定位记录。2026-11-04新版模型以README_data_sources.md、plan_parameters.json及当前报告为准；本文件中的旧结果描述不用于交付结论。

# 广州A方向：模型数据字典、证据与来源

研究截点2026-11-03。模型运行成功不等于跨年口径统一、设施现状核验或项目获准。原采集底稿和原件保留，`README_collection_stage.md`解释历史观测。

## 1 证据分级和关键字段

| 文件/字段 | 单位与定义 | 证据等级及使用边界 |
| --- | --- | --- |
| `vehicle_observations.csv`的scope/period/qualifier/source_id/pdf_page | 指标范围、时点、限定词、来源ID、从1计的PDF物理页码 | 本地公开观测，严格区分年中/年末、累计推广/保有量/上牌。2018冲突值不平均，空白不为0 |
| `vehicle_annual_2015_2025.csv`的nev_stock_vehicles/registrations_vehicles | 车辆数 | 存量不等于新增；上牌的首次登记/迁移范围未澄清，未作为新车投放输入 |
| `district_population_2015_2024.csv`的permanent/registered/value_person | 常住/户籍、人 | 2024年11区常住人口仅为空间代理；不重复加全市行，不称实测车辆分布 |
| `outlets_candidates.csv`等设施线索 | 2022快照301条/235名称地址组合 | 不是现役独立企业或再生厂。未知坐标/能力不填0。两组外市及其他待定位记录未自动纠正 |
| `chemistry_parameters.csv`的Li/Ni/Co/Mn_kg_kWh | 各化学体系每kWh初装容量对应元素kg | Zhang文献迁移值；强度不是材料质量分数。2021份额不是广州早年观测 |
| `cell_coproduct_parameters.csv`的Cu/Al/F_kg_kg_cell | kg元素/kg电芯 | Wu按Spent battery feed表头取列，B/C列位置随表变化。组分有重叠，不逐行相加作全电池组成 |
| `wu_lifetime_density_points.csv`和`lifetime_parameters.json` | age年、密度；eta年、beta无量纲、rmse密度残差 | 对论文发展中地区S0已公开曲线回译，不是广州样本拟合。低残差不能证明本地预测准确 |
| `primary_lithium_mines.csv`与`primary_lithium_baselines.json` | LCE产量千吨、kgCO₂e/kgLCE | 论文Source Data中CL+AR卤水/AU锂辉石明确子集的产量加权值，非全球或本地供应商均值 |
| `ma_selected_scalars.json`、`everbatt_selected_cells.json` | 源变量/工作表指定单位 | 文献迁移。每项源文件、表名、单元格或数组位置见`parameter_evidence.csv`，本轮自动提取93项 |
| `planning_assumptions.json` | 所有字段均有含义和单位标记 | 独立设计情景，绝非本地实测：重建初值、未来K/r、车型权重、供料合格率、距离、成本曲线、等效资本和事故池示例 |
| `policy_parameters.json` | 比率、kgce/t、t/a、完整生效日期 | 区分规范条件/课程追加目标；未知EU碳阈值为null，判UNKNOWN；不把PASS当项目审批 |
| `raw/DATAV_440100.json` | 同源区级centroid经纬度与几何 | 辅助空间代理，测绘坐标系/路网/地块许可未核验，不计作权威政策统计来源 |
| `model_results/annual_dmfa.csv` | vehicle_inflow_reconstructed=反推车辆数；battery_replacements=更换套数 | 计算值非观测；车辆与电池龄同时跟踪，更换与车辆退出不重复 |
| `process_balance.csv` | product_inherited/external、residue_inherited/external，t元素 | 原废料继承与外加元素分开，补锂不算二次资源；残余去向未取得介质分配，不称实测排放 |
| `secondary_LCE_tpa` | 原料继承Li折算tLCE/a | 含修复材料内Li，不是全部实售碳酸锂；1tLi=73.88/(2×6.94)tLCE |
| `water_gross_L/water_net_proxy_L` | 新水输入+上游水代理/扣材料信用后的代理 | 未取得独立原生路径水清单，不能当完整纯水消耗LCA |
| `gwp_gross/net` | kgCO₂e/t入厂电池包 | 回收增量/系统扩展净影响；不含历史生产使用；净负值非现场负排放 |
| `LCOR_CNY_tLCE/MAC_CNY_tCO2` | 元/t二次LCE、元/tCO₂e | 历史混合价未平减的筛选值，不是2026报价或完整原生矿项目财务对比 |
| `projects.csv`的design_scale/scale_unit | 各工程对应设计规模及单位 | P01/P02/P05串联同批电池不重复加容量；P03新水规模不等于污水站处理量 |

所有CSV用UTF-8带BOM。观测缺值保留空白；null为未知。情景中的0只表示该情景不确认相应收益/费用，例如CCER未确认收入、主方案无再利用运营收入。排放计税当量0表示缺信息而未确认金额，不能解释为实际零排放或免税。

## 2 六篇文献与实际提取位置

课程PDF仍在`../../../starter_materials/lecture12-20261103-classroom-case3/precompiled_references/`，未改动。报告7.1逐篇解释采用及不采用的口径。

| ID | 论文/公开数据 | 实际位置和限制 |
| --- | --- | --- |
| PEISELER2024 | [论文](https://doi.org/10.1038/s41467-024-54634-y)、[Zenodo13936832](https://zenodo.org/records/13936832) | ZIP内`results/Source Data.xlsx/Figure 1!B3:I18`，CL+AR或AU产量加权；正文Methods电芯比能量。电芯/包、Li/LCE分开 |
| YAO2025 | [论文](https://doi.org/10.1038/s41560-024-01701-9) | 正文低10000、基约22000、高50000USD/tLCE情景；仅取敏感性思路，不将钠电模型当本地预测 |
| WU2024 | [论文](https://doi.org/10.1038/s43247-024-01667-2)、[Zenodo11160283](https://zenodo.org/records/11160283) | ZIP内`Initial data/life_curve.xlsx/S0`的C/E发展中地区列；`proportion_elements_contained_include_waste.xlsx`按标签取电芯Cu/Al/F。NMC523和Zhang NMC532关联是待人工复核代理 |
| MACHALA2025 | [论文](https://doi.org/10.1038/s41467-025-56063-x) | 正文约第3—6页Fig3/5工业NCA-eq比较及水—碳机制，不将6.1kg/kgNCA-eq改当LFP或LCE系数；95%NiCo不当作课程98%合规值 |
| ZHANG2025 | [论文](https://doi.org/10.1038/s41467-025-61481-y)、[Zenodo15342229](https://zenodo.org/records/15342229) | ZIP中`7-Parameter input`强度/容量/结构.mat，`Car_BEV_example.m`的14.5/2.07车辆代理。新模型按生存差分实现，不搬用累计概率逐年求和 |
| EVERBATT2023 | Zhang公开包中的Argonne EverBatt 2023 | `Geographic Par.`、`GREET IO`指定有标签常量；原工作簿样式兼容与失效缓存不影响只读XML提取，不执行宏 |
| MA2024 | [论文](https://doi.org/10.1038/s41467-024-52030-0)、[作者GitHub](https://github.com/RuifeiMa/Reuse-and-recycling-pathway-of-retired-batteries) | 本地`literature_raw/ma`保留5文件。LFPBasicData标量和LFP/NMCRecycle工艺计量；README记录2025利润单位更正，不采用更正前利润图点 |

三套Zenodo的原ZIP及metadata保留于`literature_raw/`，其中约66MB、34MB和5MB的归档为公开研究源文件，程序不执行其中代码、宏或环境。哈希见`archive_checksums.csv`。`parameter_evidence.csv`逐项记录来源、表/单元格/数组位置及证据等级；假设JSON不冒充这张证据表的实测数据。

Ma水量、SOH—补锂代理和LFP过氧化氢在环境/成本段写法不一致已在报告披露，待本地工艺核验。盐的环境信用按无水硫酸盐当量，收入按金属含量单价，避免盐吨/金属吨混算。原件转录、数学闭合、物理真实性和法律适用性分别判断。

## 3 权威扩展来源与归档状态

| 来源 | 使用内容及原文入口 | 核验/归档状态 |
| --- | --- | --- |
| 广州交通年报GZ2025等 | [2025交通年报](https://ghzyj.gz.gov.cn/attachment/8/8028/8028118/10830253.pdf)，物理17页图1.7、32页等 | 既有`source_manifest.csv`与raw保留，17项成功不等于17套完整数值序列 |
| 广州统计年鉴2025 | [表2-2区人口](https://tjj.gz.gov.cn/datav/admin/home/www_nj/2025/pdfs/2-2%20%20%E5%90%84%E5%8C%BA%E5%B9%B4%E6%9C%AB%E4%BA%BA%E5%8F%A3%E6%95%B0%20%282015-2024%E5%B9%B4%29.pdf) | 原PDF和240条值保留，区常住/户籍与普查修订说明分开 |
| 工信部2024年第42号 | [原公告](https://www.miit.gov.cn/zwgk/zcwj/wjfb/gg/art/2024/art_2ca9a4ed31de469d9da26ca70c83a868.html)，附件物理1—2、6—7、14页 | 在线PDF核验；本地下载403，不能称PDF已完整归档 |
| 工信部2026年第20号 | [原公告](https://www.miit.gov.cn/jgsj/jns/wjfb/art/2026/art_945f3df30a984763877679740ff296a3.html) | 2026-07-30梯次利用调整在线核验；本地403 |
| 六部门第73号令 | [官方规章](https://www.miit.gov.cn/gyhxxhb/jgsj/cyzcyfgs/bmgz/jdcjxl/art/2026/art_392462fdc40c415ea4a4129cac3028c2.html) | 2026-04-01施行，在线核验；本地403 |
| EU2023/1542 | [EUR-Lex合并文本](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02023R1542-20250731)，第7/8/77条、附件XII | 在线读取成功；本地空响应不可用，空文件已删除；最新授权法的碳阈值未核验 |
| 2023电力生命周期因子 | [生态环境部原附件](https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202501/W020250123519612367413.pdf) | 第1页全国0.6205、水电0.0143、输配0.0036，本地PDF保存；非广东生命周期实测 |
| 2023直接CO₂电力因子 | [生态环境部原附件](https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202512/W020251231726284332528.pdf) | 广东0.4419，仅作口径压力测试；PDF保存 |
| 广东环境税 | [省税务局公布决定](https://guangdong.chinatax.gov.cn/gdsw/ssfggds/2017-12/19/content_a8b82adb0fd341d99cc89d18c77def32.shtml) | 大气1.8/水2.8元每污染当量，HTML保存；未来更新另核，不把征求意见当生效法 |
| 广东水资源税 | [粤财规2024第3号](https://guangdong.chinatax.gov.cn/gdsw/ssfggds/2026-09/22/content_f4b812c29f8b425bac06aa89f7c97649.shtml) | 地表水生产等0.2元/m³，直接取水适用、市政购水不重复计税；HTML保存 |
| HJ1186—2021 | [生态环境部标准页面](https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/gthw/qtxgbz/202108/t20210820_858544.shtml) | 2022-01-01实施；PDF保存。具体排放/厂址适用限值待环评/许可专项核验 |
| DataV440100 | [区级地图原JSON](https://geo.datav.aliyun.com/areas_v3/bound/440100_full.json) | JSON保存；仅辅助空间代理，不计入权威法规/统计数量，不具有审批测绘效力 |

扩展权威来源超过4项，但数量达标不能替代适用性核查。`new_source_urls.json`保留下载入口；`archive_checksums.csv`只证明实际文件字节完整，不保证内容已完整核验。工信部403/EU空响应记录在报告及本表，不以错误响应伪装政策原件。无项目CCER方法学或ETS覆盖资格证明，基准交易收入0，不推断全行业一概无资格。具体政策差异见报告第3章。

## 4 结果与仍缺数据

`annual_dmfa.csv`和`chemistry_dmfa.csv`输出逐年/材料流，`stock_flow_balance.csv`逐年4元素校验，`process_balance.csv`设计年7元素扩展。`all_scenarios.csv`保留1650组及FAIL；`pareto_front.csv`与`anchors_by_price.json`按固定外生锂价分别求前沿；`recommended.json`是工程和报告唯一主方案来源，`projects.csv`按工程ID关联。`sensitivity.csv`固定主方案压力测试；`dmfa_uncertainty.csv`假设包络不是置信区间；`supply_coverage.csv`标远期需求和一期产能缺口，远期潜力默认具备增量能力。

仍缺：广州首次登记/迁移与早期车龄、实际车型容量/化学结构/寿命/更换率，现役设施真实能力与接收许可、路网及工业地块，生态红线/水源保护/防火环保距离，过程能耗和介质污染实测，独立两种原生Li水清单，尾渣及含氟高盐水终处置，产品品位/承购/设备和服务报价、排放计税当量、税后现金流与营运资金、成员实际贡献与本人签字。透明情景允许继续研究，但以上未满足项仍影响评分及实施可信度。

## 5 本地再生项目证据补核验

`facilities_local_evidence.json`新增6项公开观察，关联广州优美和花都园区项目，**不代表6家独立工厂**。`facility_source_manifest.json`记录URL、下载字节和状态；本轮六项网页经浏览检索核验，但直接下载均403，因此没有声称raw下保存了这些HTML全文。JSON保存带定位的转录与官方链接，后续须补存可获取的原件。报告4.2.1自动读取该JSON成表；EIA批复与节能审查是设计口径、投产报道是投资方公开披露、环评受理不等于批复，均不推断现场实际吞吐或可签约剩余能力。

| 来源ID | 官方/原始入口 | 核验位置 |
| --- | --- | --- |
| GZ_YOUMEI_EIA2024 | [市生态环境局环评批复](https://sthjj.gz.gov.cn/gkmlpt/content/9/9802/post_9802113.html) | 穗环管影2024第8号，厂址、一期混合进料27500t/a、二期废料21200t/a另有黑粉7903.784t/a、总投资38365万元；不同进料不可直接转整包能力 |
| GZ_YOUMEI_ENERGY2024 | [市发改委节能审查](https://fgw.gz.gov.cn/tzgg/xmgg/content/post_9843213.html) | 第二、三条，25300t/a和0.395tce/t进料；年9986.85tce仅为达产设计，不是单位LCE能耗 |
| GZ_YOUMEI_PLANNING2026 | [市规自局规划条件核实公示](https://ghzyj.gz.gov.cn/ywpd/cxgh/ghxkgsgb/phgbnew/gbt/2025/content/post_10802947.html) | 公示字段实际为2026-05-10，不能按URL的2025目录推定年份；同址主体名称不同需关联，不能重复计厂 |
| GZ_YOUMEI_OPERATION2026 | [投资方2026-03-25投产报道](https://www.u-power.com.cn/detail/222.html) | 投产事件主体及日期；未采用宣传性效率作为实测参数，页脚天河办公地址不是白云工厂地址 |
| GZ_HUADU_PLAN2025 | [花都区重大项目说明](https://www.huadu.gov.cn/xxgk/zdxm/content/post_10213799.html) | 2025-04-14，规划电池综合及拆解6万吨/a；总投资含储能制造/报废车等，不能套成纯精炼投资 |
| GZ_HUADU_EIA_ACCEPT2025 | [市生态环境局环评受理](https://sthjj.gz.gov.cn/hjgl/jsxm/hpslgg/content/post_10604965.html) | 2025-12-22、建设主体及地址；与重大项目同园区关系尚未逐项统一，不合并能力 |

已有真实地址和公开项目证据，但尚未将其转成经运营及合同核实的地块级优化候选。`local_energy_crosscheck.json`将模型电/热能量折成kgce/t包，与公开节能设计395kgce/t进料作尺度核对；边界不同，不进行效率排名或据此判断企业是否符合2200kgce/tLCE要求。该差异反映清单本地化仍需补做，不能仅因有本地项目报道就宣称模型已经得到本地验证。
