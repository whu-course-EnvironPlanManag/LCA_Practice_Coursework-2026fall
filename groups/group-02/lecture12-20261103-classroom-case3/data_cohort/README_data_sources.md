# data_cohort · 成员 A 中期数据产物

本目录全部文件由 `code_implementation/` 下脚本生成，**不允许手工修改**。

数值计算有两个只读输入：

1. 稳态：`../A前期数据_IDE交接包_20261103/a_phase1_ide_handoff.json`（园区 8 万 t/a 工况）；
2. dMFA：`../A_dMFA数据交接包_20261103/yichang_dmfa_dataset.json`（市域 2010—2025 首装队列 + 寿命参数 + 收集率情景）。
   规划期与寿命参数出处要求另参考 `../assignment_documentation.md`（L79、L200）。两个快照均未修改，不引入外部数据。

| 文件 | 生成脚本 | 内容 | 数据性质 |
| :--- | :--- | :--- | :--- |
| `validation_checks.csv` | `mfa_model.py` | 交接包 17 项结构与语义校验结果（V01–V17） | 校验记录 |
| `feedstock_intake_allocation.csv` | `mfa_model.py` | 8 万 t/a 规划来料按体系份额分配（LFP 60% / MIXED_NMC 40%） | 规划假设（非市场实测） |
| `received_component_inventory.csv` | `mfa_model.py` | 整包级 8 组分 + 电芯组展开 6 组分存量 | 组成代理推算 |
| `feedstock.csv` | `mfa_model.py` | 任务书要求的一体化来料清单：2 行来料 + 28 行组分（整包级/电芯展开） | 组成代理推算 |
| `reference_li_assay.csv` | `mfa_model.py` | 粉料 Li 品位参考值（JR23 NMC 4.34%、JR23 LFP 3.425%、LS23 LFP 2.415%） | 参考量级，不可用于全厂 Li 核算 |
| `process_parameters.csv` | `mfa_model.py` | 14 项未解决输入 + 20 项未启用候选参数（数值列为空） | 缺失项记录 |
| `missing_inputs.csv` | `mfa_model.py` | 每项缺失输入阻塞了哪些模块 | 缺失项记录 |
| `module_readiness.csv` | `mfa_model.py` | 11 个计算模块的 READY / BLOCKED 状态与阻断编号 | 闸门状态 |
| `functional_zones.csv` | `engineering_plan.py` | 8 个功能分区的功能、布局要求、安全缓冲说明 | 定性骨架（面积为空） |
| `engineering_project_catalog.csv` | `engineering_plan.py` | 工程-01 至工程-06 的设备、工序衔接、规模与投资（均为空） | 定性骨架（数值为空） |
| `capacity_interfaces.csv` | `engineering_plan.py` | IF-01–IF-06 规模与投资反算公式及阻断编号 | 接口定义 |
| `dmfa_validation_checks.csv` | `dmfa_yichang.py` | dMFA 数据集 13 项校验（D01–D13：结构/来源/口径/尾部不归一化/未就绪模块不出数） | 校验记录 |
| `dmfa_parameters.csv` | `dmfa_yichang.py` | DMFA-01~07 + M01 + D-PARK-LINK 的实际取值、单位、状态与出处 | 已解析参数 + 未解项 |
| `dmfa_module_readiness.csv` | `dmfa_yichang.py` | 数据集 `module_gates`：6 个 READY(conditional) / 6 个 BLOCKED 及阻断编号 | 闸门状态 |
| `dmfa_yichang_by_chemistry.csv` | `dmfa_yichang.py` | 3 情景 × 31 年 × 2 体系：首装/退役/收集/在用存量 + LFP 锂量（186 行） | 模型计算结果 |
| `dmfa_yichang_annual_total.csv` | `dmfa_yichang.py` | 3 情景 × 31 年合计列 + `scope_note`（首装队列贡献）（93 行） | 模型计算结果 |
| `dmfa_yichang_summary.csv` | `dmfa_yichang.py` | 3 情景累计量、峰值年份、2025/2040 存量、LFP 锂与恒等式状态 | 模型计算结果 |

