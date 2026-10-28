"""按课程模板组织报告；数值直接使用计算脚本传入的结果。"""
from pathlib import Path

def format_report(text, ns):
    table=ns['table'];b=ns['b'];co=ns['co'];h=ns['h'];w=ns['w'];o=ns['o'];r=ns['r'];water=ns['water'];cap=ns['cap'];ops=ns['ops']
    chapters={
      '## 第1章 现状诊断与基准线':'## 第 1 章 园区现状诊断与碳源-新能源基准线核算\n\n### 1.1 园区产业结构与物质-能量代谢分析（MFA/EFA）',
      '## 第2章 多情景预测与规模匹配':'## 第 2 章 多情景预测与系统规模匹配核算\n\n### 2.1 规划期园区碳排放趋势与多情景设定',
      '## 第3章 规划目标与指标体系':'## 第 3 章 规划目标与指标体系设计\n\n### 3.1 规划总目标与分期节点',
      '## 第4章 空间落位与工程实施':'## 第 4 章 空间落位布局与重点工程实施方案\n\n### 4.1 园区“源-网-荷-储-化”空间管控与红线',
      '## 第5章 LCA、TEA与多目标决策':'## 第 5 章 全生命周期环境影响（LCA）、技术经济（TEA）与帕累托多目标决策评估\n\n### 5.1 全生命周期环境影响评估与电力结构分析',
      '## 第6章 制度保障与动态管理':'## 第 6 章 制度保障、商业模式与智慧环境管理机制\n\n### 6.1 商业闭环与绿色投融资机制'}
    for old,new in chapters.items():text=text.replace(old,new)
    text=text.replace('## 摘要','## 报告摘要')
    start=text.index('## 术语');end=text.index('## 第 1 章',start)
    terms=(Path(__file__).with_name('terminology_table.md')).read_text(encoding='utf-8')
    text=text[:start]+'## 核心术语与缩写中英文对照表\n\n'+terms+'\n\n'+text[end:]
    text=text.replace('材料没有提供全园区煤耗','\n\n### 1.2 工业点源CO₂排放清单与烟气特征解析\n\n材料没有提供全园区煤耗')
    text=text.replace('开篇讨论情景使用','### 1.3 绿电资源禀赋与公用工程承载力评估\n\n开篇讨论情景使用')
    text=text.replace('## 第 2 章','### 1.4 园区现行碳管理问题与减污降碳协同瓶颈\n\n主要问题为清洁供电与连续负荷匹配、循环驰放的资源损失、胺液和尾气二次污染，以及生产碳账和政策收益边界的一致性。本方案通过电源结构优化、循环调控、水回用和分项计量协同管理。\n\n## 第 2 章',1)
    text=text.replace('锚点B年捕集','\n\n### 2.2 碳捕集—绿氢—甲醇系统物料与能量衡算\n\n锚点B年捕集',1)
    rows=[['新鲜CO₂',f'{co:.3f} kg/t',f'{co*100:.3f} t/a','气体；捕集压缩至合成段'],['新鲜H₂',f'{h:.3f} kg/t',f'{h*100:.3f} t/a','气体；电解制氢至合成段'],['净除盐水（基准定额）','1385.000 kg/t','138500.000 t/a','液体；课程政策基础值，非B独立水衡算'],['综合取水（B政策口径）',f'{water*1000:.3f} kg/t',f'{water*1e5:.3f} t/a','含经验冷却耗水'],['精馏副产水回用',f'{w:.3f} kg/t',f'{w*100:.3f} t/a','液体；回流制氢进水池'],['未反应气内循环（课程基准）','4640.000 kg/t','464000.000 t/a','气体；r=1%基准，不冒充B通量'],['驰放气（B经验式）',f'{46*r/.01:.3f} kg/t',f'{46*r/.01*100:.3f} t/a','气体；送锅炉治理'],['精甲醇','1000.000 kg/t','100000.000 t/a','液体；双塔精馏产品'],['副产氧气',f'{o:.3f} kg/t',f'{o*100:.3f} t/a','气体；外售'],['综合电耗',f'{b.e_total_kwh:.3f} kWh/t',f'{b.e_total_kwh*1e5/1e8:.5f} 亿kWh/a','制氢、捕集、循环压缩、精馏合计']]
    material='表2-1 单吨定额与10万吨/年工程通量\n\n'+table(['物料或能量节点','单吨定额','年度通量','物态、来源及去向'],rows)+'\n\n'
    text=text.replace('![图1 工艺拓扑]',material+'![图1 工艺拓扑]')
    text=text.replace('(../figures_output/fig1_mfa_process_flow.png)','(../figures_output/fig1_mfa_process_flow.png)\n\n*图1 10万吨/年甲醇系统物质与能量流向拓扑图。图中B经验通量与循环基准参照分别标识。*')
    # 将独立守恒说明留在2.2，容量分析归2.3
    a=text.index('按8000小时折算');e=text.index('独立核验采用',a);capacity=text[a:e].strip();text=text[:a]+text[e:]
    text=text.replace('## 第 3 章','### 2.3 绿电波动性约束下的柔性容量与储氢缓冲配置\n\n'+capacity+'\n\n## 第 3 章',1)
    text=text.replace('|指标及单位|','### 3.2 规划指标矩阵（约束性指标与预期性指标）\n\n表3-1 规划指标矩阵\n\n|指标及单位|',1)
    a=text.index('| 工程 |');e=text.index('\n\n',a)
    order=[1,0,2,3,4];names=['碳源捕集与精制','绿氢制备与缓冲','甲醇催化合成','精馏提纯与节水','管廊输配与MRV'];years=['2027—2028','2027—2028','2027—2029','2028—2029','2027—2028']
    scales=[f'吸收及压缩；CO₂ {co*100:.0f} t/a',f'电解及氢缓冲；H₂ {h*100:.0f} t/a；功率需求{h*52*1e5/8e6:.2f} MW',f'催化合成10万吨/年；r={r*100:.4f}%','双塔精馏；回水57500 t/a','管廊、仪表、供水与电气接入']
    rows=[]
    for j,i in enumerate(order):rows.append([f'工程-0{j+1}',names[j],names[j]+'工程','新建',ns['loc'][i],scales[j],years[j],f'{cap[i]/1e8:.5f}',f'{ops[i]*10:.2f}',['回收碳源','供应氢与副产氧','形成甲醇产品','回收副产水','完善能碳计量'][j],ns['owner'][i]])
    rows.append(['合计','—','10万吨/年绿色甲醇示范项目','—','园区', '设计产能10万吨/年','2027—2029',f'{cap.sum()/1e8:.5f}',f'{ops.sum()*10:.2f}','年度避免排放'+f'{(2600-b.gwp_net)*100:.2f} t CO₂e','园区政企协同'])
    project='### 4.2 核心单元工艺比选与工程设计\n\n捕集采用课程胺吸收与多级压缩方案；制氢按PEM耗电模型核算，ALK/PEM混联作为柔性配置备选，不预先计入节能收益。合成采用固定床催化与循环分离，精馏采用双塔提纯及副产水回用。涉及氢、氧和甲醇的设备分区配置，末端驰放气送锅炉并配置治理。\n\n### 4.3 园区重点工程项目库清单表（基于锚点B）\n\n表4-1 重点工程清单（课程规划总投资9.15亿元）\n\n'+table(['编号','工程类别','工程名称','性质','空间落位','核心工艺与规模','建设周期','规划CAPEX亿元','OPEX万元/年','预期效益','责任主体'],rows)
    text=text[:a]+project+text[e:]
    text=text.replace('折现率8%、寿命20年','### 5.2 技术经济分析与平准化成本核算\n\n折现率8%、寿命20年',1)
    a=text.index('| 方案 |');e=text.index('\n\n',a)
    rows=[]
    for j,(key,z) in enumerate(ns['a'].items()):rows.append([['A：成本极小','B：折中主推','C：最低GWP'][j],f'({z.f_green*100:.4f}%, {z.r_purge*100:.4f}%)',f'{z.eta_carbon:.4f}',f'{z.gwp_net:.4f}',f'{z.base_lcom:.4f}',f'{z.lcom_policy_adjusted:.4f}',f'{z.mac_policy_adjusted:.4f}',z.compliance_status,['财务成本对照','课程规划基准','减排极限对照'][j]])
    text=text[:a]+'### 5.3 帕累托多目标决策与三锚点比选\n\n表5-1 三锚点综合比选\n\n'+table(['锚点','绿电比例/驰放比例','碳利用率%','GWP kg CO₂e/t','基础LCOM元/t','净LCOM元/t','MAC元/t CO₂e','课堂合规状态','规划定位与采纳建议'],rows)+text[e:]
    text=text.replace('(../figures_output/fig2_pareto_decision_frontier.png)','(../figures_output/fig2_pareto_decision_frontier.png)\n\n*图2 政策约束下的目标空间帕累托前沿与工程决策变量双子图。*')
    text=text.replace('MRV系统覆盖','### 6.2 数字化监测、报告与核查体系\n\nMRV系统覆盖',1).replace('涉氢区域配置','### 6.3 环境风险防控与PDCA动态管理\n\n涉氢区域配置',1)
    a=text.index('## 资料来源');text=text[:a]+'''## 参考文献

1. 《环境规划与管理》课程组. 第十讲随堂训练手册：lecture10_task_manual.md. 2026.
2. 《环境规划与管理》课程组. 工业园区CO₂捕集与绿氢合成绿色甲醇系统：工程背景与理论核算手册. 2026.
3. 《环境规划与管理》课程组. 政策法规与标准条文卡片包：policy_clauses_pack.md. 2026.
4. 《环境规划与管理》课程组. MFA工程物料平衡、LCA电力情景与TEA敏感性数据集（data_cohort内三份CSV）. 2026.
5. 《环境规划与管理》课程组. 环境规划报告编制模板与评分量表. 2026.
6. 《环境规划与管理》课程组. 四项任务Python脚手架及第十讲PR考核核验表. 2026.

以上为本报告实际采用的课程资料。法规名称及数值按课程情景使用。
'''
    # 恢复模板中独立的物理参数、来源去向及指标属性列。
    start=text.index('| 物料或能量节点 |');end=text.index('\n\n',start)
    lines=text[start:end].splitlines();newrows=[]
    for line in lines[2:]:
        cells=[v.strip() for v in line.strip('|').split('|')]
        detail=cells[3].split('；',1)
        newrows.append(cells[:3]+[detail[0],detail[1] if len(detail)>1 else '见本节模型口径'])
    text=text[:start]+table(['物料节点名称','单吨甲醇实物定额','10万吨/年工程规划通量','物质状态与物理参数','来源与去向说明'],newrows)+text[end:]
    start=text.index('|指标及单位|');end=text.index('\n\n',start)
    lines=text[start:end].splitlines();newrows=[]
    for idx,line in enumerate(lines[2:]):
        cells=[v.strip() for v in line.strip('|').split('|')]
        name,unit=cells[0].rsplit('，',1)
        detail=cells[4].split('；',1)
        dimension='环境与降碳' if idx<4 else ('能源与资源' if idx<8 else '污染协同控制')
        newrows.append([dimension,name,unit]+cells[1:4]+[detail[0]+'性',detail[1]])
    text=text[:start]+table(['目标维度','指标名称','单位','现状基准值（2026）','近期目标值（2028）','远期目标值（2035）','指标属性','核算依据与B对照'],newrows)+text[end:]
    text=text.replace('合成2028—2029年','合成2027—2029年')
    text=text.replace('不冒充B通量','仅作基准参照')
    # 标题与正文保持空行；来源在使用处标注。
    import re
    text=re.sub(r'(^#{1,3} [^\n]+)\n(?!\n)',r'\1\n\n',text,flags=re.M)
    text=text.replace('设置纯网电、混合电源及全绿电三类情景','依据课程任务与工程背景资料[1—2]，设置纯网电、混合电源及全绿电三类情景')
    text=text.replace('政策四项依次为','依据政策条文卡片[3]，政策四项依次为')
    text=text.replace('表3-1 规划指标矩阵','表3-1 规划指标矩阵（依据课程报告模板[5]）')
    return text
