# 数据与代码核查说明

审查日期：2026-11-03。此文记录发现、处理和剩余证据需求，不是评分或合规认证。已依据用户指示整合张宏生的资料与陈海滨的原模型；曾飞楊负责报告撰写，最终文本仍需全员确认。

## 重复与版本处理

逐字节比较发现34个完全相同文件：6篇预编译论文、20张年鉴、3张背景PNG及其他5个文件。部分源码只存在CRLF/LF差异，并无算法升级。独立保留原始资料一份，合并新数据与最新PNG单格式代码。数据表和代码的不同版本经逐项判断，不按同名直接删除。`audit/duplicate_inventory.json`保留原始清单。

两种原生基准不改变再生方案的绝对排放、水耗和LCOR，只改变比较差额与MAC，重复图合并展示；两套数值前沿和锚点仍分别保存。正式图目录仅PNG，数值结果在data_cohort/results，原始资料在data_cohort/raw。旧目录清理前保留工作区外恢复归档。

## 逐项发现与处理

| 文件 | 程度 | 发现 | 本次处理 | 尚需证据 |
| --- | --- | --- | --- | --- |
| installation_cohorts.csv | 高 | 1054行均为documented_scenario；市州份额使用人口代理、历年与未来安装为研究设计。 | 将“完整历史实测”改为“完整历史情景覆盖”；不再声称湖北拟合预测。 | 待补逐年注册/装机、车型容量、材料结构、换包和迁移资料。 |
| material_parameters.csv | 高 | eta=10、beta=3.5的原表未取得；2010—2040材料强度和比能量含插值/代理。 | 保留组员原数值作为条件情景，未提升为观测或校准参数。 | 原始寿命表与材料强度需逐年/逐体系核验。 |
| model_config.json | 高 | 0.32取LFP湿法收入比例，却用于混合LFP/NCM与火法，且副产品清单为空。 | 改为全链环境负荷100%计入LCE的保守情景。 | 有一致副产品质量、收益及分配依据后才能采用经济分配。 |
| energy_factors.csv | 高 | 0.4044是省级电力CO2排放因子，不是完整生命周期GWP100因子。 | 图文称碳影响筛查，不声称获得完整产品碳足迹。 | 待补同边界电力生命周期因子及输配电、线损与其他温室气体。 |
| energy_factors.csv | 中 | 绿电水耗0.05与电网2 L/kWh为代理，绿证交易不能自动代表新增无水耗绿电。 | 明确水碳结果依赖设定，不声称普遍存在此方向的权衡。 | 待补湖北供电结构、额外性、来源和水因子。 |
| lci.csv | 高 | 热源、试剂、污染治理多为每吨电池的聚合代表值；缺物质种类/单耗/数据库链。 | 只用于条件筛查；不伪称完成独立可核证LCA。 | 待补单元过程与上游清单。 |
| network_nodes.csv | 高 | 荆门单厂100000 t/y证据不足；已查工信部案例为多企业合计。 | 改名R_JINGMEN_SCENARIO，产能只作假设。 | 待补单厂批复、运行/可用能力与其他候选地。 |
| network_nodes.csv | 高 | CAPEX与固定OPEX全为0，收集点成本未计。 | 保留为变动费用筛查口径；另写可复现资本敏感性，不称完整LCOR。 | 缺真实新增投资、存量分摊及运维报价。 |
| road_distances.csv | 中 | 同城道路为0，OSRM未附原始响应；只有一个精炼候选点。 | 说明忽略市内接驳、固定目的地配置，不称全省最优选址。 | 补原始OD响应、短驳/危货运输和多候选点。 |
| procurement_quotes.csv | 高 | 不同日期、不同形态的废料报价被映射到整包、两档Li价和固定SOH。 | 保留为报价配对情景；不推断一般价格弹性。 | 补同形态含量、税运口径、日期与SOH报价。 |
| primary_lce_baselines.csv | 中 | 13.3/13.9为中国产能平均参考，不能称澳大利亚矿专属值；水耗/成本来源不完全。 | 按中国盐湖/锂辉石参考情景列示；节水与MAC均附边界。 | 原生路线同地域同功能单位完整LCI和成本。 |
| model_config.json | 高 | 1900 kgce/t等工厂合规指标按阈值情景填写，无法从聚合LCI独立算出。 | 仅报告课程数值筛选，不对真实工厂宣告认证或完全合规。 | 补产品能耗分母、合规检测、含氟排放和真实设施证明。 |
| model_config.json | 中 | 水资源税0表示漏项而非法定免税，碳信用也非自动收入。 | 核实湖北工业税额0.15/0.2及超量累进规则并提供独立函数，主情景仍标为未计。 | 待补直接取水主体、许可量、应税排放与方法学。 |
| decision.py | 中 | 严格浮点比较会把舍入误差作为支配改进，丢掉实质等价的收集方案。 | 以1e-9相对目标尺度识别等价，保留所有物理方案；固定顺序选择代表B。 | B不是唯一工程最优，需多目标绝对资源量或固定费用后再排序。 |
| run_analysis.py | 高 | 原run_manifest写artificial_provincial_data=false，与全情景安装表不一致。 | 显式标为contains_documented_scenarios=true和observed_hubei_forecast=false；正式运行需--exploratory。 | 未经进一步核验不得转换为实证预测。 |
| report/第十二讲_方向A_报告框架.md | 高 | 框架提前应用2031年6%含量要求，套用NCA-eq原生强度，固定SOH分流与全省最优选址无现成依据。 | 报告采用法定日期、LCE同功能单位和条件物流结果；不声称证明直接修复优于湿法。 | 直接修复应另建CAM或寿命服务功能单位。 |

