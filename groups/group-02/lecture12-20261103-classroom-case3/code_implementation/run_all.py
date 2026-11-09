#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按依赖顺序一次性运行成员 A 中期建模脚本。

顺序：
    1. mfa_model.py        稳态：数据校验 → 来料分配 → 组分存量 → 参数/闸门/缺失项 CSV
    2. engineering_plan.py 稳态：功能分区 → 重点工程清单 → 规模反算接口
    3. dmfa_yichang.py     dMFA：读取 A_dMFA数据交接包 → 首装队列 存量/退役/收集/锂 → CSV
    4. dmfa_skeleton.py    dMFA 方程自检（合成数据，不写表、不覆盖真实结果）
    5. plot_figures.py     稳态两张 300 DPI 图（工序流/分区布局）
    6. plot_dmfa.py        dMFA 两张 300 DPI 图（退役-收集/存量-锂）

前 2 个是**稳态工序级 MFA**（单一年度 8 万 t/a 工况）；3—4 与 6 是**动态 MFA**（时间维、存量递推），
两套方程与 CSV 分开，不要混读：
    - 稳态 CSV 前缀：validation_checks / feedstock_* / received_* / process_parameters …
    - dMFA CSV 前缀：dmfa_yichang_* / dmfa_validation_checks / dmfa_parameters …
dMFA 的 2026—2040 只表示"2010—2025 既有首装队列的剩余释放"，不是全市未来退役预测；
市域正规收集量也不能直接当园区 8 万 t/a 来料（M01、D-PARK-LINK 未解锁）。

用法：python code_implementation/run_all.py
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SCRIPTS = (
    "mfa_model.py",
    "engineering_plan.py",
    "dmfa_yichang.py",
    "dmfa_skeleton.py",
    "plot_figures.py",
    "plot_dmfa.py",
)

for script in SCRIPTS:
    print("\n" + "▶" * 3 + f" 运行 {script} " + "▶" * 3)
    try:
        runpy.run_path(str(HERE / script), run_name="__main__")
    except SystemExit as exc:
        # 各脚本以 sys.exit(main()) 收尾，此处必须捕获，否则会连带终止 run_all
        code = 0 if exc.code is None else exc.code
        if code != 0:
            print(f"\n✖ {script} 退出码 {code}，终止后续脚本。")
            sys.exit(code)

print("\n全部完成：稳态 MFA + 市域 dMFA + 4 张 300 DPI 图。")
sys.exit(0)
