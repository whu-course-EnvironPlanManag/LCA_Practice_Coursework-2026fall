# 工业园区绿色甲醇系统环境规划：政策法规与标准条文卡片包（Vibe Coding 实训数据源）



> **【使用说明】**
> 本文件提供工业园区二氧化碳捕集利用与封存（Carbon Capture, Utilization, and Storage, CCUS）耦合绿氢合成绿色甲醇（Power-to-Methanol, PtM）系统在环境规划方案编制中必须遵循的四项国内外核心政策法规与技术标准条文。
> 请阅读条文内容，提取其中的**逻辑判定条件（If-Else）、定量红线阈值（Thresholds）与成本/补贴修正项（Cost Modifiers）**，通过 AI 编程辅助工具进行编程实现，将其转化为 `task2_policy_vibe_engine.py` 中的合规评估与平准化成本修正函数。



## 一、 核心专业术语中英文全称对照表

在编写代码注释与撰写《环境规划与管理报告》时，首次出现的专业缩写必须标注中英文全称：

* **MFA**: Material Flow Analysis（物质流分析）
* **EFA**: Energy Flow Analysis（能量流分析）
* **LCA**: Life Cycle Assessment（全生命周期评价）
* **TEA**: Techno-Economic Analysis（技术经济分析）
* **GWP**: Global Warming Potential（全球变暖潜势，基准时间尺度 100 年，单位：$\text{kg CO}_2\text{e/t}$）
* **LCOM**: Levelized Cost of Methanol（平准化甲醇成本，单位：$\text{元/t}$）
* **LCOH**: Levelized Cost of Hydrogen（平准化氢气成本，单位：$\text{元/kg}$）
* **LCOC**: Levelized Cost of Carbon（平准化碳捕集成本，单位：$\text{元/t CO}_2$）
* **MAC**: Marginal Abatement Cost（边际减排成本，单位：$\text{元/t CO}_2\text{e}$）
* **PEM**: Proton Exchange Membrane（质子交换膜电解水制氢）
* **ALK**: Alkaline Electrolyzer（碱性电解水制氢）
* **CAPEX**: Capital Expenditure（固定资产资本支出，单位：$\text{亿元}$ 或 $\text{元/t}$）
* **OPEX**: Operating Expenditure（运行维护支出，单位：$\text{万元/年}$ 或 $\text{元/t}$）
* **CRF**: Capital Recovery Factor（资本回收系数）
* **WACC**: Weighted Average Cost of Capital（加权平均资本成本，折现率）
* **RED III**: Renewable Energy Directive III（欧盟《可再生能源指令》第三版，Directive (EU) 2023/2413）
* **RFNBO**: Renewable Fuels of Non-Biological Origin（非生物源可再生燃料）
* **ISCC EU**: International Sustainability and Carbon Certification EU（欧盟国际可持续发展与碳认证体系）
* **ETS**: Emissions Trading System（碳排放权交易体系）
* **CCER**: China Certified Emission Reduction（国家核证自愿减排量）
* **MRV**: Monitoring, Reporting, and Verification（可测量、可报告、可核查体系）
* **PDCA**: Plan-Do-Check-Act（策划-实施-检查-改进动态管理循环）



## 二、 四大政策法规与技术标准定量条文卡片

### 卡片 1：欧盟《可再生能源指令》(RED III) 与国际绿色航运燃料准入条文

