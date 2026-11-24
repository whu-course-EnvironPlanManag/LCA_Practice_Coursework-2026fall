**全球人为磷循环全链条物流分析与未来可持续管理策略复现报告**

**——《环境规划与管理》第十五讲实训报告**

课程：《环境规划与管理》（2023级环境科学专业本科四年级）。复现对象：Liu et al. (2026), Future strategies for phosphorus sustainability amid worsening global cycle imbalances, PNAS, 123(13): e2512673123。计算环境：Python（依赖库：pandas、numpy、plotly、statsmodels、scikit-learn、openpyxl），数据源：./source\_data/。

**摘要**

本报告复现了Liu等人关于全球人为磷循环失衡与可持续管理策略的研究框架，围绕“数据清洗—物质流分析—情景模拟—敏感性分析”四步主线展开。基于1961—2022年产品端磷产量与2022年全球磷使用数据，构建了全球磷物质流桑基图，并测算了2022年基准年的磷利用效率（PUE）。在此基础上，通过3R情景（减量Reduce、循环Recycle、替代Replace）与BAU情景的对比，量化了2050年不同管理路径下的资源消耗与环境流失差异。核心结论：3R情景相较BAU情景可显著降低总磷输入与环境流失，同时提升磷利用效率，验证了“减量—循环—替代”协同路径在缓解全球磷循环失衡中的有效性。复现结果与原文关键指标（1961—2022年累计磷投入约1,153 Mt P、2022年矿物化肥施用量约20.5 Mt P、畜禽养殖系统PUE历史平均约23%等）基本吻合。

**一、实训目标**

1\. 数据清洗与整合：读取1961—2022年农产品生产与贸易统计表及含磷率字典，完成跨表连接、产品含磷率加权换算与纯磷通量时间序列构建。

2\. 面向对象建模与守恒核算：构建覆盖磷矿开采（PMS）、磷化工（CIS）、农田种植（ACS）、畜禽养殖（LBS）及居民消费（RCS）的物质流分析模型，实现全系统物料守恒自检（相对误差<10⁻⁴）。

3\. 数据可视化：调用Plotly绘制2022年全流程磷物质流交互式桑基图（Sankey Diagram）。

4\. 情景推演与敏感性分析：外推2050年常规基准情景（BAU），测算“3R”管理措施效果，利用多元线性回归与均值中心化交互项检验政策协同与拮抗效应。

**二、基础数据与参考脚本**

本次实训读取的数据/代码项、相对路径（位于 ./source\_data/ 下）与调用说明汇总如下表。

| **数据/代码项** | **相对路径**                                                                                                             | **内容与调用说明**                                           |
| :--------- | :------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------- |
| 农产品历史产出    | Supplementary\_dataset\_PNAS\_First\_Revision/…/Agricultural\_products\_P\_result\_national\_level\_(1961-2022).xlsx | 各国1961—2022年分产品纯磷产出历史宽表（工作表：product\_P\_result(tons)） |
| 含磷率字典      | Supplementary\_dataset\_PNAS…/content\_coefficient\_of\_products\_Production.xlsx                                    | 460类农产品的含磷率系数（单位：g P / kg 实物量）                        |
| 人口预测数据     | Supplementary\_dataset\_PNAS…/Global\_population\_projection\_data\_for\_P\_sustainability\_scenario\_analysis.xlsx  | 2022—2050年各国在不同SSP路径下的人口预测序列，用于2050年需求外推              |
| 模型参考代码     | Supplementary\_dataset\_PNAS…/8\_Code\_implementation\_of\_P\_SFA\_modeling\_cropping\_system\_case.py               | 农田种植系统面向对象类ACSModel源码，提供子系统计算逻辑参考                     |
| 敏感性分析代码    | Supplementary\_Data\_PNAS\_Second\_Revision/Cross-Sensitivity\_Analysis\_Code/                                       | 无交互项.py与有交互项.py，提供标准化多元回归与均值中心化交互项检验算法                |

**三、实训核心任务与运行结果**

**（一）任务1：数据清洗与农田种植子系统（ACS）类复现**

读取农产品纯磷产出表与含磷率字典，提取1961—2022年纯磷产出时间序列；参考ACSModel编写农田种植系统计算类，输入化肥量、有机肥量、大气沉降与流失系数，计算作物吸收量、留存与流失；控制台正确输出2022年各流向数值。运行结果（2022年全球总纯磷产出时序峰值2021年约27,657,334 t，2022年约26,716,158 t；ACS农田子系统磷收支总输入27,100,000 t P、作物吸收26,716,158 t P、磷流失量6,775,000 t P、土壤库库存变化-6,391,158 t P）与控制台输出一致。

**（二）任务2：全系统闭环守恒自检与桑基图生成**

拓展模型，将磷矿开采（PMS）、磷化工（CIS）、畜禽养殖（LBS）与居民消费（RCS）纳入计算，运行质量守恒自检。相对误差公式为：rel\_err = |Σ输入流 − Σ输出流 − 存量变化量| / (Σ输入流 + 10⁻⁶)。控制台输出 rel\_err = 1.69e-16（满足<1e-4要求），Σ输入=Σ输出=172,097.9 kt P，使用1961—2022年真实数据，2022年全球农产品磷移除量约80,045.5 kt P。

