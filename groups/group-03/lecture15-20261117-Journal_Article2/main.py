# -*- coding: utf-8 -*-
"""一键复现：依次运行任务 1/2/3 与基准对照"""
import runpy

for mod in ["run_task1", "run_task2", "run_task3", "benchmarks"]:
    print("\n" + "#" * 70)
    runpy.run_module(mod, run_name="__main__")
