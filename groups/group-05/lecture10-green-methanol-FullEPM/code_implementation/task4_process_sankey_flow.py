from pathlib import Path
import sys,json
import numpy as np,pandas as pd
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code_implementation'))
from task3_pareto_frontier_decision import simulate_park_methanol_system,extract_pareto_frontier_and_anchors
from task2_policy_vibe_engine import evaluate_policy_compliance as policy
from task1_mfa_recycle_solver import solve_mfa_balance
F=ROOT/'figures_output'; F.mkdir(exist_ok=True);R=ROOT/'report';R.mkdir(exist_ok=True)
df=pd.DataFrame([simulate_park_methanol_system(f,r) for f in np.linspace(0,1,60) for r in np.linspace(.004,.045,50)])
p,a=extract_pareto_frontier_and_anchors(df);b=a['Anchor_B_Knee_Point']; f=b.f_green;r=b.r_purge;s=.960/(b.eta_carbon/100)
co=1423*s;h=198*s;w=575.;o=1584*s;water=1.385+.00008/r
crf=.08*1.08**20/(1.08**20-1);storage=680*f**2.8;rec=45*max(0,(.01/r)**.8-1)
# 课程总投资9.15亿元；制氢与缓冲余额分配为课程预算假设。
cap=np.array([9.15-1.10-1.20-.65-.97,1.10,1.20,.65,.97])*1e8
assert abs(cap.sum()-9.15e8)<1e-6
el=np.array([h*52,255*s,155*(.01/r)**.65,120,0]);price=.18*f+.42*(1-f)
ops=el*price+np.array([0,co/1000*260,0,65,285]); pol=policy(b.gwp_net,b.base_lcom,b.e_total_kwh,f,r);adj=pol['policy_breakdown'];netop=ops.sum()-316.8*s+sum(adj.values())
budget_base=cap.sum()*crf/1e5+ops.sum()-316.8*s
budget_policy=policy(b.gwp_net,budget_base,b.e_total_kwh,f,r)
budget_lcom=budget_policy['lcom_policy_adjusted'];budget_mac=budget_policy['mac_policy_adjusted']
assert abs(cap.sum()*crf/1e5+netop-budget_lcom)<1e-7
assert abs(budget_base-b.base_lcom-(cap.sum()*crf/1e5-835.2-storage-rec))<1e-7
(F/'B_budget_evaluation.json').write_text(json.dumps(dict(capex_yuan=cap.sum(),capital_annuity_per_t=cap.sum()*crf/1e5,base_lcom=budget_base,adjusted_lcom=budget_lcom,mac=budget_mac,selection='B selected by original course objective; fixed-budget evaluation only',allocation_assumption='Hydrogen and buffer assigned residual 5.23e8; not equipment quotation'),indent=2),encoding='utf-8')
checks=[]
for inp,expected in [((-1044.1,2862.3,10826,1,.01),1262.473),((800,4200,10826,.65,.015),4066.7016666667),((4531.3,7193,10826,0,.01),8699.325)]:
    z=policy(*inp);assert abs(z['lcom_policy_adjusted']-expected)<1e-6;checks.append(z['lcom_policy_adjusted'])
assert policy(2600,4000,10826,.8,.035)['compliance_status']!='Redline_Vetoed'
assert policy(2600.001,4000,10826,.8,.035)['compliance_status']=='Redline_Vetoed'
assert policy(0,4000,10826,.8,.001)['policy_breakdown']['water_cost_mod']==91.95
for _,row in p.iterrows():
    v=df[df.compliance_status!='Redline_Vetoed']; assert not (((v.gwp_net<=row.gwp_net)&(v.lcom_policy_adjusted<=row.lcom_policy_adjusted))&((v.gwp_net<row.gwp_net)|(v.lcom_policy_adjusted<row.lcom_policy_adjusted))).any()