* **法规出处**：Directive (EU) 2023/2413 (RED III) 及其授权法案 (Delegated Regulation (EU) 2023/1184, (EU) 2023/1185)。
* **适用对象**：拟外销欧洲市场或加注国际远洋船舶的电制绿色甲醇（RFNBO 属性）。
* **定量判定与核算规则**：
  1. **化石燃料基准线**：欧盟统一设定的非生物源车用与航运燃料化石基准碳强度为 $E_F = 94.0\text{ g CO}_2\text{e/MJ}$。以精甲醇低位发热量 $19.9\text{ MJ/kg}$（即 $19,900\text{ MJ/t}$）折算，对应单吨甲醇的化石碳排放基准为：
     $$
     \text{GWP}_{\text{fossil\_ref}} = 94.0 \times 10^{-3}\text{ kg CO}_2\text{e/MJ} \times 19,900\text{ MJ/t} = \mathbf{+1,870.6\text{ kg CO}_2\text{e/t 甲醇}}
     $$
  2. **温室气体减排强制阈值**：生产过程必须实现相对于化石基准至少 **$70.0\%$ 的温室气体减排量**，且生产用电的清洁可再生电力消纳比例 $f_{\text{green}}$ 不得低于 **$80.0\%$**。项目全生命周期净碳足迹必须满足：
     $$
     \text{GWP}_{\text{net}} \le 1,870.6 \times (1 - 70.0\%) = \mathbf{+561.18\text{ kg CO}_2\text{e/t 甲醇}}
     $$
  3. **认证状态与经济效益修正**：
     * 若同时满足 $\text{GWP}_{\text{net}} \le +561.2\text{ kg CO}_2\text{e/t}$ 与 $f_{\text{green}} \ge 80.0\%$，系统判定为获得欧盟非生物源可再生燃料认证资格（`RED_III_RFNBO_Certified`），享受国际绿色航运长周期离线采购协议溢价补贴：
       $$
       \Delta \text{Cost}_{\text{subsidy}} = \mathbf{-1,200.0\text{ 元/t 甲醇}}
       $$
     * 若未达到上述任一条件，认证补贴为 **$0.0\text{ 元/t}$**。

### 卡片 2：国家碳排放权交易体系（ETS/CCER）与高耗能高排放项目环境准入红线

* **法规出处**：生态环境部《碳排放权交易管理暂行条例》、国家发展改革委等部门《高耗能行业重点领域能效标杆水平和基准水平》及各省《固定资产投资项目节能审查办法》。
* **适用对象**：境内工业园区新建、改扩建化工与能源系统碳排放合规性审查。
* **定量判定与核算规则**：
  1. **国内行业基准与碳价设定**：以国内主流煤制甲醇（Coal-to-Methanol, CtM）行业平均碳排放水平作为对照基准线，取 $\text{GWP}_{\text{bench}} = \mathbf{+2,600.0\text{ kg CO}_2\text{e/t 甲醇}}$。全国碳市场基准结算碳价取 $P_{\text{carbon}} = \mathbf{100.0\text{ 元/t CO}_2\text{e}}$（即 $0.10\text{ 元/kg CO}_2\text{e}$）。
  2. **三级阶梯管控与成本修正机制**：
     * **第一级：净负碳示范级（$\text{GWP}_{\text{net}} \le 0.0\text{ kg CO}_2\text{e/t}$）**：项目全生命周期实现温室气体净固定。相对煤制甲醇基准的减排量 $\Delta \text{GHG} = (2,600.0 - \text{GWP}_{\text{net}}) / 1,000.0\text{ (t CO}_2\text{e/t)}$ 可向主管部门申请开发为国家核证自愿减排量（CCER），享受 **$1.2\text{ 倍}$** 负碳技术示范激励系数，碳收益直接抵扣生产成本：
       $$
       \Delta \text{Cost}_{\text{carbon}} = -1.2 \times \frac{2,600.0 - \text{GWP}_{\text{net}}}{1,000.0} \times P_{\text{carbon}}
       $$
     * **第二级：常规减排达标级（$0.0 < \text{GWP}_{\text{net}} \le 2,600.0\text{ kg CO}_2\text{e/t}$）**：项目相对于基准实现正向碳减排，结余碳配额按 $1.0\text{ 倍}$ 基准碳价进行市场化交易：
       $$
       \Delta \text{Cost}_{\text{carbon}} = -1.0 \times \frac{2,600.0 - \text{GWP}_{\text{net}}}{1,000.0} \times P_{\text{carbon}}
       $$
     * **第三级：反向碳增排否决级（$\text{GWP}_{\text{net}} > 2,600.0\text{ kg CO}_2\text{e/t}$）**：由于生产用电碳排放因子过高导致项目全生命周期碳排放超出煤制工艺基准（触发“电氢利用的间接增排”），项目触发高耗能、高排放项目环境影响评价一票否决红线，标记为 **`Redline_Vetoed`（环境准入一票否决）**。对于超额排放部分，必须按照 **$2.0\text{ 倍}$** 惩罚性碳价购买配额，并对全厂用电加收 **$+0.10\text{ 元/kWh}$** 的惩罚性阶梯电价：
       $$
       \Delta \text{Cost}_{\text{carbon}} = +2.0 \times \frac{\text{GWP}_{\text{net}} - 2,600.0}{1,000.0} \times P_{\text{carbon}} + 0.10 \times E_{\text{total}}
       $$

