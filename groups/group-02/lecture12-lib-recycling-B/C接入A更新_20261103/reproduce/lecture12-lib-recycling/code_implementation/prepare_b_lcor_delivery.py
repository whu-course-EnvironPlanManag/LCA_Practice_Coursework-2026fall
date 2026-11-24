"""Export an explicit conditional C handoff; never label missing final LCOR as available."""
import json,shutil,hashlib
from pathlib import Path
from finalize_member_c import ROOT,B,DATA,REPORT,DELIVERY,read_csv,prices_received,build_case
from tea_model import evaluate_tea

def main():
    out=ROOT.parent/'outputs/C发给B_LCOR接口包_20261103';out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((DATA/'C_final_assumptions.json').read_text(encoding='utf-8'))
    brows=read_csv(B/'data_cohort/scenario_results.csv');p=prices_received();items=[]
    for row in brows:
        item={k:row[k] for k in ['case_id','process_mix','green_ratio','grid_ef','lithium_price_usd','energy_efficiency']}
        item.update(lcor_final_CNY_t_LCE=None,policy_status='UNKNOWN',confirmed_policy_feasible=False,
                    partial_lcor_conditional_CNY_t_LCE=None,annual_LCE_scenario_t=cfg['lce_reference_t_a'],
                    currency='CNY',price_year=2026,
                    scope='C gross-quote budget; whole park design; LCE receipts only; other product net credit unresolved',
                    price_conversion_assumption='CNY/t = USD/t * 7.2; stress scenario only, not an observed exchange rate')
        if float(row['process_mix'])==0:
            price=float(row['lithium_price_usd'])*7.2
            case=build_case(cfg,p,brows,cfg['lce_reference_t_a'],float(row['green_ratio']),price,float(row['energy_efficiency']))
            result=evaluate_tea(case)
            item.update(status='CONDITIONAL_PARTIAL_LCOR_NOT_FINAL',partial_lcor_conditional_CNY_t_LCE=result['base_lcor_per_fu'],
                        LCE_price_quote_CNY_t=price,boundary_id=case['boundary_id'])
        else:item['status']='UNSUPPORTED_PROCESS_ROUTE_NO_EQUIVALENT_PRODUCT_BASKET'
        items.append(item)
    assert len(items)==3267 and sum(r['partial_lcor_conditional_CNY_t_LCE'] is not None for r in items)==297
    assert all(r['lcor_final_CNY_t_LCE'] is None and not r['confirmed_policy_feasible'] for r in items)
    (out/'C_to_B_conditional_by_B_case_id.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
    for source,name in [(ROOT/'code_implementation/tea_model.py','tea_model.py'),(DATA/'conditional_baseline_case.json','conditional_case.json'),(DATA/'C_final_assumptions.json','C_final_assumptions.json')]:shutil.copy2(source,out/name)
    runner='''"""Run C conditional demonstration, not a validated final plant LCOR."""
import json
from pathlib import Path
from tea_model import evaluate_tea
root=Path(__file__).resolve().parent
case=json.loads((root/'conditional_case.json').read_text(encoding='utf-8'))
r=evaluate_tea(case)
print(json.dumps(dict(status='CONDITIONAL_PARTIAL_LCOR_NOT_FINAL',lcor_final_CNY_t_LCE=None,partial_lcor_conditional_CNY_t_LCE=r['base_lcor_per_fu'],annual_LCE_scenario_t=case['fu_per_year'],boundary_id=case['boundary_id'],policy_status='UNKNOWN'),ensure_ascii=False,indent=2))
'''
    (out/'run_lcor.py').write_text(runner,encoding='utf-8')
    text='''# C给B：LCOR如何接收

日期：2026-11-03。C负责经济模型与价格/投资/费用、政策参数和规则；B负责环境情景与联调；A负责同一工况物料数量与产品产量。该包是待发送文件，没有替你向任何人发送。

## B立即可接收的内容

1. tea_model.py：C计算引擎；函数evaluate_tea(case)，输出base_lcor_per_fu，单位元/t LCE。数学定义为（资本年金+年运行费用−同边界年产品收入）/年LCE产量。不能仅凭函数返回数值就认为输入已被核实。
2. conditional_case.json和C_final_assumptions.json：可运行条件参照，不覆盖原来尚缺数的正式tea_case_economic_intake.json。参照为年LCE3000吨、实际进厂电池包68000吨、绿电50%、锂盐133000元/t；含税报价现金预算，只计锂盐回款。运行python run_lcor.py（仅需Python标准库）得到64251.711882元/t LCE。它是“仅锂盐回款口径的单位覆盖差额”，不是完整项目LCOR或碳酸锂产品分摊成本。
3. C_to_B_conditional_by_B_case_id.json：保留B现有3267个case_id及五项情景参数。只有297个纯湿法（process_mix=0）工况给出partial_lcor_conditional_CNY_t_LCE；其余路线保留空值和不支持状态，不把纯湿法成本复制给直接修复/混合路线。所有lcor_final_CNY_t_LCE均为空，政策均UNKNOWN。

## B如何接入

先按case_id连接，再同时校验process_mix、green_ratio、grid_ef、lithium_price_usd、energy_efficiency五项参数。不能按文件行号拼接。B的美元锂价在本表仅按假设汇率7.2转人民币压力情景，故22000对应158400，而不是主报告133000的报价参照；两个基准不能混用。

仅在明确选择“条件演示、纯湿法、LCE3000吨、只计锂盐回款、报价现金预算”后，才将partial_lcor_conditional_CNY_t_LCE用于单独的演示图。保留状态和范围标记。不要覆盖正式LCOR字段，不要与B原全路线帕累托前沿混画，不标注政策可行；100%绿电也不等于交付电量已经可得。grid_ef只影响此组环境指标，不直接改变C电价，因而同一其他参数下该列成本可相同。

正式接入时，A补齐数量后，C重新生成每个工况的case并调用evaluate_tea，不应只读固定基准JSON给所有工况同一LCOR。B现有c_interface.lcor_estimate读取固定case的逻辑仍需逐情景映射；拿到本包不代表该适配工作已经完成。补齐所有联产品可售量、价格与成本分配后，再共同确定正式LCOR列和图注。对直接修复路线，要先确定产品与功能单位的等效关系。

## 不要混用的旧试算

report/lcor_handoff_20261103及code_implementation/lcor_handoff.py属于另一套历史假设：由组成与阈值推产量、使用不同投资边界及税价。不能替代本轮最新主稿，也不能把其中的物质流当作A已经确认的产量。B原PROVISIONAL_SYNTHETIC_LCOR为临时合成值；本包给出的条件覆盖差额与之区别记录。

## A必须补的最小清单

第一优先：在同一负荷（设计8万吨；当前实际6.8万吨条件）下，确认梯次/再生按化学体系和SOH的分流，包→电芯→实际捕集黑粉的产量与损失；说明粉料是否含胶、干湿基和Li/Fe/P/Ni/Co/Mn品位，核清NMC622/811基准。当前C均匀分流假设下为梯次8500吨、再生59500吨电池包当量，不能写作电芯质量。

第二优先：正式LCE年产量及等级；磷酸铁、镍钴锰盐、铜、铝、再次使用产品的年可售量、含量/形态与质量标准。盐类注明水合形态或有效金属含量；再次使用注明可售kWh与质保。若未计算可提交文献兼容的规划假设和区间，但明确来源与计算式，不能用规范阈值充当实际收率。

第三优先：分工序电kWh/a、蒸汽MJ/a或t/a（给焓差）、新水/循环水/外排废水m3/a、各试剂商品用量与浓度、危废/残渣t/a及类别；给年运行小时、各工程t/h或m3/h能力与共享关系。若由B补建过程清单，A与B应共同确认同一工艺profile，不能互相等待。

第四优先：Li及Ni/Co/Mn、Cu/Al各分支回收率的分子/分母、粉料捕集率与杂质、固氟、工艺废水循环率、损失去向及守恒误差。只给“≥90%”或“PASS”不足以核算。

若要证明8万吨规模的来料保障，还需园区采购范围、外来料及合同量。现有A的2010—2025首装队列未来释放，不是宜昌未来全部退役量，也不是园区已经取得的供料。价格、投资报价/系数（A表M12）由C承担，不要求A代做。C已确认的1万吨梯次设计能力不必再询问；A需要将其落实到本次计算的分流与产量中。
'''
    (out/'README_先给B看.md').write_text(text,encoding='utf-8')
    (REPORT/'LCOR交接与当前完成状态.md').write_text(text+'''\n## Report更新状态\n\nreport/drafts/ch03_indicators.md、ch05_economics.md、ch06_management.md已追加最新A/B接续章节，历史审计保留；本轮定量口径以report/final_integration_20261103/C成员经济与管理交付稿.md为准。C本轮完成与剩余事项文件已加最新说明。不是把所有历史报告重写成同一数字。\n\nC的条件交付、模型/政策程序、5148工况、图表与贡献记录已完成；正式全厂LCOR、联产品一致边界、报价原件及人工确认仍未全部完成。C还负责核实自己的价格与规则并在补数后重跑，不是所有事情都已处理完、只剩等A。B还须按逐情景接口接入并重画最终前沿；缺数据不得标记真实合规。\n''',encoding='utf-8')
    marker='\n## LCOR交付接口更新\n'
    for name in ['ch03_indicators.md','ch05_economics.md','ch06_management.md']:
        path=ROOT/'report/drafts'/name
        body=path.read_text(encoding='utf-8').split(marker)[0]
        path.write_text(body+marker+'\nC已提供独立的outputs/C发给B_LCOR接口包_20261103。最新交接说明见report/final_integration_20261103/LCOR交接与当前完成状态.md。纯湿法条件覆盖差额与正式LCOR分列；正式LCOR仍待A的同工况产品/物耗和B/C边界一致后重算。不能将历史lcor_handoff组成推算当作A确认结果。\n',encoding='utf-8')
    files=[{'path':str(x.relative_to(out)),'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in out.iterdir() if x.is_file() and x.name!='manifest.json']
    (out/'manifest.json').write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=shutil.make_archive(str(out),'zip',root_dir=out.parent,base_dir=out.name)
    shutil.copy2(REPORT/'LCOR交接与当前完成状态.md',DELIVERY/'LCOR交接与当前完成状态.md')
    for name in ['ch03_indicators.md','ch05_economics.md','ch06_management.md']:
        shutil.copy2(ROOT/'report/drafts'/name,DELIVERY/'章节补充'/name)
    print(json.dumps({'packet':str(out),'zip':archive,'conditional_pure_hydro_rows':297,'final_LCOR_available':False},ensure_ascii=False))

if __name__=='__main__':main()