m=solve_mfa_balance();(F/'validation.json').write_text(json.dumps({'policy_totals':checks,'mfa':m,'scenario_count':len(df),'pareto_count':len(p),'capex_yuan':cap.sum(),'gross_opex_yuan_year':ops.sum()*1e5,'net_opex_yuan_year':netop*1e5},indent=2),encoding='utf-8')
plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans'];plt.rcParams['axes.unicode_minus']=False
fig,ax=plt.subplots(figsize=(14,7));ax.set(xlim=(0,14),ylim=(0,7));ax.axis('off')
nodes=[(1.5,5,f'捕集压缩\nCO2 {co*100:.0f} t/a'),(1.5,2.8,f'电解制氢\nH2 {h*100:.0f} t/a'),(5,4,'混合与催化合成\n单程转化率25%'),(8,4,'冷凝分离\n循环分流'),(11.5,4,'双塔精馏\n甲醇100000 t/a'),(8,6,f'循环压缩\nB驰放比 {r:.5f}\n循环基准464000 t/a（r=1%）'),(11.5,1.5,f'水回用 {w*100:.0f} t/a\n经验水量，需工程调和')]
for x,y,t in nodes:ax.text(x,y,t,ha='center',va='center',bbox=dict(boxstyle='round,pad=.7',fc='#e8f2f4',ec='#326278'),fontsize=11)
for i,j in [(0,2),(1,2),(2,3),(3,4),(3,5),(5,2),(4,6),(6,1)]:
 x,y,_=nodes[i];xx,yy,_=nodes[j];ax.annotate('',xy=(xx,yy-.5),xytext=(x,y-.5),arrowprops=dict(arrowstyle='->',color='#326278',connectionstyle='arc3,rad=.12'))