> 历史遗留：`dmfa_time_axis.csv` 是上一版骨架脚本输出的 15 行**空表**（7 个数值列全空），
> 已被 `dmfa_yichang_by_chemistry.csv` / `dmfa_yichang_annual_total.csv` 的真实结果取代；
> 读数一律以 `dmfa_yichang_*` 为准，不要引用该空表。

## 四条不可违反的读数规则

1. **空单元格不等于 0**：`value`、`design_capacity_t_a`、`capex_yi_yuan` 等列留空表示"尚无数据"，
   不是"计算结果为零"。任何下游脚本读取时应先判空，禁止 `fillna(0)`。
   dMFA 的 2026—2040 首装列为空，`install_status` 标注 `excluded_by_cohort_definition_not_zero`，
   表示"队列边界之外，未建模"，不是"当年新增为 0"。
2. **两级组分不可相加**：`received_component_inventory.csv` 中 `level=整包` 的 8 行合计等于该体系来料量；
   `level=电芯展开` 的 6 行是"电芯"这一行的展开，两者相加会重复计算。
3. **Li 品位只作参考**：`reference_li_assay.csv` 中 `eligible_for_full_li_mfa` 全为 False，
   且粉料原始基准（湿基/干基、元素基/氧化物基）未确认，不能直接乘黑粉产量。
   dMFA 的整包 Li 强度（10.266 / 10.875 / 13.659 kg Li/t 整包）来自车型配套强度换算，**不是**粉料品位。
4. **两套方程不混读**：稳态 CSV（`feedstock_*`、`received_*`、`reference_*`）是"单一年度 8 万 t/a 工况"；
   dMFA CSV（`dmfa_yichang_*`）是"时间维存量—流量递推"。禁止用稳态单年流量反推历史装机，
   也禁止把 dMFA 的既有队列释放写成全市未来退役预测。

## dMFA 表的读法

- 三情景（C065 / C085 / C100）**只改正规收集率 c**；`retired_pack_t` 在三个情景中完全相同——c 不影响退役量。
- `collected_pack_t = c × retired_pack_t`，而 `collected ≠ recycled ≠ park feed`：梯次分流 M01 与
  市域→园区链接 D-PARK-LINK 未解锁，本目录不出现"进入再生"或"园区来料"列。
- `li_in_use_kg` / `li_retired_kg` / `li_collected_kg` 仅对 `chemistry=LFP` 有值；
  未细分三元的 `li_status=null_unresolved_D06-NMC`，**不取 622/811 平均、不填 0**。
- 2026—2040 段的 `mode=closed_historical_cohort_release`，只表示 2010—2025 那批电池的剩余寿命释放。
- 恒等式：`stock_flow_identity_LFP`、`stock_flow_identity_NMC`、`li_identity_LFP` 均须为 PASS
  （结构残差容差 1e-9；Li 物理口径仍以严格 <5e-4 为上限）。

## 数据来源编号

- `SRC031`：规划来料 8 万 t/a（团体规划假设，见 `a_phase1_ide_handoff.json` → `baseline_inputs`）。
- `SRC039` 等：前段组成代理来源（JR23 系列拆解报告），详见交接包 `sources` 与各组分 `source_ids`。
- `R08-1`：危废与一般固废分类贮存要求（`reference_policies`）。
- `DMFA-S011` / `YC_DMFA01_RECON_V2`：dMFA 首装队列条件重建；`DMFA-S001`（WU 2024，Table S1）：
  Weibull 寿命参数；`DMFA-S002`：正规收集率情景与车型配套锂强度。
  完整条目见 `dmfa_parameters.csv` 的 `source` 列与 dMFA 数据集 `sources`。

重新生成：`python code_implementation/run_all.py`（无外网依赖，含 4 张 300 DPI 图）。
