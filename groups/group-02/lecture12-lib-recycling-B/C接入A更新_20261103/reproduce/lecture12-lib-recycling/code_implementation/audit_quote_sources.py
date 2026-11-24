"""AI-assisted source/date/applicability review, not a human signature or a quotation.
Evidence statements below reflect bounded public searches made on 2026-11-03.
Missing original quotations are not replaced with unrelated market prices.
"""
import csv
import json
from collections import Counter
from pathlib import Path
from prepare_economic_case import SOURCE, read_prices

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'report/review_20261103'
VAT='https://tianjin.chinatax.gov.cn/11200000000/0300/030004/03000418/p20241226144544917.shtml'
REFUND='https://fgk.chinatax.gov.cn/zcfgk/c102416/c5202062/content.html'
CATALOG=REFUND.replace('/content.html','/5202062/files/')+'资源综合利用产品和劳务增值税优惠目录（2022年版）.pdf'
INCOME='https://www.chinatax.gov.cn/chinatax/c102166/c5178971/content.html'
SAFE='https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do'
CFETS='https://www.chinamoney.com.cn/chinese/bkccpr/index.html?tab=2'
OIL='https://www.oilchem.net/26-1012-17-692c8906100edda1.html'

CONDITIONS={
 'EXCH-01':'仅保留7.2作外部压力情景；未取得2026年10月逐交易日数据和月均计算，不能称月均已核；官方当日数据不替代月均。',
 'PRC-01':'2026为小组价格基年选择，不由一本方法书直接证明；第四版书目、忽略PPI±1.2%的依据待核。',
 'FIN-01':'20年与5%残值为收到的规划设定；未取得HG/T20636或企业可研支持该年限的页码，不能称标准强制寿命。本模型不计残值。',
 'FIN-02':'修改表已明确real 7%；未找到所称2025指南的可核原文，7%只作折现假设。名义与实际利率须用Fisher关系，不用原备注乘法。',
 'FIN-03':'85%是运行情景，不是已确认实际负荷或一概禁止100%的规范要求；分支负荷与8万吨设计能力分列。',
 'CAP-01':'需具体环评/设备报价、日期、处理对象及土建安装范围；900万元/万吨×8仅能验算7200万元，不能证明工程合理。',
 'CAP-02':'需检测重组与质保范围、产能分母及具体报价；1万吨能力保留，但再次使用用途质量另审。',
 'CAP-03':'每万吨1亿元所指包/电芯/黑粉能力不清，不能据此验算2.24亿元；需工艺及设备清单，避免多路线同时满负荷。',
 'CAP-04':'需具体评估题名、产品、补锂及设备范围；2万吨当量与B工艺份额的分母待对齐。',
 'CAP-05':'20—30%比例未给分母与原文；污水、废气、残渣设施及安装工程分项核对；投资不等于治理达标。',
 'CAP-06':'需供水、蒸汽、配电、消防设备及土建分列；600万元/万吨×8仅为算术假设。',
 'CAP-07':'需光伏/储能容量、EPC日期、可交付年电量及输配边界；2400万元不证明可达100%绿电。',
 'CAP-08':'法规并不规定平台应投资1200万元；软件、硬件、工程服务税目与税率不能统一假定13%。',
 'CAP-09':'8项相加=52000万元已验算；只是收到估算合计，不是经审定概算；不能重复计入。',
 'FS-01':'需LFP电池包品级、SOH、成分、杂质、报价日及到厂含税条款；收购方简易/一般计税与发票资格需核。',
 'FS-02':'需NMC622/811组成及金属含量、SOH、杂质与到厂日期；不能把黑粉金属折扣价当电池包价。',
 'FS-03':'5200×60%+8800×40%=6640已验算，但原始价格未核；全体进料配比不能自动等于各分支配比。',
 'TR-01':'当前到厂价含运费，单独费用为0；500元/t不能再乘180km。实际运输分类按物料与法规判定，不等同全部为危废。',
 'UT-01':'需湖北适用月份、用户电压、计费制、分时负荷和基本电费；0.62未取得相同条件公示原件。',
 'UT-02':'2026Q3成交均价未取得原始公告；需电能量、绿证/环境价值、输配损耗、基金附加和售电服务同边界。',
 'UT-03':'蒸汽需压力温度、焓差、热量计量及到厂报价；受热力等交易类别影响，原13%税率未核，不能统一除1.13。',
 'UT-04':'新水/中水不能混价；自来水一般计税9%与原13%标记需核，简易计税另审；排污费、取水税不与水价重复。',
 'RG-01':'需98%硫酸商品吨、运费包装和报价日期；不能将纯酸吨直接乘商品价。',
 'RG-02':'需27.5%双氧水商品吨、稳定剂及运输安全条件，纯量除0.275；只列平台名称不能核验1450。',
 'RG-03':'需片碱固含与品级；液碱不同浓度不可直接替代；补报价日及运包费。',
 'RG-04':'需轻质/重质、纯度、吨袋与到厂条件及日期。',
 'RG-05':'需CaO有效含量、粒径、活性和商品吨；与治理包价去重。',
 'LB-01':'85000为含社保福利的自有员工年薪预算；工资不征增值税，不按原6%除税。外包服务须另列合同和人数口径。',
 'WS-01':'需废物鉴别/代码、含水率、稳定化和接收设施许可与具体报价；不能默认HW49或全部适用6%。',
 'TX-01':'13%是部分货物适用的一般计税税率，不是综合统一税率；税法另有9%、6%及简易计税，按实际交易核对。',
 'TX-02':'25%与优惠资格分开；资源综合利用优惠与特定环保项目三免三减半不能混同，当前税前年金模型不计所得税优惠。',
 'TX-03':'所引2022目录3.1列废旧电池及其拆解物，符合条件时列50%而非30%；磷酸铁不等同磷酸铁锂，不能泛称锂盐铁盐均可退；仍不计入基准。',
 'PR-01':'140000×95%=133000只是算术；原生基价原件与5%再生折价合同均缺，99.5%碳酸锂应匹配认证及杂质。',
 'PR-02':'51200×95%=48640，48600仅可称约数；磷酸铁与磷酸铁锂是不同产品，先核源表是否误取LFP价格。',
 'PR-03':'需Ni/Co/Mn比例、溶液浓度、干基及计价金属，混合盐不能直接叠加三个分离盐单价，折价依据缺。',
 'PR-04':'需2026-10具体交易日、商品铜牌号及升贴水；破碎分选铜箔/废铜不是无需加工即可售的阴极铜，额外精炼费用要匹配。',
 'PR-05':'需具体报价日、牌号杂质和到厂/出厂条件；分选铝片不自动等于99.7%铝锭，熔炼与损耗要匹配。',
 'PR-06':'480元/kWh需可售剩余容量、质保、BMS、检测与应用范围；SOH>85%优先来料与70—85%产品报价对象不完全相同。',
}
PERIODS={'EXCH-01':'2026-10','FS-01':'2026-10','FS-02':'2026（原文无明确周次）',
 'UT-01':'2026（未注明月份）','UT-02':'2026Q3','RG-01':'2026（未注明日/月）',
 'LB-01':'2026','WS-01':'2026','PR-01':'2026-10','PR-04':'2026-10','PR-05':'2026-10','PR-06':'2026'}