### 卡片 3：工业取水定额、超定额累进税率与水资源承载力红线

* **法规出处**：水利部、国家发改委《工业取水定额》标准及财政部、税务总局、水利部《水资源税改革试点实施办法》。
* **适用对象**：重点缺水地区、西北干旱荒漠地区化工园区取水许可与水资源论证。
* **定量判定与核算规则**：
  1. **系统取水总量函数关系**：生产 1 t 精甲醇的 PEM 电解槽除盐纯水理论净消耗为 $1.385\text{ t}$（扣除精馏副产物冷凝生成水闭环循环利用量 $0.575\text{ t}$ 后）。此外，循环冷却系统蒸发散失量与反应分离回路的循环气压缩功及冷凝换热负荷正向相关，随驰放分流比 $r_{\text{purge}}$ 的降低而上升，吨产品综合取水量模型为：
     $$
     W_{\text{total}} = 1.385 + 0.008 \times \left(\frac{0.010}{r_{\text{purge}}}\right) \quad (\text{t 水 / t 甲醇})
     $$
  2. **阶梯计税与工程技改红线**：
     * 园区核定的单位产品基准取水定额为 $W_{\text{quota}} = \mathbf{1.400\text{ t 水 / t 甲醇}}$。定额以内正常计征水资源税，税额基准为 **$5.0\text{ 元/t 水}$**。
     * 若 $1.400 < W_{\text{total}} \le 1.425\text{ t/t}$，定额内按基准税率计征，超出定额部分依法加收 **$3.0\text{ 倍}$（$15.0\text{ 元/t 水}$）** 的超定额累进水资源税：
       $$
       \Delta \text{Cost}_{\text{water}} = 1.400 \times 5.0 + (W_{\text{total}} - 1.400) \times 15.0
       $$
     * 若 $W_{\text{total}} > 1.425\text{ t/t}$，触发区域水资源刚性约束承载力红线。规划方案必须强制配套全厂闭式循环风冷节水系统，产生固定资产追加投资年金摊销 **$\Delta \text{Cost}_{\text{water\_retrofit}} = +85.0\text{ 元/t 甲醇}$**；实施风冷技改后，吨甲醇实际外取水量强制降至 $1.390\text{ t/t}$，按基准税率计税：
       $$
       \Delta \text{Cost}_{\text{water}} = 1.390 \times 5.0 + 85.0 = \mathbf{91.95\text{ 元/t 甲醇}}
       $$

### 卡片 4：大气污染物排放标准、二次逸散环保税与清洁生产准入底线

* **法规出处**：《中华人民共和国环境保护税法》及国家生态环境标准《大气污染物综合排放标准》(GB 16297)、《石油化学工业污染物排放标准》(GB 31571)。
* **适用对象**：碳捕集吸收剂再生气液逸散、合成未反应气末端处置环境监管。
* **定量判定与核算规则**：
  1. **次生污染源解析**：

     * 污染源一：二氧化碳烟气单乙醇胺（MEA）化学吸收与热解吸再生系统排气中携带的微量挥发性有机胺（VOCs）；
     * 污染源二：合成反应回路驰放尾气（Purge Gas，流量 $M_{\text{purge}} = 46.0 \times \frac{r_{\text{purge}}}{0.010}\text{ kg/t 甲醇}$）输送至园区自备供热锅炉掺烧过程中，因含氮化合物及高温燃烧生成的氮氧化物（$\text{NO}_x$）。
  2. **环保税与末端治理运维成本核算**：

     $$
     \Delta \text{Cost}_{\text{env\_tax}} = 12.0 + 18.5 \times \left(\frac{r_{\text{purge}}}{0.010}\right) \quad (\text{元/t 甲醇})
     $$

     该项费用包含尾气脱硝催化剂消耗、水洗塔循环除胺吸收液定期处理以及向税务部门申报缴纳的相应大气污染物环境保护税。
  3. **清洁生产物料转化利用率红线**：若为规避循环压缩功而无序放大驰放分流比（$r_{\text{purge}} > 0.035$，即驰放比例超过 $3.5\%$），全系统总碳转化利用率将跌破 **$88.0\%$**，不符合国家《清洁生产评价指标体系（煤炭石油化学工业）》中规定的碳素高效利用基准，规划方案直接标记为 **`Redline_Vetoed`（清洁生产不合规一票否决）**。



