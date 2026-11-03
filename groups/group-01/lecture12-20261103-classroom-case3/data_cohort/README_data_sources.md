# 输入字典、现有证据与组员资料交接

## 已提供的区域资料

输入来自本任务目录中的20张湖北统计年鉴.xls。`yearbook_cells.csv`保留3878个非空单元格及文件、工作表、坐标、数据类型与SHA-256；`hubei_yearbook_context.csv`整理58条可直接核对的背景指标，原文件不改写。

| 资料 | 可用内容与边界 |
| :--- | :--- |
| 16-7私人车辆拥有量 | 2000、2005、2010、2015、2018—2024年的私人汽车保有量。非连续年份且包括燃油车，不能直接替代动力电池安装序列 |
| 16-6民用车辆拥有量 | 2024民用汽车11877843辆，是汽车总量，不是新能源数量 |
| 工业产品产量续表 | 2024新能源汽车507318辆为工业产量，不是省内新增上牌；锂离子电池1762865847只为自然只，不能直接换成整包数量或GWh |
| 6-7全社会电力平衡表 | 表内为2019—2023年，不能误称2024。发电结构与消费侧碳因子不同，不从该表直接赋值回收厂EF |
| 10-5主要城市电力情况 | 2024年12个主要城市用电数据；不是全部市州，不能据此把未列地区用电量填零 |
| 土地、行政、人口、GDP、交通和三废表 | 已完整保留原始单元格，可供诊断和候选地资料核查；不能仅凭人口或GDP比例生成市州退役电池量 |

文件名与表内标题存在差异时，以表内标题、表头和单位为准。例如人口表不能因文件名提及人口密度就将实际城镇化率列当作密度。原表中的零、空值和汇总差异保留，不人为调平。

## 优先请组员补充的资料

1. **湖北省及市州历年电池安装或可转换的新能源注册数据**：分BEV/PHEV、车型、安装年、正极体系，含替换电池；若只有保有量，还需年龄结构、平均电池容量、换包、跨省流转等转换依据。不得使用507318辆工业产量替代。
2. **寿命与物质强度**：Weibull eta、beta的实际出处；各安装年份整包比能量及Li/Ni/Co/Mn含量，明确整包/电芯/活性材料边界。论文中的6—8年时间滞后不等于可直接填入的Weibull尺度参数。
3. **正规收集、梯次比例和滞后**：区分实际统计、规划情景和文献代理；梯次库存起始状态、回流位置和返厂收集边界。
4. **工艺与区域环境清单**：回收率、设备能耗、热源、试剂、治理负荷和排放、用水、电力碳/水/价格因子。省级工业用电量不能替代工厂可用容量。
5. **候选设施与道路OD**：坐标、合规/环境筛选、可用产能、建站投资、固定费用、道路距离与运输因子。不能把城市中心坐标说成获批厂址，也不能用直线距离冒充道路运输距离。
6. **经济与政策参数**：明确日期的CNY报价，或汇率、原币和换算出处；不同Li价与SOH条件下的收购价；实际税费口径、合同溢价和可用碳信用证明。未知金额不能默认为零。

## 输入文件与字段单位

所有正式记录都必须填写`source`与`source_locator`。前者为完整文件或权威URL，后者为页码、表号、工作表单元格或数据库行。所有比例填0—1，所有金额统一CNY。规划情景不是观测，应在出处中标明“有依据的研究设计/情景”。

| 文件 | 每行含义 | 关键字段 |
| :--- | :--- | :--- |
| `installation_cohorts.csv` | 城市×正极体系×原始安装年 | `installed_kwh`为新增安装容量；`record_type`为`observed_installation`或`documented_scenario`。相同三元组须先合并车型，不允许重复计入 |
| `material_parameters.csv` | 体系×安装年 | `eta_years`、`beta`；`pack_specific_energy_kwh_per_kg`必须是整包；Li/Ni/Co/Mn均为kg元素/kWh。没有某元素填有证据的0 |
| `opening_stock.csv` | 开始模拟前一年的存活队列 | `base_year=model_start_year-1`，`vintage_year=base_year-age_years`；`surviving_kwh`不是当年原始安装量。采用完整历史时本表可空 |
| `collection_rates.csv` | 年×城市 | 正规收集率，模型计算区间每年必须有记录；明确为零也要有依据 |
| `echelon_parameters.csv` | 年×体系 | `echelon_share`为正规收集后分流比例；`delay_years`为整年。无梯次需明确填0比例，不自动假设 |
| `recovery_parameters.csv` | 工艺ID×体系 | `Li_effective_recovery`等为进入全链再生产品的总有效回收率，**不是仅冶炼工序回收率**；可能低于90%，不能直接拿来判定冶炼是否达标 |
| `energy_factors.csv` | 代表年、省域同一口径 | grid/green的GWP为kg CO2e/kWh、水耗L/kWh、价格元/kWh，不能只换碳因子却默认水耗/价格不变 |
| `lci.csv` | 工艺ID×体系×清单项 | 所有数量基于1吨整包精炼进料；电力kWh、运输t·km，其余quantity的unit与单位因子严格对应。`electricity_mix`因子由能源表读取，其余项直接读取独立因子 |
| `procurement_quotes.csv` | 体系×碳酸锂价格×SOH | `lce_price_cny_t`元/吨LCE，`purchase_cny_per_t_battery`元/吨废电池；程序精确匹配，不自动拟合或外推SOH系数 |
| `primary_lce_baselines.csv` | 卤水/锂辉石两行 | `route=brine/spodumene`；`functional_unit=t_LCE`，`system_boundary=cradle_to_gate`，GWP为kg CO2e/吨LCE、水耗L/吨LCE、生产成本元/吨LCE；不得填NCA-eq指标 |
| `network_nodes.csv` | 一个有出处的城市起点/候选设施 | `role=origin/collection/echelon/refining`；`capacity_t_y`设计产能，投资元、WACC、寿命年、固定运行费元/年；eligible必须true/false；坐标为经纬度。收集环节单吨处理费可填；精炼和梯次变动费由LCI/服务模型计，节点该字段为0 |
| `road_distances.csv` | 一条有方向、类别明确的运输边 | `commodity=recycling/echelon`；道路km；元/(t·km)、kg CO2e/(t·km)、L/(t·km)。允许边由模型约束，不接收当年梯次直接转精炼的虚构边 |

