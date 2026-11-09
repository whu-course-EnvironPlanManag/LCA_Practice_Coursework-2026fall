"""AI-assisted: record official policy checks without upgrading unsupported rules."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data_cohort'
CN='https://www.miit.gov.cn/cms_files/filemanager/1226211233/attach/202410/8cee9eb9b5af4f7a8bb05880e552ac66.pdf'
ORDER='https://www.miit.gov.cn/gyhxxhb/jgsj/cyzcyfgs/bmgz/jdcjxl/art/2026/art_392462fdc40c415ea4a4129cac3028c2.html'
NOTICE='https://www.miit.gov.cn/jgsj/jns/wjfb/art/2026/art_945f3df30a984763877679740ff296a3.html'
LOCATORS={
 'CN_LI':'三（三）3；PDF第6页','CN_NI':'三（三）3；PDF第6页',
 'CN_CO':'三（三）3；PDF第6页','CN_MN':'三（三）3；PDF第6页',
 'CN_REPAIR':'三（三）3；PDF第6—7页','CN_POWDER':'三（三）3；PDF第6页',
 'CN_IMPURITY_AL':'三（三）3；PDF第6页','CN_IMPURITY_CU':'三（三）3；PDF第6页',
 'CN_ENERGY':'三（三）3；PDF第6页','CN_WATER':'三（三）3；PDF第7页',
 'CN_CAPACITY':'三（一）1；PDF第2—3页；产能原则性要求',
 'CN_RD':'三（一）8；PDF第4页'}

def main():
    path=DATA/'policy_parameters.json'
    policy=json.loads(path.read_text(encoding='utf-8'))
    policy['sources']['CN2024_OFFICIAL']={
      'type':'official_industry_guidance','url':CN,'checked_on':'2026-11-03',
      'status':'已核读工信部公告所附正式PDF；非征求意见稿',
      'application':'已建成投产企业的自愿公告规范评价；不等同普遍行政许可条件',
      'amendment':NOTICE,'amendment_note':'2026第20号已废止梯次相关条款；此处仅核读保留的再生及通用量化项'}
    policy['sources']['TASK_CN2024']['status']='正式原文已另登记CN2024_OFFICIAL；本来源仍仅代表任务书附加/简化口径'
    policy['sources']['TASK_EU2023']['status']='官方检索命中基本条款与2025/1561修订；整合文本正文访问受限，未将全部规则升级为现行已核验'
    policy['scope_note']='课程量化筛选。12项国内规范数值已核读正式PDF，适用于其公告规范评价范围，不具有普遍行政审批前置性；铜铝回收与固氟3项仍仅任务书口径。EU规则未完成整合文本及全部配套核验。PASS仅表示编码项满足，不覆盖许可、排放、质量、消防、碳足迹等全部要求。2026第20号再次使用条款另行检查。'
    for r in policy['rules']:
        if r['id'] in LOCATORS:
            r.update(source_id='CN2024_OFFICIAL',verification='verified_current',
              verified_on='2026-11-03',locator=LOCATORS[r['id']],
              legal_nature='行业引导性规范；自愿公告评价口径',
              application_note='须结合企业对象和指标核算方法；不据此作出整体法定合规结论')
        elif r['id'] in ['CN_CU','CN_AL','CN_FLUORINE']:
            r['evidence_note']='未在本次核读2024规范正式正文中确认该阈值；保留任务书要求，不能归为本规范已核验条款'
    path.write_text(json.dumps(policy,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=[]
    for r in policy['rules']:
        rows.append(dict(rule_id=r['id'],metric=r['metric'],threshold=r['threshold'],
          source_id=r['source_id'],verification=r['verification'],locator=r.get('locator','任务书；官方完整条款及配套待核'),
          url=CN if r['id'] in LOCATORS else policy['sources'][r['source_id']].get('official_url_to_verify',''),
          checked_on='2026-11-03',evidence_note=r.get('evidence_note','已核数值不等于全部项目证据齐备')))
    with (DATA/'policy_evidence_register.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    obligations=dict(checked_on='2026-11-03',source_url=ORDER,effective_from='2026-04-01',
      source_title='六部门令第73号；新能源汽车废旧动力电池回收和综合利用管理暂行办法',
      rules=[
       dict(id='CN73_PROJECT',locator='第18条',scope='从事废旧动力电池综合利用活动',
         requirement='投资核准/备案、环评、配套环保安全设施及排污许可/登记按适用程序落实',
         evidence=['investment_registration','eia','environment_safety_facilities','discharge_permit_or_registration']),
       dict(id='CN73_USE',locator='第22条；2026第20号第二项',scope='利用废旧动力电池生产电池产品',
         requirement='应用质量要求和禁止用途检查',supplement_url=NOTICE),
       dict(id='CN73_TRACE_IN',locator='第24条第一款第（七）项、第二款',scope='综合利用企业',
         requirement='接收后30个自然日内报送入库；核对编码及来源',deadline_natural_days=30),
       dict(id='CN73_TRACE_OUT',locator='第24条第一款第（七）项、第二款',scope='综合利用企业',
         requirement='综合利用产品移交出库后30个自然日内报送出库；核对编码及去向',deadline_natural_days=30)],
      note='按综合利用企业角色登记，不套用生产企业15日期限；未收到项目文件和事件台账，当前均为证据待补。')
    (DATA/'policy_operational_obligations.json').write_text(json.dumps(obligations,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Official quantitative checks:',len(LOCATORS),'Coursework-only CN:',3,'Operational obligations:',4)

if __name__=='__main__':main()