## 证据补齐（2026-11-03 第二轮）

逐项状态同时登记在 [audit/evidence_gap_register.csv](../data_cohort/audit/evidence_gap_register.csv)（字段：gap_id、file_field、status、evidence_found、value、unit、source、source_locator、action_taken、residual_limitation）。状态定义：`resolved`＝已取得可用证据并按证据处理；`partial`＝取得部分证据但不足以替换输入；`unavailable`＝公开渠道未取得；`scenario`＝证据本身只是阈值/情景，不能升级为观测。

| gap_id | 文件/字段 | 状态 | 新增证据 | 落盘位置 | 剩余缺口 |
| --- | --- | --- | --- | --- | --- |
| G01 | installation_cohorts.csv | partial | 湖北1—11月新增注册34.4万辆、存量96.7万辆；武汉2024年末新能源车58.02万辆 | `sources_2026/hubei_drc_2024_new_energy_registrations.md` 等 | 逐年分市州上牌转容量、车型容量、换包、省际迁移 |
| G02 | material_parameters.csv | partial | 动力电池Weibull β=3.5、η=10年见《有色金属(冶炼部分)》2026(2)摘要 | `sources_2026/weibull_lifetime_2026_nonferrous_metallurgy.md` | 付费全文；逐年材料强度与比能量原表 |
| G03 | lce_environment_allocation_fraction | resolved_as_scenario | 0.32来自LFP湿法Li2CO3收入占比17.7%—32.4%，因无副产品清单改为1.0 | `model_config.json` allocation_source | 副产品清单与收益，才能经济分配 |
| G04 | grid_gwp_kg_per_kwh | partial | 湖北2023电力CO2因子0.4044 kgCO2/kWh（仅CO2口径） | `sources_2026/mee_2023_provincial_electricity_co2_factors.pdf` | 输配电损耗、上游燃料链、非CO2温室气体 |
| G05 | green_water_l_per_kwh | partial | 检索到风电约0.004 L/kWh量级；未取得可存档原文，0.05仍为设计值 | 未落盘 | 湖北供电结构、额外性、可引原文 |
| G06 | lci.csv | partial | 骆驼襄阳节能审查：810.17 kWh/t、160.84 m³天然气/t、2.08 m³新水/t；Maritz 2024每kWh清单（HCl 55.4、H₂SO₄ 37.3、NaOH 30.4、H₂O₂ 21.9 kg）；ACS ES&T 2025沉淀工段6.956 kWh | `sources_2026/unit_process_lci_and_primary_lce_2024.md`、`hubei_drc_2023_camel_50kt_energy_review.md` | 只作数量级核对，未替换`lci.csv`；`process_heat` 80—100 kgCO₂/t低于实测天然气折约347 kgCO₂/t；缺试剂品种单耗与上游数据库版本 |
| G07 | R_JINGMEN_SCENARIO 产能 | partial | 荆门单厂批复：10万t/a含锂废料（3万t黑粉+7万t含锂废渣）、1万t/a电池级LCE、投资5.98亿元 | `sources_2026/jingmen_100kt_lce_eia_approval.md` + 同名PDF | 整包拆解/分选与梯次产能、实际利用率、其他候选点 |
| G08 | capex / fixed_opex | partial | 新增荆门5980元/(t·年)；已有惠州6200、襄阳12117.42、福建23240.08 | `tea_cost_benchmarks.csv`；荆门证据存档 | 荆门口径为含锂废料，未并入敏感性；缺整包厂新增投资与运维报价 |
| G09 | road_distances.csv | partial | 34条OSRM道路边；17条同城0 km为设计 | `road_distances.csv` | 原始OD响应、短驳与危货线路、多候选点 |
| G10 | procurement_quotes.csv | partial | 卓创2025-08-22三元19650元/t、SMM2026-11-02 LCE 93481.3元/t、2025年LFP包3200元/t | `sources_2026/sci99_2025_08_22_scrap_triad_price.html`、`smm_2026_11_02_lce_price.html` | 同形态含量、税运口径、同日SOH报价 |
| G11 | primary_lce_baselines.csv | partial | 模拟LCA：盐湖5.0—25.0 kgCO₂e/kg LCE、水0.2—7.7 m³/kg；锂辉石17.1—22.3、水0.2—0.5；Science 2026硬岩精炼约20 t CO₂e/t LCE | `sources_2026/unit_process_lci_and_primary_lce_2024.md` | 模型13.3/13.9与200/60未改；报告改用证据区间；MAC与帕累托未按新基准重算；区间为模拟值 |
| G12 | lce_energy_kgce_per_t | scenario | 1900 kgce/t为规范条件阈值情景 | `policy_rules.json` | 产品能耗分母、合规检测、含氟排放、设施证明 |
| G13 | water_tax_cny_m3 | resolved | 工业地表0.15、地下0.20元/m³；超量2/3/5倍；擅自3倍 | `sources_2026/hubei_water_tax_2024.md`；`policy_engine.hubei_industrial_water_tax` | 取水主体、许可量、实际取水量、应税排放 |
| G14 | decision.py 浮点等价 | resolved | 1e-9相对容差，保留全部物理方案，B有11个同距方案 | `code_implementation/decision.py`、`test_models.py` | 需绝对资源量或固定费用后再排序 |
| G15 | run_manifest 标记 | resolved | `contains_documented_scenarios=true`、`observed_hubei_forecast=false` | `results/run_manifest.json` | 未经实证核验不得转为预测 |
| G16 | 报告框架_方向A | partial_resolved | 采用2031/2036法定日期、LCE同功能单位、条件物流 | `sources_2026/eu_2023_1542_batteries_regulation.html` | 直接修复需另建CAM或寿命服务功能单位 |

