# 最小复现

Python3.11以上；只跑年度清单、经济接口和测试用标准库即可。画图/PDF另需requirements.txt依赖与Windows微软雅黑字体。进入lecture12-lib-recycling后依次执行：

    python code_implementation/integrate_a_supplement.py
    python -m unittest discover -s code_implementation -p "test_*.py" -v
    python code_implementation/write_a_update_report.py
    python code_implementation/render_a_update_pdf.py

A补充读取data_cohort/a_update_20261103快照，不回写A目录。B旧CSV仅用于保留工况ID及历史测试，不读取合成LCOR作为新经济值。不同参考profile不是全厂拼接清单。重新生成的报告需再次检查版式。