### 工艺JSON配置

`pathway_fields_reference.json`只是字段结构，null不是参数。组员填好有出处的工艺对象，再加入`model_config.json`的`pathways`。当前空列表会阻止正式模拟。

- `id`与LCI、有效回收率表中的`pathway`一致；`pathway`类型为hydro/pyro/direct。
- `refining_node_ids`限制该工艺可选的真实候选基地。
- `lithium_output_kind=battery_grade_LCE`时才能进入本版同功能LCE比较。直接修复正极不允许伪装成LCE出售。
- `policy_case`中的冶炼回收率是**工序**指标，`recovery_parameters.csv`是**全链有效**比例；有效值不得高于对应工序比例。
- 物理能耗、回收率、R&D等需对应同一规划工况。不能把别的工况达标指标复制进来。EU碳足迹值若属于整电池，不能拿每吨再生LCE的碳足迹替代。
- `lce_environment_allocation_fraction`及`allocation_source`必须说明多产品及梯次服务负荷如何归属Li产品，不能凭视觉或任意均分指定。
- `coproducts_per_t_battery`每项须明确同单位产量与价格及出处；Cu/Al箔、盐和含金属量价格不能混用。主Li产品收入由程序单列，不再放进本数组。
- 梯次比例大于0时必须提供`echelon_service`的成本、碳、水、服务收入及出处。当前采用供给服务当年记账的简化模式，不是跨期梯次NPV；如要长期运营现金流，须扩展逐年收益模型。
- `financial_policy`不得把“没有提供金额”理解为“金额为零”；确认不适用碳信用或出口溢价时选择`none`。`contract_scenario`是合同假定，不是法规统一补贴。
- 网络投资与固定OPEX已计算一次，LCI不得再放一行同一资本年金。工艺额外CAPEX应落在相应候选设施，不可在区域层重复加总。

## 可修改的研究设计

默认规划期2026—2040、代表年2030和20×25网格仅作为研究设置，可由小组调整。`model_start_year=2010`不是已确认的湖北首个安装年份；必须根据完整历史修改。若省内历史不完整，应采用有年龄结构的期初存量，不从2010年起默认之前没有电池。

每年所有城市/体系都要有输入；缺失城市不能补0。2024总汽车数不能按人口比例机械分配成各地新能源汽车。正式结果应记录资料覆盖地区及未覆盖部分；不得把12个主要城市当作全湖北。

## 政策来源及需组员复核的地方

课程阈值来自任务书2.2、功能模块2及评分量表，配置为课程筛选标准。正式核对入口：

- [工信部2024年本解读](https://www.miit.gov.cn/xwfb/gxdt/sjdt/art/2024/art_7c15af2a502341adacec6c44d16da11b.html)。
- [湖北省经信厅正式转发](https://jxt.hubei.gov.cn/bmdt/rdjj/202412/t20241228_5481302.shtml)。正式文本明确其为行业引导性文件，不具有行政审批前置性、强制性；代码`Redline_Vetoed`是课程筛选标签。
- [EU 2023/1542正式文本](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R1542)，重点Article 8、77和Annex XII。到期材料回收率与新电池强制含量的起始日期不同；回收率也不等于正规收集率。
- [2026年动力电池回收和综合利用管理办法](https://www.miit.gov.cn/gyhxxhb/jgsj/cyzcyfgs/bmgz/jdcjxl/art/2026/art_392462fdc40c415ea4a4129cac3028c2.html)，需要政策负责组员继续梳理适用条款；本代码不冒称已覆盖全部新规。

税额、当期价格、信用方法学、授权法案细则及地方许可仍需组员补充。当前没有填入无来源湖北水税、环保税、碳价或出口碳阈值。