def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    records=read_prices(SOURCE)
    rows=[]
    for r in records:
        pid=r['param_id']
        if pid in ['CAP-09','FS-03']:kind='derived_control'
        elif pid.startswith('TX-'):kind='tax_policy_parameter'
        elif pid in ['EXCH-01','PRC-01','FIN-01','FIN-02','FIN-03']:kind='planning_financial_assumption'
        else:kind='external_monetary_estimate'
        url=VAT if pid in ['LB-01','TX-01','UT-03','UT-04','CAP-08'] else REFUND if pid=='TX-03' else INCOME if pid=='TX-02' else CFETS if pid=='EXCH-01' else OIL if pid=='PR-02' else ''
        check='仅算术控制已核，上游价格未核' if kind=='derived_control' else '原件及项目条件未核，保留规划假设'
        if pid in ['TX-01','TX-02','TX-03','LB-01','UT-03','UT-04']:check='原文/类别发现适用性问题，不能按原备注直接认定'
        if pid=='EXCH-01':check='原月均出处未核，不得称实测月均'
        rows.append(dict(param_id=pid,name=r['name'],value=r['value'],unit=r['unit'],
          parameter_kind=kind,claimed_source=r['source'],claimed_period=PERIODS.get(pid,'原表未给可识别报价期间'),
          exact_quote_date='',quote_valid_until='',quote_date_status='未取得确切报价日和有效期' if kind=='external_monetary_estimate' else '非报价或待原件定位',
          original_quote_received=False,source_document_date='',evidence_url=url,
          evidence_scope='相关政策/机构页面或行情条目定位；不能据此确认原表单价' if url else '本地未见具体原件；公开检索未定位相同报价',
          review_status=check,application_conditions=CONDITIONS[pid],
          final_base_evidence_complete=False,review_date='2026-11-03',reviewer='Codex AI辅助核查；成员C本人确认待签'))
    write_csv(OUT/'报价原件日期适用条件核对.csv',rows)
    result=dict(review_date='2026-11-03',source_file=SOURCE.name,total_parameters=len(rows),
      kind_counts=dict(Counter(r['parameter_kind'] for r in rows)),
      exact_original_commercial_quotes_verified=0,
      original_quote_note='未发现可认证的同一商品/服务/范围且含报价日、有效期及交付条件的原始报价；未购买数据、未联系供应商。未命中不证明资料不存在。',
      per_parameter={r['param_id']:r for r in rows},
      tax_basis_has_unresolved_applicability=True,
      priority_flags=['EXCH-01','UT-01','UT-02','UT-03','UT-04','LB-01','TX-01','TX-02','TX-03','PR-02','PR-03','PR-04','PR-05','PR-06'])
    (OUT/'quote_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    evidence=[
      dict(id='VAT2026',title='中华人民共和国增值税法',url=VAT,document_date='2024-12-25',effective_date='2026-01-01',
        locator='第6、10、12—17、22条',finding='工资不作为应税交易；交易类别与进项凭证决定适用处理，不能统一13%除税',limitation='不是项目发票和供应商报价'),
      dict(id='REFUND40',title='财政部税务总局2021年第40号公告',url=REFUND,document_date='2021-12-30',effective_date='2022-03-01',
        locator='第三条、附件目录3.1，PDF第6页',finding='所引目录列废旧电池项目退税50%及条件，不能支持原表统一30%',limitation='未完成项目资格和全部后续变动核实，不计实际可得退税'),
      dict(id='REFUND_CATALOG',title='资源综合利用产品和劳务增值税优惠目录（2022年版）',url=CATALOG,document_date='2021-12-30',effective_date='2022-03-01',
        locator='目录3.1；PDF第6页',finding='资源、产品名单、原料比例及技术条件须逐项匹配；磷酸铁不等于磷酸铁锂',limitation='政策文件不是价格证明'),
      dict(id='INCOME90',title='综合利用资源生产产品取得的收入在计算应纳税所得额时减计收入',url=INCOME,document_date='2022-08-12',effective_date='依所引法律及目录',
        locator='优惠内容、享受条件',finding='符合目录条件的资源综合利用减计收入，与特定环保项目三免三减半不同',limitation='未证明本项目自动满足条件'),
      dict(id='CFETS',title='中国货币网人民币汇率中间价',url=CFETS,document_date='动态数据页',effective_date='相应交易日',
        locator='人民币汇率中间价查询',finding='可作官方取数入口，7.2的10月月均仍未取得完整日序列支持',limitation='动态页面未导出10月全量，不以最近日替代月均'),
      dict(id='SAFE',title='国家外汇管理局汇率查询',url=SAFE,document_date='动态数据页；查看日2026-11-03',effective_date='相应交易日',
        locator='人民币汇率中间价列表',finding='核对汇率需外币单位与交易日；非月平均报价',limitation='不自动修改7.2压力情景'),
      dict(id='OILCHEM_DATE',title='2026年10月12日国内磷酸铁市场价格行情',url=OIL,document_date='2026-10-12 17:34（官方检索摘要）',effective_date='原价格期间待正文',
        locator='平台原条目标题及发布时间',finding='仅定位到日期；未核读正文价格，不能确认51200或48600',limitation='正文读取失败；未购买会员或绕过访问限制')]
    (OUT/'公开来源核读记录.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['total_parameters','kind_counts','exact_original_commercial_quotes_verified']},ensure_ascii=False))

if __name__=='__main__':main()
