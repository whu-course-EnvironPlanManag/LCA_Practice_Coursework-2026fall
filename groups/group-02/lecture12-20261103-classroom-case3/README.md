# lecture12 案例三（锂离子电池回收）· 成员 A 中期建模

本目录对应任务书中的 `lecture12-lib-recycling/` 工作场景，按组内命名沿用 `lecture12-20261103-classroom-case3`。

本阶段完成成员 A 的两条线：

1. **稳态工序级 MFA**：8 万 t/a 园区来料分配 + 组分存量 + Li 守恒接口 + 功能分区与工程骨架（不产出未解锁的湿法流量、投资与 LCA 结果）；
2. **市域动态物质流分析（dMFA）**：跨年度存量—退役—正规收集时序与 LFP 在用锂存量。**老师最新要求以 dMFA 为核心方法**，
   不再是"MFA 或 dMFA 二选一"。

## 目录结构

```text
lecture12-20261103-classroom-case3/
├── assignment_documentation.md             官方任务书（只读，不改动）
├── precompiled_references/                 官方预编译文献（只读，6 篇 PDF）
├── A前期数据_IDE交接包_20261103/           成员 A 前期数据（只读快照，不改动）
├── A_dMFA数据交接包_20261103/              市域 dMFA 数据（Codex 交接，只读，未修改原始文件）
│   ├── yichang_dmfa_dataset.json           主数据（13 个顶层键：边界/来源/假设/观测/DMFA-01~07/闸门）
│   ├── README_数据口径与使用顺序.md、IDE_数据接入提示词.md、校验报告.json、文件索引.json
├── code_implementation/
│   ├── mfa_model.py            稳态：数据校验 + 来料分配 + 组分存量 + Li 守恒接口
│   ├── engineering_plan.py     稳态：功能分区 + 工程-01~06 骨架 + 规模反算接口
│   ├── dmfa_yichang.py         dMFA：首装队列 存量/退役/收集/锂 + 恒等式校验 + CSV
│   ├── dmfa_skeleton.py        dMFA 接口库与方程自检（默认不写表，避免覆盖真实结果）
│   ├── plot_figures.py         稳态两张 300 DPI 图
│   ├── plot_dmfa.py            dMFA 两张 300 DPI 图
│   └── run_all.py              按依赖顺序一次跑完 6 个脚本
├── data_cohort/                以上脚本生成的 CSV 与数据说明（禁止手改）
├── figures_output/
│   ├── fig1_mfa_process_flow.png           稳态工序流骨架
│   ├── fig2_zone_layout.png                园区功能分区
│   ├── fig3_dmfa_retirement_collection.png 退役量 vs 三情景正规收集量
│   └── fig4_dmfa_stock_and_li.png          在用存量与 LFP 在用锂/退役锂
└── report/
    └── A_中期建模说明.md        中期成果说明（含 dMFA 结果、阻断清单与下一步）
```

## 运行方式

```powershell
cd groups/group-02/lecture12-20261103-classroom-case3
python code_implementation/run_all.py
# 单独跑 dMFA：python code_implementation/dmfa_yichang.py
# 方程自检（合成数据）：python code_implementation/dmfa_skeleton.py --self-test
```

依赖：Python 3.10+、matplotlib（画图用）；无 pandas/联网需求，两个交接包路径按脚本位置自动定位。

## 一、dMFA 结果（市域首装队列，2010—2040）

数据：`A_dMFA数据交接包_20261103`；确定性文献参数（WU 2024 寿命），条件重建首装队列，三档正规收集率情景。

| 指标 | C065（c=0.65） | C085（c=0.85） | C100（c=1.00） |
| :--- | ---: | ---: | ---: |
| 累计首装（2010—2025，t 整包） | 29,791 | 29,791 | 29,791 |
| 累计首次退役（2010—2040，t） | 29,765 | 29,765 | 29,765 |
| 退役峰值（2029 年，t/a） | 4,817 | 4,817 | 4,817 |
| 累计正规收集（2010—2040，t） | 19,348 | 25,301 | 29,765 |
| 2025 年末在用整包存量（t） | 27,493 | 27,493 | 27,493 |
| 2040 年末既有队列残留（t） | 25.7 | 25.7 | 25.7 |
| LFP 在用锂存量（2025 年末，kg Li） | 239,596 | 239,596 | 239,596 |
| LFP 累计退役锂（kg Li） | 256,010 | 256,010 | 256,010 |
| LFP 累计收集锂（kg Li） | 166,406 | 217,608 | 256,010 |

恒等式：存量—流量（LFP / 未细分三元）与 LFP 锂平衡 **全部 PASS**（相对残差 < 1e-9；Li 口径仍以严格 < 5e-4 为上限）。
13 项数据校验（D01—D13，`dmfa_validation_checks.csv`）全通过。

