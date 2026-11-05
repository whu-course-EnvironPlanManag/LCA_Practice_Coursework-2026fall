"""跨文件核对模型结果、工程流量、报告引用和目录；不替代原始证据核验。"""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import sys
from PIL import Image
from common import ROOT, DATA, RESULTS, OUTPUT, read_csv, write_json


def validate():
    checks=[]
    for path in (ROOT/"code_implementation").glob("*.py"):
        ast.parse(path.read_text("utf-8"))
    checks.append("Python语法")
    manifest=json.loads((RESULTS/"run_manifest.json").read_text("utf-8"))
    for name,digest in manifest["input_sha256"].items():
        assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==digest, "输入已变更但未复算: "+name
    checks.append("实际输入哈希与复算记录")
    raw=json.loads((DATA/"yearbook_source_manifest.json").read_text("utf-8-sig"))
    for entry in raw:
        assert hashlib.sha256((ROOT/entry["file"]).read_bytes()).hexdigest()==entry["sha256"]
    checks.append("20张年鉴原件哈希")
    for name in ["element_balance.csv","recommended_balance_brine.csv","recommended_balance_spodumene.csv"]:
        balance=read_csv(name,directory=RESULTS)
        assert balance and max(float(r["relative_error"]) for r in balance)<.0005
    checks.append("基准及两种推荐工况元素守恒")
    scenarios=read_csv("scenario_results.csv",directory=RESULTS)
    lookup={r["case_id"]:r for r in scenarios}
    anchors=read_csv("anchors.csv",directory=RESULTS)
    for anchor in anchors:
        matching=lookup[anchor["case_id"]]
        assert matching["status"]=="Feasible"
        for field in ["gwp_kg_per_t_lce","lcor_cny_per_t_lce","annual_lce_t","refining_input_t","capex_cny"]:
            assert abs(float(anchor[field])-float(matching[field]))<1e-6
    checks.append("锚点与原始情景逐值一致")
    for primary in ("brine","spodumene"):
        b=next(r for r in anchors if r["primary_route"]==primary and r["anchor"]=="B_Utopia_Distance_Min")
        flow=read_csv(f"recommended_dmfa_{primary}.csv",directory=RESULTS)
        q=sum(float(r["refining_input_t"]) for r in flow if int(r["year"])==int(b["year"]))
        assert abs(q-float(b["refining_input_t"]))<1e-6
        projects=read_csv(f"recommended_projects_{primary}.csv",directory=RESULTS)
        assert abs(sum(float(r["capex_cny"]) for r in projects)-float(b["capex_cny"]))<1e-6
        assert sum(float(r["design_capacity_t_y"]) for r in projects if r["role"]=="refining")>=q
    checks.append("推荐物质流与节点工程容量/已计资本一致")
    report_path=ROOT/"report/Environmental_Planning_Report.md"
    report=report_path.read_text("utf-8")
    cited=set(re.findall(r"!\[[^\]]*\]\(\.\./figures_output/([^\)]+)\)",report))
    pictures={p.name for p in OUTPUT.glob("*.png")}
    assert cited==pictures, f"孤立或缺失图片: {cited^pictures}"
    assert all(p.suffix==".png" for p in OUTPUT.iterdir()), "图片目录含重复格式或附件"
    for path in OUTPUT.glob("*.png"):
        with Image.open(path) as im:
            assert min(im.info["dpi"])>=299.9
    assert not any(ord(c)<32 and c not in "\n\r\t" for c in report), "报告存在公式转义控制字符"
    for name in ["模块0","第1章","第2章","第3章","第4章","第5章","第6章","第7章"]:
        assert name in report
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", report):
        if not target.startswith(("http:","https:","#")):
            assert (report_path.parent/target.strip("<>")).exists(), target
    checks.append("模块0—7、全部PNG引用、300 DPI、相对链接及公式转义")
    guard=subprocess.run([sys.executable,"-X","utf8",str(ROOT/"code_implementation/run_analysis.py"),"--run"],capture_output=True,text=True,encoding="utf-8")
    assert guard.returncode==2 and "--exploratory" in guard.stderr
    checks.append("未显式接受情景时阻止误作实证运行")
    result={"code_and_artifact_checks_passed":True,"checks":checks,"pictures":len(pictures),
        "scenarios":len(scenarios),"research_evidence_ready":False,"member_signatures_complete":False,
        "limitations":"见report/Data_and_Code_Audit.md；测试不证明输入真实，未代签成员。"}
    write_json(RESULTS/"validation.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__=="__main__":
    validate()