补充说明：

1. **荆门证据的口径**。批复项目为"10万吨含锂废料（一般工业固废）→1万吨电池级碳酸锂"，原料是黑粉与含锂废渣，不含整包拆解。因此只补"荆门存在万吨级LCE再生能力"的单厂证据，不把精炼节点容量改写成整包处理能力，也不把 5980 元/(t·年) 混入整包厂的资本敏感性表。
2. **水资源税不进入主情景**。税额与累进规则已核实并有独立函数，但取水主体（直接取水或公共供水购水）、许可量与年取水量未知，故 `water_tax_cny_m3` 仍为 0，含义是"本情景未计入"。若改填 0.15，每吨电池仅增约 0.27 元，但会改变输入哈希，必须整体重跑并更新 `run_manifest.json`。
3. **未改动的输入**。本轮只新增证据存档、台账与说明，未修改 `model_config.json`、`network_nodes.csv`、`tea_cost_benchmarks.csv` 的数值，`data_cohort/results/` 的 4000 组结果与输入哈希保持可复现。`model_config.json` 中"未取得湖北水资源税适用税额"的旧措辞与 G13 不一致，属待随下次重跑一并订正的文字项，不影响数值。
4. **本轮新增的单元过程与原生LCE证据**。G06取得骆驼襄阳节能审查实测单耗与Maritz 2024、ACS ES&T 2025的单元过程数据；G11取得Mas-Fons 2024盐湖/锂辉石模拟LCA与Science 2026硬岩精炼值。二者均只升级为`partial`：前者用于数量级核对、未替换`lci.csv`；后者用于报告区间对照，`primary_lce_baselines.csv`的13.3/13.9与200/60保持原值，故MAC与帕累托前沿仍基于旧基准，改用新区间须整体重跑。
5. **仍未取得原文或未替换输入的项**：G05（可存档水耗原文）、G06（试剂品种单耗与上游数据库版本）、G11（同口径成本与本地化LCI），以及 G01/G02/G10 的同口径细项。这些保持 `partial`/`unavailable`，不因新增了说明文字而升级为已核证。

## 复算结论的边界

26项模型测试通过只能证明相应算法与输入约束按预期工作。4000组参数组合中2200组满足本组70%收集率目标，1800组按规划目标单列，不能说因违法被否决。原版在低收集率下选B、按0.32分配环境负荷和将固定费用记0的结论不得直接写进最终报告。

修正后的B是条件代表工况；考虑浮点等价后存在11个同距物理方案。2040年收集量超过假设单厂上限，远期只完成规模压力提示，未伪造扩建最优解、项目总概算、产品环境认证或成员签字。

原始网页部分参数仅有摘录，付费或未存档原文没有被本次升级为已核证数据。报告按科学陈述保留限制；如需作为投资可研，须补充主体、工艺与地区一致的原始凭证后重新运行。