**结果读法（写报告时必须保留）**：

- 首装队列只有 2010—2025 段，2026—2040 是**既有队列剩余释放**，不是全市未来退役预测，也不能推出"2040 年退役为 0"；
- `collected ≠ recycled`：正规收集量还要经梯次分流 M01 才得到再生处理量，再经 D-PARK-LINK 才谈得上园区来料；
- 市域正规收集量**不能**直接当 8 万 t/a 园区来料（口径、边界、地理范围都不同，见 `D-PARK-LINK`）；
- Li 只覆盖 LFP 部分（按车型配套强度 10.266 / 10.875 / 13.659 kg Li/t 整包），未细分三元整列为 null，**不取 622/811 平均**；
- 寿命分布尾部**不重新归一化**（与交接包 `lifetime_tail` 一致），否则会人为放大退役量。

## 二、稳态模块状态（8 万 t/a 园区）

| 模块 | 状态 | 输出 |
| :--- | :---: | :--- |
| `json_loading_and_validation` | READY | 17 项校验全通过（`validation_checks.csv`） |
| `received_pack_intake_allocation` | READY | LFP 48,000 t/a、MIXED_NMC 32,000 t/a |
| `received_component_inventory` | READY | 整包 8 组分 + 电芯展开 6 组分；任务书要求的合并清单 `feedstock.csv` |
| `recycling_feed_allocation` | BLOCKED（M01） | — |
| `recycling_flow_mfa` | BLOCKED（M01–M03） | — |
| `full_plant_li_mfa` | BLOCKED（M01–M05） | 仅接口 `li_balance_check()` |
| `wet_process_activities` | BLOCKED（M06、M07） | — |
| `engineering_equipment_sizing` | BLOCKED（M09） | 分区与工程骨架（无数值） |
| `complete_lca_inventory` / `lca_tea_results` | BLOCKED（B、C 职责） | — |

稳态与 dMFA 是**两套方程**：稳态是单年度工况，dMFA 是时间维存量递推；CSV 前缀分开（`feedstock_*` / `dmfa_yichang_*`），禁止混读或互推。

## 团队接口约定

- **给成员 B（LCA）**：`received_component_inventory.csv`（`level` 列区分整包级与电芯展开）、
  `dmfa_yichang_annual_total.csv`（时序活动量，含 `scope_note` 列说明"首装队列贡献"）、
  `process_parameters.csv` 中未解决项——B 不可用空值代替 0，也不可自行假设分选收率。
- **给成员 C（TEA/政策）**：`engineering_project_catalog.csv`、`capacity_interfaces.csv`（IF-06 依赖 M12），
  以及 `dmfa_yichang_summary.csv` 三情景收集量（C 做政策情景时只改 `collection_rate`，不改寿命参数）。
- **本阶段不提交 Git**：两个交接包 README 均要求 IDE 不执行提交；由成员 A 复核后统一提交。

## 四条红线（脚本已内置检查）

1. 缺数不填 0：`write_csv` 将 `None` 写为空单元格；`engineering_plan.py` 断言无规模/投资数值泄漏；
   dMFA 的 2026—2040 首装列为空并标注 `excluded_by_cohort_definition_not_zero`。
2. 部分组成不归一化：`mfa_model.py` V10 仅记录原始合计（NMC 粉料 0.82971、LFP 粉料 0.96432、LS23 0.772665）。
3. 未激活不计算：20 个候选工艺参数 `active=false`，V11/V13 校验通过后才继续；dMFA 未就绪的 6 个模块不出数（D12）。
4. 边界不外推：寿命尾部不重归一化、`collected ≠ recycled ≠ park feed`、未细分三元 Li 保持 null。

## 下一步（按优先级）

1. **M01 梯次利用分流比**：组内统一口径（SOH 阈值 ≠ 数量分布）；解除后 `collected(t)` 才能分成梯次/再生两股。
2. **D-PARK-LINK 市域→园区链接**：明确收集半径、合规转运与园区准入，才能把 `collected(t)` 与 8 万 t/a 园区工况对齐。
3. **M02/M03/M05**：分选收率、粉料基准与工艺回收率——决定黑粉产量、湿法通量与全厂 Li 平衡。
4. **M06/M07 湿法体系与酸量版本**：解除 `wet_process_activities`。
5. **M09 年运行小时**：决定设备台数与分区面积（当前全部为空）。
6. **M12 价格与投资系数**：由 C 提供，脚本只留公式与接口。
7. **dMFA 剩余缺口**：全市总量预测（含替换电池与新增装机至 2040）、NMC622/811 细分与对应锂强度、空间网络参数（DMFA-07）。