ax.text(.3,.3,f'用电：制氢 {el[0]*1e5/1e8:.3f}、捕集 {el[1]*1e5/1e8:.3f}、循环 {el[2]*1e5/1e8:.3f}、精馏 {el[3]*1e5/1e8:.3f} 亿kWh/a\n副产氧 {o*100:.0f} t/a；取水 {water*1e5:.0f} t/a；经验驰放尾气 {46*r/.01*100:.0f} t/a → 锅炉治理',fontsize=11)
ax.set_title('锚点 B：园区物料与能量拓扑（课程经验模型；箭头不按流量比例）',fontsize=16);fig.tight_layout();fig.savefig(F/'fig1_mfa_process_flow.png',dpi=300);fig.savefig(F/'fig1_mfa_process_flow.svg');plt.close(fig)
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)
anchors=table(['方案','绿电%','驰放%','碳利用率%','GWP kg/t','基础LCOM元/t','净LCOM元/t','MAC元/tCO2e'],[[k.split('_')[1]]+[f'{v:.4f}' for v in [z.f_green*100,z.r_purge*100,z.eta_carbon,z.gwp_net,z.base_lcom,z.lcom_policy_adjusted,z.mac_policy_adjusted]] for k,z in a.items()])
names=['PEM及储能缓冲','捕集压缩','合成及循环增压','精馏与回用水','公用管廊与监测'];loc=['能源岛','烟气源邻近区','化工生产区','水处理邻近区','公用管廊'];owner=['能源公司','热电企业','化工项目公司','水务公司','园区平台公司']
projects=table(['工程','建设内容及规模','性质/位置','等效投资亿元','运行费万元/年','效益','责任主体'],[[f'工程-0{[2,1,3,4,5][i]}',names[i]+['；制氢需求%.2f MW'%(el[0]*1e5/8000/1000),'；CO2 %.0f t/a'%(co*100),'；甲醇10万吨/年','；回水57500 t/a','；全厂计量覆盖'][i],'新建/'+loc[i],f'{cap[i]/1e8:.5f}',f'{ops[i]*10:.2f}',['保障清洁氢供给','回收碳源','提高碳利用率','降低外取水','可追溯核算'][i],owner[i]] for i in [1,0,2,3,4]])
text=f'''# 工业园区10万吨/年绿色甲醇环境规划与管理方案报告

第5组｜2026年秋季《环境规划与管理》课程｜第十讲案例2

## 摘要
本方案针对煤化工园区的工业二氧化碳资源化需求，以年产10万吨甲醇为规划规模，开展物质流、能源流、生命周期评价和技术经济联合分析。基于课程给定的电价、排放因子、储能年金和政策情景，对60档绿电比例及50档驰放比例组合进行3000组搜索，排除否决方案后获得{len(p)}个非支配解。采用前沿目标范围归一化的理想点距离最小准则，确定锚点B的绿电比例为{f*100:.2f}%，驰放比例为{r*100:.3f}%，课程经验碳利用率为{b.eta_carbon:.2f}%。标准模型推荐方案净碳足迹为{b.gwp_net:.2f} kg CO2e/t，基础成本为{b.base_lcom:.2f}元/t，政策调整后成本为{b.lcom_policy_adjusted:.2f}元/t，边际减排成本为{b.mac_policy_adjusted:.2f}元/t CO2e。五项重点工程规划投资合计{cap.sum()/1e8:.4f}亿元，未扣收益运行支出为{ops.sum()*10:.2f}万元/年；按9.15亿元预算重算的B净成本为{budget_lcom:.2f}元/t。方案以清洁电力长协、氧气消纳及有条件的绿色溢价构成收入保障，并设置分项计量、异常联锁及年度复核机制。独立化学计量核验发现教学数据不能同时满足标称循环比、碳利用率及全部物流组分约束，故将守恒模型与经验规划模型分别披露。负值碳足迹仅代表课程边界下的信用核算结果，不等同于永久碳移除或实际国际认证。

## 术语
MFA（Material Flow Analysis）：物质流分析；LCA（Life Cycle Assessment）：生命周期评价；TEA（Techno-Economic Analysis）：技术经济分析；GWP（Global Warming Potential）：全球变暖潜势；LCOM（Levelized Cost of Methanol）：平准化甲醇成本；MAC（Marginal Abatement Cost）：边际减排成本；PEM（Proton Exchange Membrane）：质子交换膜；CAPEX（Capital Expenditure）：资本支出；OPEX（Operating Expenditure）：运行支出；CRF（Capital Recovery Factor）：资本回收系数；MRV（Monitoring, Reporting and Verification）：监测报告核查；PDCA（Plan-Do-Check-Act）：策划实施检查改进。RED III为欧盟可再生能源指令第三版，RFNBO为非生物源可再生燃料，ETS为碳排放权交易体系，CCER为国家核证自愿减排量。本报告政策数值均为课程情景输入。

## 第1章 现状诊断与基准线
园区以煤化工及配套热电为背景，拟以烟气捕集、清洁电力电解、催化加氢及精馏构成示范系统。材料没有提供全园区煤耗、电耗、烟气流量、污染物实测浓度、土地及水权清单，因此不能将规划需求写成已落实的资源供应。项目前置调查须取得烟气连续流量、CO2浓度、温度及硫氧化物、氮氧化物、颗粒物监测结果，并核定胺吸收前脱硫、除尘、骤冷能力。若烟气CO2质量分数为y、捕集率为q，则年烟气需求为年捕集需求/(yq)，尚无依据赋予y和q实测值。

开篇讨论情景使用煤电0.75、光伏0.04 kg/kWh，电价分别0.32和0.20元/kWh；优化情景使用网电0.550、绿电0.035 kg/kWh及0.42、0.18元/kWh，二者不能混用。开篇临界比例由10826×(0.75−0.71x)−1423≤2600求得x≥{(.75-4023/10826)/.71*100:.4f}%。光伏1200小时与装置8000小时对应15%利用水平，原投资不变时年金单位成本升至6.667倍。连续固定床反应器不能由无储能光伏直接稳定支撑；频繁启停还增加电解设备的动态运行负担，材料不足以定量推算寿命。

## 第2章 多情景预测与规模匹配
设置纯网电、混合电源及全绿电三类情景，统一在3000组网格内比较。锚点B年捕集CO2为{co*100:.2f}吨，氢气{h*100:.2f}吨，经验副产水57500吨，氧气{o*100:.2f}吨，总电量{b.e_total_kwh*1e5/1e8:.5f}亿kWh，政策取水量{water*1e5:.2f}吨/年。基础经验口径r=0.01时，分别为142300吨、19800吨、57500吨、158400吨、10.826亿kWh；净脱盐水138500吨/年与含冷却用水139300吨/年是不同边界。

![图1 工艺拓扑](../figures_output/fig1_mfa_process_flow.png)

按8000小时折算，B制氢电力平均需求{el[0]*1e5/8000/1000:.3f} MW，比130 MW课堂基准高{el[0]*1e5/8000/1000-130:.3f} MW。因此130 MW在8000小时条件下不能满足B产量；若维持130 MW，至少需年等效满负荷运行{el[0]*1e5/130000:.2f}小时。本课程方案将此列为容量匹配差异，建议扩容至不低于上述平均需求并保留调节余量；扩容投资未单独计入经验成本。提出4小时氢缓冲作为设计假设，对应{h*100/8000*4:.3f}吨氢，不作为已完成的设备选型。若全部清洁电量仅由1200小时光伏供应，需要{b.e_total_kwh*1e5*f/1200/1000:.2f} MW光伏等效装机，仍需时序储能或互补电源，年电量平衡不能证明逐时可靠性。

独立核验采用CO2+3H2→CH₃OH+H2O及净逆水煤气反应CO2+H2→CO+H2O，单吨甲醇a=1000/32.042 kmol，净副产CO为1.124 kmol；未反应CO2=(a+1.124)(1−X)/X，补料=反应耗量+r×未反应量。氢气采用同单程消耗率假设，CO稳态循环量为1.124(1−r)/r。所有出口物种独立求得后才计算元素误差。上述假设下基准求解碳利用率{m['eta_carbon']*100:.4f}%，循环质量{m['recycle_kg']:.3f} kg/t，质量循环比{m['recycle_ratio_mass']:.4f}，摩尔循环比{m['recycle_ratio_molar']:.4f}；三元素最大相对误差{max(m['errors'].values()):.3e}。这与经验数据不等同，差异来自净副反应和气体循环假设。

## 第3章 规划目标与指标体系

近期为2027—2028年示范建设阶段，远期为2029—2035年扩展阶段。以下保留课程模板已给目标；模板空白项由本方案提出。B为课堂经验模型推荐点，不将目标值写成已达到的实测结果。

|指标及单位|2026基准|2028近期目标|2035远期目标|性质、核算与B对照|
|---|---|---|---|---|
|CO2捕集量，万吨/年|0|≥14.23|≥70.00|约束；质量流量计；B={co*100/1e4:.4f}，远期需扩产|
|捕集脱除率，%|未给|≥90|≥93|约束；进出口气量浓度；现有数据未核算|
|GWP，kg CO2e/t|2600|≤561.2（拟定）|≤0（拟定）|约束；LCA；B={b.gwp_net:.2f}|
|RED III RFNBO认证达标率，%|0|100|100|约束；第三方核查；模型标签符合，未表示实际获证|
|绿电比例，%|0|≥80（拟定）|≥95|约束；电量计量；B={f*100:.2f}|
|制氢直流电耗，kWh/Nm³|未给|≤4.30|≤4.05|预期；整流柜输出/标况产氢量；52kWh/kg为系统口径，不直接判断直流达标|
|新鲜水取水，t/t|1.650|≤1.390|≤1.350|约束；全厂水表；B={water:.6f}，近期满足、远期不满足|
|副产水回用率，%|0|100|100|约束；回水流量/产水量；模型假设全部回用|
|MEA逃逸，mg/Nm³|未给|≤2.0|≤1.0|约束；吸收塔顶监测；列为治理目标，不推算虚构浓度|
|尾气NOx，mg/Nm³|未给|≤30|≤20|约束；锅炉烟气监测；治理费不等于排放浓度|
|总碳利用率，%|78|≥90（拟定）|≥96|约束；产品碳/输入碳；B={b.eta_carbon:.4f}，近期满足、远期不满足|

远期70万吨捕集目标高于本期10万吨甲醇工程的原料需求，应作为后续扩建目标。原取水函数下限为1.385 t/t，单纯改变驰放比无法实现1.350 t/t；按B还需额外节水{(water-1.35)*1e5:.2f}吨/年。经验碳效率达到96%需r≤1%，近期取水≤1.390需r≥1.6%，现有两变量模型不能同时达到这两个目标。远期提出尾气回收、节水改造及清洁供能扩建方向，不在本期数值中提前记入其效果。

## 第4章 空间落位与工程实施
捕集装置靠近烟气源，电解及缓冲设施布置在能源岛，合成、精馏布置在化工生产区并通过专用管廊连接。避让生态保护红线、居民敏感点及洪涝风险地段；按课堂要求预留涉氢隔离带≥150 m作为初步布局控制，不将该距离视为所有装置通用的法定间距。最终布置仍需场址测绘及专项论证。

{projects}

五项工程规划投资合计{cap.sum()/1e8:.2f}亿元，毛运行支出合计{ops.sum()*10:.2f}万元/年。总额9.15亿元依据课程PR核验表；工程01的1.10亿元、工程03的1.20亿元和工程04的0.65亿元沿用背景手册，工程05按报告模板取0.97亿元，工程02取余额9.15−1.10−1.20−0.65−0.97=5.23亿元。工程02的余额分配为课程预算假设，包含制氢及缓冲配置的规划额度，未按设备报价拆分。运行费按工段电耗分配，捕集服务费归工程01，水处理65元/t归工程04，固定运维285元/t归工程05。政策费用与收入在第5章另列。建设周期见表4-1。

## 第5章 LCA、TEA与多目标决策
课程评价包含上游电力及基础设施，属于原料获取至厂门的简化边界，而非严格门到门。GWP=电耗×混合排放因子+95+1200(r−0.01)−新鲜CO2−氧气信用。纯网电r=0.01时为4531.3 kg/t；全绿电为−1044.09 kg/t。在网电高碳排放因子驱动下，制氢上游间接碳排放增量超过催化加氢直接固定碳汇，导致系统净温室气体排放强度呈现正增长。电解电耗占比高，是间接排放的主要来源。

该信用方法将全部捕集进料作抵扣，未完整反映驰放燃烧和产品最终燃烧，也依赖氧气确实替代外部生产。不得把负值直接解释为永久封存。吸收剂逸散、废液及冷却水转移负担亦应单独监控；本模型没有足够数据计算毒性等其他影响类别。

折现率8%、寿命20年，CRF={crf:.8f}。任务三仍按课程脚手架的835.2元/t基础年金、680f^2.8元/t储能年金和循环增量求取A/B/C，作为课程标准模型结果。B的标准模型基础成本为{b.base_lcom:.4f}元/t、净成本为{b.lcom_policy_adjusted:.4f}元/t。

工程实施预算采用9.15亿元总投资直接计算年金，为{cap.sum()*crf/1e5:.4f}元/t；该预算情景将储能缓冲纳入工程02额度，因此替换标准模型全部资本年金，不另加680元/t。B的毛运行费为{ops.sum():.4f}元/t，氧气销售抵扣{316.8*s:.4f}元/t；据此预算基础LCOM为{budget_base:.4f}元/t。政策四项分别为{adj['red_iii_subsidy']:.4f}、{adj['carbon_cost_mod']:.4f}、{adj['water_cost_mod']:.4f}、{adj['env_tax_mod']:.4f}元/t，预算净LCOM为{budget_lcom:.4f}元/t，MAC为{budget_mac:.4f}元/t CO2e。费用之和与代码输出一致。

9.15亿元是B的课程规划预算约束；下表及图2保留标准模型三锚点，预算成本为同一B工况的追加评价，不声称B在替换后的成本目标下仍为最优点。两种核算分别记录在anchors.csv和B_budget_evaluation.json。

{anchors}

![图2 决策前沿](../figures_output/fig2_pareto_decision_frontier.png)

筛选规则为存在另一方案两目标均不大且至少一项严格较小时删除本方案；先剔除政策否决解。用前沿自身的最小最大值归一化成本和排放，再最小化到(0,0)的欧氏距离。基于目标空间双向极小化距离，标定边际减排成本与平准化综合成本折衷最优的帕累托拐点；实际寻优目标为成本与GWP，MAC为派生评价量。本次A、B、C分别代表最低成本、归一化距离最小和最低碳足迹方案。推荐B只在既定权重、价格与网格下成立，不代表连续空间全局精确解。

电价统一增加0.01元/kWh，B成本上升{b.e_total_kwh*.01:.3f}元/t，MAC增加{b.e_total_kwh*.01/((2600-b.gwp_net)/1000):.3f}元/t CO2e。取消国际溢价，成本增加1200元/t；取消碳收益，成本增加{-adj['carbon_cost_mod']:.3f}元/t。两项收益未落实前应采用相应保守情景评估偿债能力。

## 第6章 制度保障与动态管理
建议资本金30%、绿色贷款70%作为融资测算假设，分别对应{cap.sum()*.3/1e8:.4f}和{cap.sum()*.7/1e8:.4f}亿元；不假设财政资金已获批。电力长协需约定供电量、时序及属性凭证，甲醇采购协议需约定质量和溢价兑现条件，氧气销售协议需匹配实际消纳量。CCER与配额收益不得在同一减排量上重复计算，课堂成本收益不构成登记资格承诺。

MRV系统覆盖绿电及网电电表、CO2和氢气流量计、甲醇及氧气出厂计量、循环与驰放分流计量、取水及回水计量。生产部门每日形成平衡表，环保部门每月汇总碳与水台账，财务部门核对收益兑现，第三方按年核验计量及属性凭证。数据留痕并记录缺失数据替代方法，严禁用差额自动消除实测异常。

涉氢区域配置泄漏报警、通风与紧急切断联锁；CO2管廊设置泄漏监测及疏散路径；胺液及废液实行分区收集、防渗和合规处置。课堂初步控制预留不小于1500 m³应急池，正式容量由消防水及事故液量计算确定。装置防爆等级须按危险区域划分和设备适用性审查，不能以统一等级替代设计。按PDCA每月检查异常、每年复核电力与碳数据、每三年修编规划；若绿电、取水或驰放指标偏离，先调整负荷与供电合同，再复算方案经济性。

## 附录：核算假设与数据差异
1. 1423 kg CO2与1000 kg甲醇按分子量计算碳利用率为{1000/32.042/(1423/44.010)*100:.4f}%，并非严格96%。原数据S08组分合计超过100%；循环气质量、摩尔数和组分也不能同时闭合。不得利用输入减其他输出定义未知元素流，再声称独立守恒通过。
2. 政策三组总成本按公式分别为1262.473、4066.701667、8699.325元/t，材料表格1262.51、4089.47、8706.36存在合计差异；本版断言验证公式值。水资源空冷分支在指定r≥0.004网格内不会触发，另用r=0.001验证。
3. 课程清洁生产规则按r>0.035否决，但经验碳效率在边界附近已低于88%；本版严格执行卡片的r阈值，不能宣称同时满足88%效率红线。较高驰放增加捕集原料信用，导致模型偏向更低净碳足迹，这是信用边界造成的偏差。
4. 经验规划模型保留课程的碳效率、能耗及成本函数；独立MFA采用明确的理想化组分假设。两者尚未构成严格化学计量耦合的工程设计模型，因此图1中经验回用水与尾气只用于课堂规模估算。本报告采用课程经验模型进行规划比较，独立守恒模型用于数据核验，二者不混作同一闭合流程。
5. 数值检查覆盖3000组搜索、全部前沿非支配性、三组政策总成本、关键阈值、独立元素守恒及投资运行费闭合。全部原始工况、前沿、锚点及验证结果存于figures_output。图表为300 DPI PNG，工艺图另附SVG。

## 资料来源
本案例starter_materials中的lecture10_task_manual.md、background_engineering_docs.md、policy_clauses_pack.md、三份CSV、四份脚手架及report_writing_rubric.md。本报告政策参数按课堂情景解释。
'''
from report_format import format_report
text = format_report(text, locals())
(R/'Environmental_Planning_Report.md').write_text(text,encoding='utf-8')
print('PASS: policy boundaries, totals, MFA, Pareto, CAPEX/OPEX reconciliation; report generated')
