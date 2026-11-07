"""AI辅助。Prompt：离线从头复现数据提取、模型、检查、图表与报告。人工复核待课程小组确认。"""
from pathlib import Path
import subprocess,sys,os,time
B=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(B/'report/.matplotlib_cache'))
steps=['extract_inputs.py','planning.py','feasibility.py','test_models.py','document_sources.py','figures.py','report.py','validate_delivery.py']
with (B/'report/validation_run.log').open('w') as out:
    for name in steps:
        print('RUN',name,flush=True);out.write('\nRUN '+name+'\n');out.flush()
        result=subprocess.run([sys.executable,str(B/'code_implementation'/name)],stdout=out,stderr=subprocess.STDOUT)
        if result.returncode:raise SystemExit('FAILED '+name+'; see report/validation_run.log')
print('ALL STEPS PASS')