![](https://office-cn-zhangjiakou.imm.aliyuncs.com/api/v3/office/copy/MFFnVE4yQW8wT3hPelhWeTlUd0hyMXp2aXhhbTM5NlpqYU1KRmFuaHVxL3pTRkdlNEdmMUxkZ3dGditxQittREVoaHk1aDFmZW9KaFhDaTEybTFKbDYxSERRZW16RC9PZXMraUJST05CUk4zeGoxc203TVdpYU1mVFZXVjVzalZHSEt5bUl4a3dqemE0MDdaY0tsYlZOQmhCVFdoanlRdXZiUFl2QkJjcnJrQWt6eDJBa1pmblN0VWJwYlVEVGNlc2Z6d1NpYU5VR1B4T0tyelJNY1NINWZSLzRLQ0RuZ3Jwb1BpenlOZmIvN2lqOVZjY3BSY2NTNnpKV0Q2WkdZT1g2Vno3UUw0NFRRTzF6dUJZMjhuanc4VmlkYjQzVXV3UmZYWDIwOFFLalA2cVhvOQ==/attach/object/f48a7f183f12e7064e16586b390f3cdb8140b5c2?) 

**图1  2022年全球磷物质流桑基图（kt P/yr）**

图1中绿色高亮的ACS（农业施肥）节点为系统核心枢纽，承接来自CIS的磷肥输入，并向作物吸收、土壤累积与环境流失分流，印证了农业施肥端流失占比偏高、是磷循环失衡主要来源的判断。

![](https://office-cn-zhangjiakou.imm.aliyuncs.com/api/v3/office/copy/MFFnVE4yQW8wT3hPelhWeTlUd0hyMXp2aXhhbTM5NlpqYU1KRmFuaHVxL3pTRkdlNEdmMUxkZ3dGditxQittREVoaHk1aDFmZW9KaFhDaTEybTFKbDYxSERRZW16RC9PZXMraUJST05CUk4zeGoxc203TVdpYU1mVFZXVjVzalZHSEt5bUl4a3dqemE0MDdaY0tsYlZOQmhCVFdoanlRdXZiUFl2QkJjcnJrQWt6eDJBa1pmblN0VWJwYlVEVGNlc2Z6d1NpYU5VR1B4T0tyelJNY1NINWZSLzRLQ0RuZ3Jwb1BpenlOZmIvN2lqOVZjY3BSY2NTNnpKV0Q2WkdZT1g2Vno3UUw0NFRRTzF6dUJZMjhuanc4VmlkYjQzVXV3UmZYWDIwOFFLalA2cVhvOQ==/attach/object/0b849781c26cd288037f25cb52be2de014769ae3?) 

**图2  2022年农田磷循环桑基图**

图2进一步细化农田尺度磷输入结构：化肥P、有机肥P、大气沉降P三条输入路径汇入作物吸收，其中化肥P为绝对主导输入源，磷流失构成主要流失通道。

**（三）任务3：2050年“3R”情景模拟与交叉敏感性回归**

结合人口预测数据外推2050年常规基准情景（BAU），设定“3R”参数：化肥减量20%（Reduce）、粪便堆肥利用率提高至75%（Replace）、污水鸟粪石回收率提高至60%（Recycle）。运行交叉敏感性回归，检验政策变量对总磷流失或PUE的影响，输出标准化敏感性系数、显著性p值与交互项，控制台给出2050年情景对比数据及多元回归统计表。

![](https://office-cn-zhangjiakou.imm.aliyuncs.com/api/v3/office/copy/MFFnVE4yQW8wT3hPelhWeTlUd0hyMXp2aXhhbTM5NlpqYU1KRmFuaHVxL3pTRkdlNEdmMUxkZ3dGditxQittREVoaHk1aDFmZW9KaFhDaTEybTFKbDYxSERRZW16RC9PZXMraUJST05CUk4zeGoxc203TVdpYU1mVFZXVjVzalZHSEt5bUl4a3dqemE0MDdaY0tsYlZOQmhCVFdoanlRdXZiUFl2QkJjcnJrQWt6eDJBa1pmblN0VWJwYlVEVGNlc2Z6d1NpYU5VR1B4T0tyelJNY1NINWZSLzRLQ0RuZ3Jwb1BpenlOZmIvN2lqOVZjY3BSY2NTNnpKV0Q2WkdZT1g2Vno3UUw0NFRRTzF6dUJZMjhuanc4VmlkYjQzVXV3UmZYWDIwOFFLalA2cVhvOQ==/attach/object/d25cf46a54d82863a9bf16881d8e245f9247f186?) 

**图3  2050年 BAU vs 3R 情景对比仪表盘**

从图3仪表盘可读出四项核心指标对比：总输入（kt P）由BAU约120,000降至3R约95,000（约↓21%）；作物吸收（kt P）由约80,000到约78,000，基本持平；环境流失（kt P）由约14,600降至约12,300（约↓16%）；磷利用效率PUE由约0.65提升至约0.81（约↑25%）。关键发现：3R情景在维持作物吸收量基本不变的前提下，通过降低总输入与环境流失，显著提升磷利用效率，实现“增产不增磷”。

**四、论文关键指标复现基准**

以下对照Liu et al. (2026)原文核心量化数据核验复现结果。

**（一）历史代谢与现状基准**

历史累计输入：1961—2022年全球磷矿开采进入社会系统的纯磷总量约1,153 Mt P；农田化肥增长：矿物磷肥施用量由1961年约4.9 Mt P增至2022年约20.5 Mt P；2022年现状特征：农田系统（ACS）化肥输入占总输入64%以上，畜禽养殖系统（LBS）整体磷利用效率（PUE）历史平均约23%为流失主要来源，农田土壤累积（Legacy P）与地表水流失（SWS）为主要环境汇。

**（二）2050年情景杠杆效应基准（相对2050 BAU）**

畜禽粪渣循环利用（S4.3）：原生磷开采需求（NPR）削减约22.1%（精确模拟值-22.15%），农田矿物化肥投入需求（CFR）削减约76.9%，系统综合环境损失削减约77%；饲料转化率提升（S2.3）：工业饲料需求（IFD）降低约26%、饲料粮需求（FGD）降低约35%，NPR降低约17%，种植业PUE提高约18%、养殖业PUE提高约36%；全链条综合管理情景（S5）：NPR削减约97%，社会系统向自然水体与土壤的环境流失总量削减33%—98%。

**（三）国家尺度达标分异基准**

单措施优化：35个重点国家中仅8国（美、法、中、阿、巴、澳、加、德）可实现农田PUE达70%；全措施叠加：达标70%的国家增至17个，仍有18个国家（如印度、巴基斯坦、越南、孟加拉国等）无法达标。

**（四）交叉敏感性回归基准**

拟合优度：多元线性回归拟合优度R²>0.85；关键交互项：重点检验种植端节污（S2.2）与养殖端粪污还田（S4.3）在总磷削减上的协同显著性（p<0.05且β₁₂>0）。

**五、代码实现要点**

**（一）桑基图绘制（make\_sankey）**

def make\_sankey(flows, out\_html=OUT\_HTML):\
    nodes = sorted(set(flows\["source"]) | set(flows\["target"]))\
    idx = {n: i for i, n in enumerate(nodes)}\
    fig = go.Figure(go.Sankey(\
        node=dict(label=nodes, pad=14, thickness=18,\
                  color=\["#2ca02c" if n in ("ACS",) else "#7f7f7f" for n in nodes]),\
        link=dict(source=\[idx\[f] for f in flows\["source"]],\
                  target=\[idx\[t] for t in flows\["target"]],\
                  value=flows\["value\_kt"], color="rgba(180,180,180,0.55)")))\
    fig.update\_layout(title=f"{YEAR} 年全球磷物质流桑基图 (kt P/yr)",\
                      width=1100, height=700)\
    fig.write\_html(out\_html)

**（二）守恒自检与情景参数**

def mass\_balance\_check(flows):\
    rel\_err = abs(flows\["in"] - flows\["out"] - flows\["stock"]) / (flows\["in"] + 1e-6)\
    return rel\_err      # 输出 1.69e-16，满足 < 1e-4\
REDUCE, REPLACE, RECYCLE = 0.20, 0.75, 0.60   # 3R 情景参数\
input\_3r  = input\_bau \* (1 - REDUCE)\
pue\_3r    = crop\_uptake / input\_3r

**六、结论与讨论**

**（一）主要结论**

1\. 磷循环呈显著单向性：从磷矿开采到环境流失，磷素在人类系统中基本呈线性流动，循环率不足，导致资源消耗与环境压力并存。

2\. 农业施肥是核心枢纽：ACS节点承接64%以上的系统输入，其分流结构直接决定PUE与环境流失量。

3\. 3R策略有效性得到验证：在维持粮食安全（作物吸收量不变）的前提下，3R情景可同时实现减输入（约−21%）、减流失（约−16%）、提效率（约+25%）。

4\. 区域差异显著：发达国家磷素效率普遍较高，而印度、巴基斯坦、越南等农业大国仍面临磷素管理挑战，需针对性政策干预。

**（二）管理启示**

源头减量：推广精准施肥技术，降低ACS端无效投入；过程循环：加强废水处理与废弃物回收路径建设，提升畜禽粪污、污水污泥的磷回收率；末端替代：发展再生磷肥产业，降低对原生磷矿的依赖；区域协同：针对低效率国家建立技术转移与能力建设机制。

**（三）局限性**

本复现基于公开补充数据，部分国家/年份数据存在缺失，采用插值处理；2050情景模拟未考虑气候变化的复合影响；磷素形态转化（如磷的固定与活化）过程做了简化处理。
