"""AI Prompt: 按工信部2026年第20号公告核对再使用用途及质量证据。
人工核验：官方网页已读取，具体项目适用证据待C核对；非完整法律合规认证。
"""
from datetime import date

SOURCE_URL = 'https://www.miit.gov.cn/jgsj/jns/wjfb/art/2026/art_945f3df30a984763877679740ff296a3.html'


def evaluate_reuse_application(case):
    if date.fromisoformat(case['evaluation_date']) < date(2026,7,30):
        return {'status':'NOT_APPLICABLE','reason':'不按此公告审查公告前日期','source':SOURCE_URL}
    if case.get('has_reuse_branch') is False:
        return {'status':'NOT_APPLICABLE','reason':'无再使用分支','source':SOURCE_URL}
    if case.get('has_reuse_branch') is not True:
        return {'status':'UNKNOWN','reason':'未确认是否含再使用分支','source':SOURCE_URL}
    if case.get('application') == 'electric_bicycle' or case.get('prohibited_by_law_or_mandatory_standard') is True:
        return {'status':'FAIL','reason':'应用领域属于公告明确禁止或其他法律强制标准禁止范围','source':SOURCE_URL}
    if (not case.get('application') or case.get('prohibited_by_law_or_mandatory_standard') is not False
            or case.get('quality_standard_evidence_verified') is not True):
        return {'status':'UNKNOWN','reason':'需明确用途、适用质量标准及符合性证据；旧梯次规模或SOH不能证明合规','source':SOURCE_URL}
    return {'status':'PASS_SCOPED','reason':'仅已提供的用途与质量证据检查通过，不代表完整项目许可合规','source':SOURCE_URL}
