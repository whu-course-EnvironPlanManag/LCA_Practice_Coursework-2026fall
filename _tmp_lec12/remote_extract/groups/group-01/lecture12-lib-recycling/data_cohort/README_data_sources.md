# 数据字典与来源声明

## 当前证据状态

组员补充的表格可以驱动条件计算，但不是完成了湖北实测队列校准。所有安装行均为`documented_scenario`；公开注册统计锚点、人口分摊、未来安装和材料插值并存。接口完整不等于证据完整，运行须显式选择`--exploratory`。16项具体问题见[audit/data_quality_issues.csv](audit/data_quality_issues.csv)和[核查说明](../report/Data_and_Code_Audit.md)。

原始6篇论文、17份补充来源在`raw/references/`，20张年鉴在`raw/湖北统计年鉴2025-定/`。`yearbook_cells.csv`保存3878个非空单元格；`hubei_yearbook_context.csv`整理58条背景统计；`yearbook_source_manifest.json`记录原件SHA。汽车工业产量、各类燃料保有量、电芯自然只数没有直接替代动力电池安装容量。

## 输入接口

所有正式记录保留`source`和`source_locator`。比例用0—1，金额统一CNY；观测、外部代理和研究设计须分别说明。未知量不得因程序允许填0而写成实测零。

| 文件 | 每行/单位 | 当前来源与适用边界 |
| --- | --- | --- |
| installation_cohorts.csv | 城市×安装年×体系；installed_kwh为kWh | 2010—2040，1054行情景；部分注册锚点可查，其余人口权重/插值/未来设计未充分校准 |
| material_parameters.csv | 原安装年参数；eta_years、beta；整包kWh/kg；kg元素/kWh | LFP和聚合NCM共62行；η=10、β=3.5及材料演变原表待核，不能称湖北拟合 |
| opening_stock.csv | 基准年前一年的存活kWh和整年年龄 | 当前采用完整情景历史，本表仅表头；不意味着2010年前真实存量已证实为0 |
| collection_rates.csv | 年×城市，正规收集比例 | 527行设计序列；代表年外层遍历覆盖规划期收集率，历史值保留 |
| echelon_parameters.csv | 年×体系，分流比例、延迟年 | 比例0是本次不启用的情景，不因旧管理文件废止就断言所有梯次利用被禁止 |
| recovery_parameters.csv | 工艺×体系，Li/Ni/Co/Mn全链有效比例 | 4行研究代表值，不能用全链有效值替代冶炼工序政策分母 |
| energy_factors.csv | 代表年，kg/kWh、L/kWh、CNY/kWh | 0.4044为官方湖北2023电力CO2因子；其他GWP/水/绿电价为异时点引用或代理，未形成同边界电力LCA |
| lci.csv | 工艺×体系×过程，quantity_per_t_battery以1t整包进料为基础 | 电力行kWh；其他聚合单耗和负荷待补试剂/热源真实数量及数据库活动；不能声称完整可核证LCA |
| procurement_quotes.csv | 体系×LCE价格×SOH；CNY/t电池 | 两档Li价70500、93481.3，SOH0.8；废料形态、时点及税运口径未完全匹配，作为配对情景 |
| primary_lce_baselines.csv | brine/spodumene各1行，1t LCE、cradle_to_gate | 中国参考碳强度13300/13900 kg/t；水200000/60000 L/t和成本40000/66700 CNY/t待完善，不冒称澳洲专属值 |
| network_nodes.csv | 城市起点/收集/精炼，t/y、CNY、WACC与年限、经纬度 | 35点，精炼点R_JINGMEN_SCENARIO的100000 t/y是假设；成本0代表漏项/未计，不是工程概算 |
| road_distances.csv | from→to，recycling/echelon；km，CNY/(t·km)、kg/(t·km)、L/(t·km) | 34条边，其中17条同城0km；OSRM记录缺原始响应，货运因子为代理，未核实厂址与危货线路 |
| tea_cost_benchmarks.csv | 投资单位CNY/(t·年)、单耗或费用情景 | 3个项目的工艺边界不同；fixed OPEX3%/6%、收集费250 CNY/t是明确假设 |

