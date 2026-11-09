# A_BC补充数据_20261103（只读快照）

本目录是 Codex 于 2026-11-03 交付的「A/BC 核查与数据补充」包的**只读快照**，用于：
成员 A 按 `code_review`（A01—A07）修正 `code_implementation/plant_case.py` 与 `code_implementation/dmfa_yichang.py`。

## 文件

| 文件 | 作用 | 是否被代码读取 |
| :--- | :--- | :--- |
| `A_给BC的补充数据.json` | 主数据（13 个顶层键：conventions / operating_case / annual_common_inventory / mechanical_capture_screening / reference_routes / sources / unresolved_inputs / code_review / readiness / input_snapshot / reuse_energy_interface / existing_B_result_audit / metadata） | 是（`plant_case.py` 只读） |
| `补充数据校验.json` | 交付方自检（25 项 PASS） | 否 |
| `来源链接与引用格式.md` | 引用格式 | 否 |
| `核查结论与补充数据说明.md` | 核查结论（B 3267 行全为合成 LCOR、C 的 LCE 3,000 为财务变量等） | 否 |
| `给A项目IDE的简短修改prompt.md` | 本次改动的 6 条要求 | 否 |
| `文件索引.json` | 文件索引 | 否 |

主 JSON `sha256 = 8a7edbd0c3f09def26e868b3a2078f4cdd7d575676cfe6144505ef5706523cbf`（87,497 bytes），
登记于 `../data_cohort/a_group_decisions.json` 的 `supplement_registry`。

## 使用纪律

1. **只读**：本目录内容不得改写；上游若更新，另建新快照目录并改登记，不覆盖本目录。
2. **不自动生效**：`automatically_adopted=false`。其中 `LS23_LFP_NATIVE_POWDER`、`ANL19_GENERIC_HYD_CELL`、
   `JIANG24_NATIVE_LFP_PILOT`、`ND22_WHOLE_CATHODE_PROJECT_REFERENCE` 四套参考 profile
   **互为备选，禁止默认拼成同一座工厂**；`EV_I_M02_TRANSFER_SCREENING`（η=0.9328）是**文献迁移情景**，
   不是园区实测，也不是 Li 回收率。
3. **不解除闸门**：使用本包不改变 `M01—M14` 的未解状态，也不改变正式 LCA / LCOR 的阻断结论。
4. **不覆盖旧口径**：`EV II`（0.8353）与 `EV I`（0.9328）**并列不平均**；
   LS 硫酸 0.5630527 与 0.4902 **并列不平均**；缺陷/舍入残差不得被改写成 PASS。
