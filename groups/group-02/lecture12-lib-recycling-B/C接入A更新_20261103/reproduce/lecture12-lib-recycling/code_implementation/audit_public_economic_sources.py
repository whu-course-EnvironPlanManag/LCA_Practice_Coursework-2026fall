"""Record public-source review without silently changing financial assumptions.
Findings manually transcribed from web tool observations on 2026-11-03.
Search snippets are explicitly distinguished from readable source bodies.
"""
import csv,json,hashlib,shutil
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'report/public_source_audit_20261103'
DAY='2026-11-03'
# title, URL, document/reference date, access, supported fact and limitations
S={
 'CFETS':('中国货币网人民币汇率中间价查询','https://www.chinamoney.com.cn/chinese/bkccpr/index.html?tab=2','','检索摘要可读；未取得本次月度原始序列','提供官方查询入口；不证明2026年10月均值为7.2。'),
 'NDRC_REV':('建设项目经济评价方法与参数修订建议稿遴选公告','https://www.ndrc.gov.cn/xwdt/tzgg/202306/t20230620_1357700_ext.html','2023-06-20','正文已读','公告启动第三版修订；不是原表所称第四版的完整出版核验。'),
 'HG':('HG/T20636-2017标准目录（非官方目录）','https://www.bzxz.net/bzxz/173275.html','2023-06-25（目录页发布时间）','仅检索摘要；非官方目录、未核标准全文','目录指向自控设计管理范围，不能据此证明20年运营寿命；标准正式原文仍待核。'),
 'CACE':('中国循环经济协会科技成果评价通知','https://www.chinacace.org/science/view?id=254','2025-02-18','检索摘要；仅用于辨认机构','确有协会官网及相关通知；未定位到原表声称的2025动力电池TEA指南。通知不支持7%。'),
 'GS_CAP':('甘肃定西1万吨废旧锂电池回收项目落地（SMM报道）','https://news.smm.cn/news/103980323','2026-06-30','检索摘要可读；未核原环评','报道投资880万元、拆解1万吨/年；项目对象和投资范围仍需原环评，不能直接证明900万元/万吨系数。'),
 'GZ_CAP':('广州新环年处理1万吨回收及梯次利用项目环评','https://sthjj.gz.gov.cn/attachment/7/7718/7718613/9971378.pdf','','检索摘要；PDF打开因18.55MB体积受限','摘要列总投资5200万元，含拆包检测重组等且不拆电芯；不是本案梯次产线3600万元的原件。'),
 'ENV_PAPER':('锂离子电池工业化回收技术环境影响评价研究','https://www.eep1987.com/article/doi/10.20078/j.eep.20251103?viewType=HTML','2026年第40卷第1期（检索线索）','期刊正文页摘要已读；经济数值只见PDF检索摘要，PDF下载404','检索PDF线索列不同项目环保占比4.73%/6.8%；尚未核经济段全文，仅用于提醒20—30%不是由此证实的普遍系数。'),
 'PV':('中山市2024年9月备案项目信息','https://www.zs.gov.cn/attachment/0/518/518321/2451159.pdf','2024-09（备案期）','仅检索摘要，未逐页核PDF','含5.99MW光伏、约2400万元及年发电量信息；不同地点且并非本项目光储微网，仅是结构化投资代理线索。'),
 'EU':('欧盟电池法规2023/1542','https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R1542','2023-07-12（原法规）','检索到原文及2025整合版线索；本轮未完整重核所有修订','第77条电池护照要求可解释功能需求，不能支持平台1200万元；适用对象及后续修订另核。'),
 'SMM_METHOD':('SMM新增废旧磷酸铁锂相关价格点公告','https://news.smm.cn/news/102146863','2023-03-23','正文已读','区分电池、极片、黑粉及锂系数计价；本页不提供5200元到厂包价。'),
 'SMM_SCRAP':('SMM废金属及废电池行情','https://m.smm.cn/hq/fjs','2026-11-02（检索所见更新）','检索可见类别和到厂标记，价格登录受限','只能核查报价类别；未读取到FS-01/02所称2026-10原价。'),
 'HAINAN':('海南退役动力电池回收利用全链条研究','https://www.efchina.org/Attachments/Report/report-ctp-20221114/海南省电动汽车退役动力电池回收利用处理全链条方案研究及政策建议.pdf','2022（报告发布路径；正文日期未复核）','仅PDF检索摘要','表格线索区分运输400元/t与燃料动力500元/t；不证明本案180km运输500元/t。'),
 'ELEC_RULE':('电力中长期市场基本规则','https://zfxxgk.ndrc.gov.cn/web/iteminfo.jsp?id=20581','2025-12-17','正文已读；第17、26、33条','绿电分电能量与环境价值，电网另有费用收取职责；不是0.41或0.62的成交凭证。'),
 'HB_041':('湖北357座中石化加油站用上绿电（湖北日报）','https://epaper.hubeidaily.net/pc/attachment/202511/26/34b656cc-a3d1-458c-90b4-f9416d8ccc18.pdf','2025-11-26','PDF检索摘要；未逐页核读','0.41是报道中的光伏余电售电计算价，不能作为本园区2026Q3购买绿电完整到户价。'),
 'YC_UTIL':('宜昌招商要素：供水蒸汽天然气自备水源','https://www.yichang.gov.cn/show-62359-1024745-1.html','2025-03-05（检索页标日期）','检索摘要可见，正文两次超时','找到宜昌官方公辅信息入口，但未读到证明蒸汽0.085元/MJ及工业新水4.2元/m3的内容。'),
 'YC_STEAM':('宜昌公共资源交易答疑','https://ggzy.sc.yichang.gov.cn/jyxx/003001/003001003/20250306/0b17027a-2843-4ce3-8abf-f4784e41c7ea.html','2025-03-06','检索摘要；本轮未打开正文','线索为特定项目暂定183.79元/t蒸汽，条件含170℃、0.7MPa；需先核原页及热量换算，不能直接替换MJ价。'),
 'ACID':('隆众硫酸日评20260519','https://nenghua.m.mysteel.com/a/26051917/57C45415A4218E8C_abc.html','2026-05-19','检索摘要；打开Cache miss','河南98%冶炼酸380—480元/t参考区间；不同地域/物流，未证明卓创湖北到厂480元。'),
 'PEROXIDE':('隆众双氧水日评20260624','https://nenghua.m.mysteel.com/a/26062416/9FD369E6D417FD87_abc.html','2026-06-24','检索摘要；打开Cache miss','河北27.5%参考650元/t线索，不是1450的原证据。历史2018研报也出现1450，但不能充作2026原价。'),
 'NAOH':('黑猫环保2026片碱采购第二次询价公告转载','https://www.chemall.com.cn/hangye/show-85850.html','2026-06-15','正文已读；原发布者平台附件未核读','98%片碱10吨，控制单价3100元/t，含运税；是景德镇采购控制价而非卓创99%片碱成交价。'),
 'SODA':('生意社轻质纯碱基准价','https://www.100ppi.com/news/detail-20261030-6417422.html','2026-10-30','正文已读','轻质纯碱1025元/t，属于模型基准价；不能当重质/电池工艺等级到厂合同价，也不支持原2600。'),
 'SODA_HZ':('隆众华中纯碱价格','https://www.mysteel.com/oilchem/a/26101611/CCF981988484585B.html','2026-10-16','仅检索摘要；打开Cache miss','华中重质1050—1150元/t线索；须复核原表交付、规格及税价后才可选为代理。'),
 'LIME':('润丰矿业黑龙江生石灰介绍','https://runfengcn.com/detail/2899.html','','仅检索摘要；打开Cache miss，厂家宣传类','含量≥85%的区间及高活性品680—720元/t线索；无可核精确发布日期，不证明湖北90%灰720元。'),
 'WAGE':('湖北省统计局2025年在岗职工平均工资答复','https://tjj.hubei.gov.cn/hdjl/lxgs/202605/t20260519_5938848.shtml','2026-05-19（统计期2025）','正文已读','制造业85571元/年；与85000接近，但工资统计不等于含雇主社保福利的2026宜昌园区人均人工总成本。'),
 'VAT':('中华人民共和国增值税法','https://shanghai.chinatax.gov.cn/zcfw/zcfgk/zzs/202412/t474694.html','2024-12-25通过；页面2024-12-30；2026-01-01施行','正文已读；第6、10、16条','工资服务不征VAT；货物一般13%有例外，交易/凭证决定处理，不能一律13%除税。'),
 'CIT':('税务总局问答引用企业所得税法第四条','https://www.chinatax.gov.cn/chinatax/c102449/c5237520/content.html','2024-12-30','检索摘要；官方问答但主题为非居民所得','可核一般税率25%的法律引用；项目优惠及完整所得税现金流未据此确认。'),
 'REFUND':('财政部税务总局2021年第40号及2022目录','https://fgk.chinatax.gov.cn/zcfgk/c102416/c5202062/content.html','2021-12-30','正文及附件提取文本已读；目录PDF第6页3.1','所引目录废电池项为50%且有资源、产品和技术条件，不支持原统一30%；本轮不证明项目资格或全部后续政策。'),
 'TREND':('集邦锂电产业链价格趋势','https://www.trendforce.cn/price/battery-price/li_co_ni','2026-10-22','正文已读','可见电池级碳酸锂14万元/t及磷酸铁前驱体1.63万元/t；无本项目再生折价成交依据。'),
 'COPPER':('长江有色上海1号铜走势图','https://copper.ccmn.cn/quota/c8282c1efedb4c778ad4be004a5d635c.html','2026-10-22','正文已读','所见1号铜109790元/t，不支持原表所称同月62000；拆解铜箔料与精炼铜规格仍不同。'),
 'METAL':('中国有色网转载长江有色现货行情','https://www.cnmn.com.cn/ShowNews1.aspx?id=474811','2026-10-21','正文已读，转载来源长江有色','含税13%的A00铝23610元/t及明确商品分类；不证明18200，更不证明拆解铝可直接按铝锭售价成交。'),
 'REUSE':('电动汽车退役电池储能应用潜力及成本分析','https://www.escn.com.cn/news/show-1752108.html','2020年前后（检索显示约6.4年前，精确日期待核）','仅检索摘要，历史研究非最新报价','有465元/kWh的假设算例，不支持2026年480的真实模组成交及质保条件。'),
}

