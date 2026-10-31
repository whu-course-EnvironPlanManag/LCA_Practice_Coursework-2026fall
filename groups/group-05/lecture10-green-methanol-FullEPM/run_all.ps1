$ErrorActionPreference='Stop'
foreach ($name in @('task1_mfa_recycle_solver.py','task2_policy_vibe_engine.py','task3_pareto_frontier_decision.py','task4_process_sankey_flow.py')) {
 python (Join-Path $PSScriptRoot "code_implementation/$name")
 if ($LASTEXITCODE -ne 0) { throw "运行失败：$name" }
}