## 政策、工艺配置与修正

`model_config.json`采用2030年代表年、两条LCE工艺、20×25网格、两个报价与两种原生参考。70%正规收集率是小组规划目标，不是全国法定红线。`policy_rules.json`保存2024年本课程筛选、欧盟分期日期及湖北水税参考。任何政策数值通过不代替真实企业许可/认证。

- 将0.32环境收入分配改为1：未取得一致副产品清单，不确认未证实的环境信用。全链负荷归LCE仍是条件筛查，不弥补清单缺项。
- `historical_installations_complete=false`，仅显式声明完整历史情景覆盖。省外流入流出没有观测，采用封闭区域情景。
- 容差1e-9内的目标差异视为等价，保留不同物理方案；B并列时固定输入顺序，不能声称唯一工程最优。
- 精炼点容量100000 t/y、收集点容量、工序Li回收90%及1900 kgce/t产品等是输入假定，未独立核实为某企业现况。
- 财务主情景缺固定费用、未知税费和副产品收入，仅可作已计费用筛查。`postprocess.py`另外复现资本敏感性，不篡改主工况。
- 新电池再生Li含量6%/12%分别从2031/2036年8月18日起适用；与废电池Li材料回收50%/80%及正规收集率分开。
- 水资源税直接工业地表/地下水0.15/0.2元/m³可查；实际主体、水源、许可量未核定时，不自动套入工程。未知应税排放不由治理费代替。

## 主要核实入口

1. 湖北统计年鉴原始表及提取SHA：`raw/湖北统计年鉴2025-定/`，表1607、0607、1005等。
2. 湖北日报2024-12-25原报：<https://epaper.hubeidaily.net/pc/attachment/202412/25/dd813655-57ba-4723-a3ea-b70a494479fb.pdf>。1—11月新增注册34.4万辆、当时存量96.7万辆，不能当全年安装。
3. 武汉2024年末新能源车58.02万辆：<https://www.wuhan.gov.cn/sy/whyw/202501/t20250120_2520341.shtml>；与省级报道时点不同，60%份额仅作设计。
4. 湖北电力CO2：<https://www.mee.gov.cn/ywdt/zbft/202601/t20260105_1139911.shtml>；须与产品LCA电力因子区分。
5. 工信部2024年本：<https://jxt.hubei.gov.cn/bmdt/rdjj/202412/t20241228_5481302.shtml>；引导性规范不自动等同审批前置条件。
6. 2026年管理办法：<https://www.miit.gov.cn/gyhxxhb/jgsj/cyzcyfgs/bmgz/jdcjxl/art/2026/art_392462fdc40c415ea4a4129cac3028c2.html>。
7. 欧盟法规Article8/77/AnnexXII：<https://eur-lex.europa.eu/eli/reg/2023/1542/oj>。
8. 清华中国锂盐碳足迹介绍：<https://www.tsinghua.edu.cn/info/1175/119485.htm>；不将原文NCA-eq强度移用为LCE。
9. 湖北水资源税：<https://czj.wuhan.gov.cn/FBJD/ZCWJ/GFWJ/202412/t20241231_2511060.html>。
10. 福建项目投资与工艺：<https://gxt.fujian.gov.cn/zwgk/jsxm/xmhz/202408/t20240812_6500736.htm>。其余惠州、襄阳投资出处和未取得原文的限制保留在tea_cost_benchmarks.csv，不能自动视为荆门报价。

## 下一步资料优先级

先补历年真实安装/注册转容量及年龄结构、原始寿命与材料强度；再补单厂能力、候选点和道路响应；随后补LCI、同口径采购与产品报价、固定投资运维、产品质量与排污/取水证明。若原始证据仍不能支撑，将参数保留为情景并做敏感性，不能把“文件有出处字符串”当成已核实。

## 输出

`results/`是可复算数值、报告指标和运行日志，不放图片；`../figures_output/`只放PNG。原始/补充数据与计算结果分层，避免三套CSV或不同版本报告并行使用。