# id, classification, sources, assessment, action, query
R=[
('EXCH-01','规划假设；所称月均未核',['CFETS'],'未取得7.17—7.24月均区间的官方日序列和计算。','保留7.2为压力参数，删“已核2026-10月均”表述。','中国货币网 2026-10 人民币中间价 美元 月均'),
('PRC-01','小组设定；书目未核',['NDRC_REV'],'2026价格基年是小组选定；不能由方法书直接证明。','保留价格基年；第四版与忽略PPI的依据待核。','国家发改委 建设项目经济评价方法与参数 第四版'),
('FIN-01','规划假设；原引标准范围疑点',['HG'],'20年未由可核原文支持；所引标准目录为自控专业设计管理。','保留年限假设，撤去标准强制寿命暗示。','HG/T 20636-2017 标准 年限'),
('FIN-02','规划假设；精确出处未定位',['CACE'],'未定位原表所称2025技术经济测算指南及7%条款。','7%实际折现率保持假设，做利率敏感性；不虚构协会页码。','中国循环经济协会 动力电池回收项目技术经济测算指南 2025'),
('FIN-03','小组运行情景',[],'85%负荷不是已核实际运行率；未取得普遍禁止满负荷的规范依据。','按情景保留，区分设计8万和预算6.8万。','环评 白名单 电池回收 年运行负荷 85%'),
('CAP-01','类比线索；原值未核',['GS_CAP'],'仅有相近拆解项目投资报道，不是本案7200万元设备清单。','补原环评、设备/土建边界及规模分母；不线性照搬。','甘肃 1万吨 废旧锂电池 拆解 投资 900万元'),
('CAP-02','类比线索；原值未核',['GZ_CAP'],'有1万吨拆包检测重组项目，但总投资范围与本项不同。','3600万元继续作为预算；参考项目只作类比。','梯次利用 3600万元 1万吨 投资'),
('CAP-03','精确出处未定位',[],'未定位到22400万元湿法设备投资的同口径原件；包/粉料能力分母不清。','保留预算；须工程清单支撑，不把每万吨1亿元当已核系数。','湿法 回收 22400 电池 每万吨 1亿元 投资'),
('CAP-04','精确出处未定位',[],'未定位2万吨直接修复线4000万元的原技术经济评估。','本轮纯湿法已排除此项；其他路线须独立估算。','直接再生 正极 修复 4000万元 2万吨 投资'),
('CAP-05','比例依据未核；有不同项目线索',['ENV_PAPER'],'不同工艺与项目的环保占比不一致；现有证据不证明固定20—30%。','6400万元保留预算，按治理设施拆项核算。','电池回收 环保投资 占比 20% 30%'),
('CAP-06','精确出处未定位',[],'未定位600万元/万吨公辅通用系数及4800万元工程量。','按供水配电消防等实际能力补估。','公用工程 600万元/万吨 电池回收'),
('CAP-07','类比线索；范围不匹配',['PV'],'公开备案有相同2400万元金额但规模、设施和地点不同。','本轮外购绿电已排除该项；自建方案需MW/MWh和发电量。','光伏 储能 2400万元 园区 投资'),
('CAP-08','功能要求存在；金额未核',['EU'],'数字护照法规不提供1200万元造价。','按硬件点位/软件服务/运维报价估算，法规只证功能。','电池数字护照 1200万元 平台 投资'),
('CAP-09','派生算术通过',[],'八项CAPEX相加=52000万元；只证明加法，不证明造价。','保留控制总额；纯湿法选定组合45600万元另列。','本地 CAP-01 至 CAP-08 加总'),
('FS-01','来源类别可核；精确价格受限',['SMM_METHOD','SMM_SCRAP'],'找到废电池报价类别及方法；未取得5200元/t整包同月原价。','保留到厂采购假设；不能用废电芯/粉料价冒充整包。','陶志军 2025 废旧电池 回收 5200 SMM 磷酸铁锂 电池包'),
('FS-02','精确价格未核；公开数值受限',['SMM_SCRAP'],'未取得8800元/t混合三元整包到厂报价原件。','明确体系、SOH、税运和金属含量；保留假设。','三元 电池包 8800 SMM 百川盈孚 回收价格'),
('FS-03','派生算术通过',[],'5200×0.6+8800×0.4=6640，底价仍未获凭据。','只标加权计算通过，不标市场价核实。','本地 FS-01 FS-02 60% 40% 加权'),
('TR-01','历史代理线索；原值未核',['HAINAN'],'文献运输费用与燃料动力费用分列，不能用500燃料费支持500运费。','180km与500元/t保留假设；到厂采购已含运，现金基准不重复计。','退役电池 运输 500元/吨 180km'),
('UT-01','计价结构可核；原值未核',['ELEC_RULE'],'未核到与用户电压、两部制、分时负荷相符的0.62完整综合价。','补当月电价表与负荷曲线；容量费等分列。','湖北 2026 大工业 两部制 代理购电 0.62'),
('UT-02','原值未核；交易边界风险',['ELEC_RULE','HB_041'],'检索中相同0.41出现在余电售电报道；不是所称2026Q3直购均价证明。','完整到户费用未核前，不声称已证明绿电必然便宜。','湖北 2026 三季度 绿电 成交均价 0.41'),
('UT-03','类比线索；单位适配待核',['YC_UTIL','YC_STEAM'],'有特定项目元/吨蒸汽线索；未证明0.085元/MJ。','核压力温度/焓差和热量计费，再做单位换算。','宜昌 工业园 蒸汽 报价 0.085 MJ'),
('UT-04','官方入口定位；原值未核',['YC_UTIL'],'官方页面正文超时；未找到支持本案工业新水4.2元/m3的具体表项。','不把自来水与中水或含污水费综合水价混用。','宜昌 工业 水价 4.2 湖北 园区'),
('RG-01','地区区间代理线索',['ACID'],'其他地区区间包含480，不是同年本案到厂报价证实。','480仍作收到假设；核浓度与运费。','卓创 2026 98% 硫酸 480 元/吨'),
('RG-02','精确原值未核；浓度年份风险',['PEROXIDE'],'2026参考线索与1450不同；检索也有旧年同数值，不能移作当年价。','1450保留假设，核27.5%商品溶液吨，不拿50%或纯物质价格替代。','卓创 27.5% 双氧水 1450 2026'),
('RG-03','同值代理；浓度与报价性质不同',['NAOH'],'已读公告3100元/t对应98%采购控制价，不是本案99%市场成交价。','可列类比证据，需声明规格差异；浓度换算随选定规格同步。','片碱 3100 2026 98% 99%'),
('RG-04','公开对照差异；规格另核',['SODA','SODA_HZ'],'公开轻质基准1025及华中重质区间线索均不支持原2600为同月普通行情。','2600不能称已核2026行情；选工艺等级后另定代理并复跑。','纯碱 2600 2026-10 华中 重质 价格'),
('RG-05','弱代理线索；精确原值未核',['LIME'],'厂家区域区间包含720，但仅摘要且日期/纯度/运费不匹配。','不能升级已核报价；补湖北规格原件或保留预算。','生石灰 CaO 720 元/吨 2026'),
('LB-01','官方统计代理；成本范围不同',['WAGE','VAT'],'制造业工资85571可作工资参照，不是85000含雇主社保福利的直接证明。','分工资和雇主负担，保留85000预算，不再按工资含6%VAT除税。','湖北 2025 制造业 平均工资 2026 宜昌 薪酬'),
('WS-01','精确出处未定位',[],'未定位2200元/t对应本案残渣的湖北处置报价；原HW49标签未证实。','按废物鉴别/代码、含水、运距、固化和处置范围询证。','湖北 危废 2200 元/吨 稳定化 填埋 处置费'),
('TX-01','税率原文可核；统一适用不成立',['VAT'],'货物一般税率条款存在，工资和其他交易分类不能统一13%。','维持报价现金预算，不做全表统一除税；另核凭证和交易。','中华人民共和国增值税法 第六条 第十条 13%'),
('TX-02','一般税率有依据；优惠未证',['CIT'],'一般企业所得税25%有官方法律引用；不证明回收业务自动享三免三减半。','税前/报价预算不直接扣所得税；若扩展税后现金流再审核资格。','企业所得税法 第四条 25% 资源综合利用'),
('TX-03','原引目录与30%不符',['REFUND'],'所引2022目录3.1为50%且列资源产品与条件，并非一切铁盐都适用。','不自动改为项目实得50%；基准激励仍为0，留资格待核。','2021年第40号 2022目录 3.1 废旧电池 退税'),
('PR-01','基准价部分支持；折价为假设',['TREND'],'已读2026-10-22页面可支持14万元参考；乘95%得到13.3万，不证明再生售价。','记录基准日期与5%假设；税运和项目质量另核。','集邦 2026-10 电池级 碳酸锂 140000'),
('PR-02','商品/数量级风险；原价未证',['TREND'],'同日磷酸铁前驱体参考16300，明显不同于原48600；不能因此断言原数值出处必为另一商品。','需核FePO4/LiFePO4及等级；51200×95%=48640，48600另有取整。','磷酸铁 51200 48600 隆众 磷酸铁锂'),
('PR-03','精确出处与折算公式未定位',['TREND','METAL'],'分立硫酸镍等单盐参考不能直接证明混合盐32400。','A先给水合形态/有效金属组成，C按明确计价公式换算。','Ni Co Mn 混合硫酸盐 32400 价格'),
('PR-04','公开对照不匹配；商品适配待核',['COPPER'],'已读同月1号铜价格不是62000；也不等于拆解铜箔可售净价。','62000仅保留假设；按实际商品形态及精炼费用重估。','长江有色 2026年10月 铜 62000'),
('PR-05','公开对照不匹配；商品适配待核',['METAL'],'同月A00铝对照23610而非18200；原表规格99.7%与拆解铝仍需匹配。','不直接套铝锭价给分选料，补熔炼损耗费用。','长江有色 2026年10月 铝 18200'),
('PR-06','历史算例代理；原值未核',['REUSE'],'找到历史假设售价465元/kWh线索，不证明2026年480成交。','按剩余/标称kWh、SOH、用途、BMS和质保确认商品范围。','梯次 储能 模组 480 元/kWh 2026')
]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    watched=[ROOT/'data_cohort/economic_parameters.csv',ROOT/'data_cohort/economic_parameters_received.csv',ROOT/'data_cohort/economic_parameters_revised_20261103.csv',ROOT/'code_implementation/tea_model.py',ROOT/'data_cohort/final_integration_20261103/C_final_assumptions.json']
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    params=list(csv.DictReader((ROOT/'data_cohort/economic_parameters_revised_20261103.csv').open(encoding='utf-8-sig')))
    ids={p['param_id'] for p in params};assert ids=={r[0] for r in R} and len(R)==38
    lookup={r[0]:r for r in R}
    records=[]
    for p in params:
        pid,status,sources,finding,action,query=lookup[p['param_id']]
        records.append(dict(param_id=pid,name=p['name'],received_value=p['value'],unit=p['unit'],claimed_source=p['source'],review_date=DAY,status=status,exact_original_quote_verified=False,source_ids=sources,finding=finding,action=action,search_query=query,model_value_changed=False))
    sources={k:dict(title=v[0],url=v[1],source_date=v[2],access=v[3],finding=v[4],access_date=DAY) for k,v in S.items()}
    (OUT/'逐项公开出处核查.json').write_text(json.dumps(dict(review_date=DAY,scope='38项逐项检索；搜索不保证穷尽，未命中不证明不存在；仅来源审计，不是采购确认或完整法规审查',records=records,sources=sources),ensure_ascii=False,indent=2),encoding='utf-8')
    intro='''# 38项经济参数公开出处核查

核查日期：2026-11-03（Asia/Shanghai）。逐项对照收到的38项参数；搜索有时仅返回摘要或受登录/体积/超时限制，均单列。不把找到平台、相同数字或相近项目当作原报价证实；未命中不证明原件不存在。政策文件仅用于核对所引条款，不证明本项目税收资格或全部后续规则。

本轮只更新来源证据和报告说明，未改变任何模型价格、税收收益或既有LCOR。所有原值的完整项目报价凭据仍未全部匹配。CAP-09和FS-03是算术派生，FIN/PRC是规划设定，不能与市场报价混计“已核率”。

优先处理：PR-02磷酸铁商品/数量级；UT-02交易价与到户价；RG-04纯碱的规格年份；FS采购整包口径；CAP-03设备范围。PR-01可追溯14万元参考，但5%折价仍是假设。不同公开页面的日期、定义和计价边界可能不同，不能拼成同一天一致行情。

## 逐项结果

'''
    lines=[intro]
    for r in records:
        lines += [f"### {r['param_id']} {r['name']}\n",f"收到值：{r['received_value']} {r['unit']}。状态：**{r['status']}**。\n",f"核查：{r['finding']}\n",f"处理：{r['action']}\n",f"检索词：{r['search_query']}。\n"]
        for sid in r['source_ids']:
            s=sources[sid]
            lines.append(f"来源[{sid}]：[{s['title']}]({s['url']})；日期：{s['source_date'] or '未核得精确日期'}；读取状态：{s['access']}。\n")
    lines += ['\n## 来源核读摘要\n']
    for sid,s in sources.items():lines.append(f"- [{sid}] [{s['title']}]({s['url']})：{s['finding']}\n")
    lines += ['\n## 对当前模型的影响\n\n当前纯湿法主稿不计磷酸铁、铜铝等未确认联产品回款，因此本轮发现的PR-02/04/05风险尚未改变其数值；接入全部产品前必须处理。原绿电便宜的结果仍只是0.41/0.62同边界输入假设下的条件结果，不能宣传成核实的到户成本优势。价格与工艺数量确认后应另建版本复跑，不能静默覆盖已经发给B的接口结果。\n']
    (OUT/'38项经济参数公开出处核查.md').write_text('\n'.join(lines),encoding='utf-8')
    register=ROOT/'data_cohort/economic_source_register.csv'
    backup=OUT/'economic_source_register_before_public_review.csv'
    if not backup.exists():shutil.copy2(register,backup)
    with register.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
    added=['public_review_date','public_review_status','public_source_urls','public_source_dates','public_access_status','public_finding','public_action']
    for field in added:
        if field not in fields:fields.append(field)
    byid={r['param_id']:r for r in records}
    for row in rows:
        pid=row['source_id'].removeprefix('ECON_BOOK:')
        if pid not in byid:continue
        r=byid[pid];e=[sources[k] for k in r['source_ids']]
        row.update(public_review_date=DAY,public_review_status=r['status'],public_source_urls=' | '.join(x['url'] for x in e),public_source_dates=' | '.join(x['source_date'] for x in e),public_access_status=' | '.join(x['access'] for x in e),public_finding=r['finding'],public_action=r['action'])
    with register.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    # Historic source columns are retained; newest findings are in the dated public_* columns.
    marker='\n## 2026-11-03逐项公开来源复核\n'
    for name in ['ch03_indicators.md','ch05_economics.md','ch06_management.md']:
        path=ROOT/'report/drafts'/name;body=path.read_text(encoding='utf-8').split(marker)[0]
        path.write_text(body+marker+'\n38项经济输入已完成一轮逐项公开检索，详见report/public_source_audit_20261103/38项经济参数公开出处核查.md及economic_source_register.csv的public_*列。集邦2026-10-22页面支持碳酸锂14万元参考，5%再生折价仍为假设；磷酸铁商品/数量级、纯碱规格年份及绿电到户费用需优先复核。本轮不改变价格、不计新增税收收益，既有情景结果仅保留条件含义。\n',encoding='utf-8')
    after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    assert before==after
    summary=dict(parameter_count=38,source_count=len(S),exact_project_quote_fully_verified=0,derived_arithmetic_verified=['CAP-09','FS-03'],reference_anchor_partially_supported=['PR-01'],model_prices_changed=False,register_rows_updated=sum(x.get('public_review_date')==DAY for x in rows),model_rerun_required_for_this_metadata_update=False,model_inputs_and_code_unchanged=before==after)
    assert summary['register_rows_updated']==38
    (OUT/'unchanged_model_input_hashes.json').write_text(json.dumps(dict(before=before,after=after),ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    deliver=ROOT.parent/'outputs/C公开出处核查_20261103';deliver.mkdir(parents=True,exist_ok=True)
    for p in OUT.iterdir():
        if p.is_file():shutil.copy2(p,deliver/p.name)
    shutil.copy2(register,deliver/register.name)
    manifest={str(p.relative_to(deliver)):hashlib.sha256(p.read_bytes()).hexdigest() for p in deliver.iterdir() if p.is_file() and p.name!='manifest.json'}
    (deliver/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.make_archive(str(deliver),'zip',root_dir=deliver.parent,base_dir=deliver.name)
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