## 三、 Vibe Coding 提示词与代码构建参考

在运用代码生成工具构建量化引擎时，请参考使用下列规范的结构化提示词输入：

```text
请阅读环境规划与管理政策条文卡片包（policy_clauses_pack.md），编写 Python 评估模块 task2_policy_vibe_engine.py。
模块须实现函数 evaluate_policy_compliance(gwp_net, base_lcom, e_total_kwh, f_green, r_purge)，严格遵循以下核算逻辑：
1. 欧盟 RED III 判定：当 gwp_net <= 561.2 且 f_green >= 0.80 时，赋予补贴 -1200.0 元/t，标记具备 RED III 认证资格；否则补贴为 0。
2. 国内碳市场判定：基准为 2600.0 kg CO2e/t，碳价 100.0 元/t。若 gwp_net <= 0，获得 1.2 倍 CCER 激励；若 0 < gwp_net <= 2600.0，获得 1.0 倍配额收益；若 gwp_net > 2600.0，触发一票否决（Redline_Vetoed），执行 2.0 倍惩罚碳价并对全厂电耗征收 0.10 元/kWh 惩罚阶梯电价。
3. 取水定额判定：基准定额 1.400 t/t，基准税率 5.0 元/t。若 1.400 < w_total <= 1.425，超定额部分按 15.0 元/t 征收；若 w_total > 1.425，强制追加 85.0 元/t 空冷技改年金摊销，实际取水修正为 1.390 t/t 计税。
4. 次生环保税与清洁生产底线：按公式 12.0 + 18.5 * (r_purge / 0.010) 计算环保税与末端运维费。若 r_purge > 0.035，直接触发一票否决（Redline_Vetoed）。
5. 综合状态输出：若触发任何一票否决项，状态标记为 'Redline_Vetoed'；否则若满足欧盟认证，标记为 'RED_III_RFNBO_Certified'；否则标记为 'Domestic_Compliant'。
6. 计算政策修正后平准化成本 lcom_policy_adjusted 与边际减排成本 mac_policy_adjusted（以煤制甲醇价格 2500.0 元/t 与碳排 2600.0 kg/t 为参考）。
7. 在代码文件末尾编写单元测试，对标准自检表中的三个典型工况进行验证。
```



## 四、 单元测试基准自检表

学生构建的代码模型必须通过下列三组代表性工程工况的数值校验：

| 校验工况说明                           | 输入向量 `(gwp_net, base_lcom, e_total_kwh, f_green, r_purge)` | 预期合规状态 `compliance_status` | 预期国际认证溢价 (元/t) | 预期碳市场调节费用 (元/t) | 预期总平准化成本 (元/t) |
| :------------------------------------- | :--------------------------------------------------------------- | :--------------------------------: | :---------------------: | :-----------------------: | :---------------------: |
| **工况 1：高比例绿电基地情景**   | `(-1044.1, 2862.3, 10826.0, 1.00, 0.010)`                      |    `RED_III_RFNBO_Certified`    |      `-1200.00`      |        `-437.29`        |       `1262.51`       |
| **工况 2：多能互补过渡情景**     | `(+800.0, 4200.0, 10826.0, 0.65, 0.015)`                       |       `Domestic_Compliant`       |        `0.00`        |        `-180.00`        |       `4089.47`       |
| **工况 3：高碳电网反向增排情景** | `(+4531.3, 7193.0, 10826.0, 0.00, 0.010)`                      |         `Redline_Vetoed`         |        `0.00`        |       `+1468.86`       |       `8706.36`       |

*注：工况 1 中，碳市场调节收益为 $-1.2 \times (2,600.0 - (-1,044.1))/1,000.0 \times 100.0 = -437.29\text{ 元/t}$；取水费用为 $1.393 \times 5.0 = 6.965\text{ 元/t}$；环保税为 $12.0 + 18.5 = 30.5\text{ 元/t}$；净平准化成本为 $2,862.3 - 1,200.0 - 437.29 + 6.965 + 30.5 = 1,262.48\text{ 元/t}$。*
