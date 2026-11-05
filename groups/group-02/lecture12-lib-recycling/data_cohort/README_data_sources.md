# 数据来源与溯源登记（三方合并）

> 本文件汇总成员 A/B/C 三方输入数据来源，是任务书 §八 自检项「README_data_sources 溯源」的载体。
> 所有金额为规划参考价、未取得成交原件；缺省值保持 UNKNOWN，不代填。

---

## 一、成员 A（市域 dMFA / 园区物质流 / 工艺清单 / 工程）

# data_cohort · 成员 A 中期数据产物

本目录全部文件由 `code_implementation/` 下脚本生成，**不允许手工修改**（唯一例外是 `a_group_decisions.json`，
它是成员 A 维护的**输入**决策文件，由本人在此处登记，脚本只读并逐项校验）。

## 1. 三个只读输入 + 一个组内决策文件

| 输入 | 路径 | 用途 |
| :--- | :--- | :--- |
| 稳态交接包 | `../A前期数据_IDE交接包_20261103/a_phase1_ide_handoff.json` | 园区 8 万 t/a 规划来料、组成代理、候选参数、闸门 |
| dMFA 交接包 | `../A_dMFA数据交接包_20261103/yichang_dmfa_dataset.json` | 市域 2010—2025 首装队列 + 寿命参数 + 收集率情景 |
| **B/C 核查补充包（2026-11-03 新增）** | `../A_BC补充数据_20261103/A_给BC的补充数据.json` | 捕集实验代理、LS23/ANL19/JIANG24/ND22 参考 profile、`code_review` A01—A07、11 项未解输入 |
| **组内决策（本目录内）** | `a_group_decisions.json`（schema v2.0.0） | 80,000 / 0.85 / 8,500 / 59,500 等组内工况、产品口径规则、B 快照默认值、外置参考常数 |

三个快照均**未修改**；补充包在 `a_group_decisions.json → supplement_registry` 中登记了 sha256 与
`automatically_adopted: false`，六个纪律开关全部为 false（不激活候选参数、不激活补充路线、不解除正式 LCA/LCOR 闸门）。
规划期与寿命参数出处要求另参考 `../assignment_documentation.md`（L79、L200）。

## 2. 稳态 MFA（`mfa_model.py`）

| 文件 | 内容 | 数据性质 |
| :--- | :--- | :--- |
| `validation_checks.csv` | 交接包 17 项结构与语义校验结果（V01–V17） | 校验记录 |
| `feedstock_intake_allocation.csv` | 8 万 t/a 规划来料按体系份额分配（LFP 60% / MIXED_NMC 40%） | 规划假设（非市场实测） |
| `received_component_inventory.csv` | 整包级 8 组分 + 电芯组展开 6 组分存量 | 组成代理推算 |
| `feedstock.csv` | 任务书要求的一体化来料清单：2 行来料 + 28 行组分 | 组成代理推算 |
| `reference_li_assay.csv` | 粉料 Li 品位参考值（JR23 NMC 4.34%、JR23 LFP 3.425%、LS23 LFP 2.415%） | 参考量级，不可用于全厂 Li 核算 |
| `process_parameters.csv` | 14 项未解决输入 + 20 项未启用候选参数（数值列为空） | 缺失项记录 |
| `missing_inputs.csv` | 每项缺失输入阻塞了哪些模块 | 缺失项记录 |
| `module_readiness.csv` | 11 个计算模块的 READY / BLOCKED 状态与阻断编号 | 闸门状态 |

## 3. 功能分区与工程骨架（`engineering_plan.py`）

| 文件 | 内容 | 数据性质 |
| :--- | :--- | :--- |
| `functional_zones.csv` | 8 个功能分区的功能、布局要求、安全缓冲说明 | 定性骨架（面积为空） |
| `engineering_project_catalog.csv` | 工程-01 至工程-06 的设备、工序衔接、规模与投资（均为空） | 定性骨架（数值为空） |
| `capacity_interfaces.csv` | IF-01–IF-06 规模与投资反算公式及阻断编号 | 接口定义 |

## 4. 市域 dMFA（`dmfa_yichang.py`）

| 文件 | 内容 | 数据性质 |
| :--- | :--- | :--- |
| `dmfa_validation_checks.csv` | dMFA 数据集 13 项校验（D01–D13） | 校验记录；任一 FAIL 即不计算（A07 fail-fast） |
| `dmfa_parameters.csv` | DMFA-01~07 + M01 + D-PARK-LINK 的取值、单位、状态与出处 | 已解析参数 + 未解项 |
| `dmfa_module_readiness.csv` | 数据集 `module_gates`：6 个 READY(conditional) / 6 个 BLOCKED | 闸门状态 |
| `dmfa_yichang_by_chemistry.csv` | 3 情景 × 31 年 × 2 体系：首装/退役/收集/在用存量 + LFP 锂量（186 行） | 模型计算结果 |
| `dmfa_yichang_annual_total.csv` | 3 情景 × 31 年合计列 + `scope_note`（首装队列贡献）（93 行） | 模型计算结果 |
| `dmfa_yichang_summary.csv` | 3 情景累计量、峰值年份、2025/2040 存量、LFP 锂与恒等式状态 | 模型计算结果 |

> 历史遗留：`dmfa_time_axis.csv` 是上一版骨架脚本输出的 15 行**空表**（7 个数值列全空），
> 已被 `dmfa_yichang_by_chemistry.csv` / `dmfa_yichang_annual_total.csv` 的真实结果取代；
> 读数一律以 `dmfa_yichang_*` 为准，不要引用该空表。

## 5. 单工况年度接口（`plant_case.py`，2026-11-03 新增）

输入：`a_group_decisions.json` + `../A_BC补充数据_20261103/A_给BC的补充数据.json`（sha256 已校验）。
输出 8 张表，主表 131 行、其中数量留空 12 行：

| 文件 | 内容 | 读法要点 |
| :--- | :--- | :--- |
| `plant_annual_material_products.csv` | 同 `case_id` 的年度物料/中间品/可售品长表（131 行） | 5 个 `section`：A 工况 / B 组分库存 / C 黑粉与捕集 / D 再使用与产品 / E 公用工程与药剂；每行带 `quantity_kind`、`value_basis`、`status`、`source_ids` |
| `blackmass_capture_screening.csv` | 黑粉库存 vs EV I（η=0.9328）/ EV II（η=0.8353）捕集情景（4 行） | 两情景**并列不平均**；分母是"可回收黑粉基准质量"，不是整包或 Li 质量 |
| `b_activity_reference_profiles.csv` | 按 `profile_id` 隔离的活动量/品位参考（78 行：LS23 38 / ANL19 18 / JIANG24 18 / ND22 4） | **禁止跨 profile 拼成一条产线**，`per_fu_value` 只在 LS 情景用干纯 1,059.736 t LCE 作分母 |
| `activity_vector_for_B.csv` | B 的 12 活动键接口 | `a_formal_value_per_fu` **全为空**；只能取 `a_screening_annual` 并保留占位/商品吨注记 |
| `c_cost_quantity_interface.csv` | C 计价用年量（CR-01—CR-33） | `commercial_or_active` 列区分商品吨/有效吨；`wet_or_dry` 列区分湿基/干基；可售品数量全空 |
| `integration_abc_checks.csv` | A/B/C 交叉校验 28 项（I01—I30 中的 28 条） | 状态含 PASS / NOTE / NOT_COMPARABLE / REMOVED / PARTIAL / NOT_AVAILABLE / DECLARED_FAIL；**A 侧 FAIL 0** |
| `plant_case_checks.csv` | 工况与口径自检 X01—X13 + 补充包 S01—S12 + 成果 P01—P17 | 任一 FAIL 即不写结果表（fail-fast） |
| `gap_table.csv` | 14 行缺口（11 项未解输入 + M06_ROUTE + M07_ACID + GAP-LCE-SALE） | 含 `blocking_scope / owner / next_action / severity / status`，是报告第 8 章的替代数据源 |

### 5.1 R1 背景情景（2026-11-04 新增，与原情景并列）

输入：`a_group_r1_scenario_20261104.json`（只读，`automatically_adopted=false`）；脚本 `plant_case_r1.py`、`dmfa_future_r1.py`。
R1 用「文献迁移 + 情景假设」把原本 null 的量填成一套可复现第二情景（再生入口 60,579.50 t/a），与 59,500 原情景**并列不混用**。

| 文件 | 内容 | 读法要点 |
| :--- | :--- | :--- |
| `plant_r1_scenario_products.csv` | R1 分流/主物料/粉料元素/药剂/三元/能耗/梯次长表（62 行） | 8 个块 SPLIT / LFP_MAIN / LFP_ASSAY / LFP_LI / LFP_REAGENT / NMC / ENERGY / REUSE；每行带 `attribute`（组内设定/文献原值/文献迁移/情景假设/无） |
| `plant_r1_scenario_checks.csv` | R1 情景自检 17 项 | fail-fast；任一 FAIL 不写结果表；含 R1-L06~L08 Li 守恒闭合（`mfa_model.li_balance_check` 判 pass） |
| `dmfa_r1_future_annual_inflow.csv` | 2026—2040 分体系首装/替换流入 | 首装 5%/a、替换=存续车辆失效立即同体系同质量换包（情景假设） |
| `dmfa_r1_future_check.csv` | 校核年退出/存量 + c=0.80 收集与供需量比 | 退出未扣梯次与其他企业分流；供需量比≠园区进料 |
| `dmfa_r1_future_summary.csv` | 参数、2025 条件库存、纪律 | 条件库存非宜昌实测库存 |

纪律：0.50 是粉产率非捕集率；粗品/元素量非合格商品（可售品仍 null；GAP-LCE-SALE 未解）；622/811 技术端点非本地拆分；硫酸主/备选不平均、蒸汽不转 MJ；`dmfa_r1_future_*`（未来新增+替换）与 `dmfa_yichang_*`（既有队列剩余释放）**不可相加**；LFP_LI 块的损耗拆分（40%/32%/20%/8%）是显式标注的**情景假设占位拆分，非实测损耗分布**，只用于让湿法粉料参考块的 Li 元素守恒自洽闭合（相对误差 0），不代表已定位真实去向。

## 6. 读数规则（不可违反）

1. **空单元格不等于 0**：`value`、`quantity_per_year`、`design_capacity_t_a`、`capex_yi_yuan` 等列留空表示"尚无数据"，
   不是"计算结果为零"。任何下游脚本读取时应先判空，禁止 `fillna(0)`。
   dMFA 的 2026—2040 首装列为空，`install_status` 标注 `excluded_by_cohort_definition_not_zero`。
2. **两级组分不可相加**：`level=整包` 的 8 行合计等于该体系来料量；`level=电芯展开` 的 6 行是"电芯"这一行的展开，
   两者相加会重复计算。`plant_annual_material_products.csv` 沿用同一 `level` 约定。
3. **Li 品位只作参考**：`reference_li_assay.csv` 的 `eligible_for_full_li_mfa` 全为 False，
   且粉料原始基准（湿基/干基、元素基/氧化物基）未确认，不能直接乘黑粉产量。
   dMFA 的整包 Li 强度（10.266 / 10.875 / 13.659 kg Li/t 整包）来自车型配套强度换算，**不是**粉料品位；
   `plant_annual_material_products.csv` 的 C-06/C-07 元素参考含量以**黑粉库存**为分母，不乘捕集率。
4. **多套口径不混读**：`feedstock_*` / `received_*` 是"8 万 t/a 规划来料分配"；`plant_*` 是"设计 80,000 × 负荷 0.85 →
   68,000 / 8,500 / 59,500"的实际入口工况；`dmfa_yichang_*` 是"时间维存量—流量递推"。
   禁止用稳态单年流量反推历史装机，也禁止把 dMFA 的既有队列释放写成全市未来退役预测。
5. **上限、中间品、可售品三者不可互换**：`reference_material_ceiling`（LCE 3,142.425、FePO4·2H2O 7,986.757 / 5,195.981、
   箔材与镍钴锰盐上限）是物料上限；`recovered_intermediate`（粗碳酸锂湿 1,338.051、磷酸铁渣湿 7,060.243 等）是中间品；
   `saleable_product` 的 9 行数量全为空。C 的 3,000 t LCE 是财务变量，不得当作 A 的产量。
6. **单耗 ≠ 实测量**：98% 硫酸两版本（5,303.312 / 4,617.123）并列不平均；组合电耗 11,232,000 kWh/a 不得除以粉量或 LCE；
   蒸汽只给 t 不转 MJ；天然气只给 Nm³；32% 液碱商品吨 13,788.612 与有效吨 4,412.356 必须同时引用。

## 7. dMFA 表的读法

- 三情景（C065 / C085 / C100）**只改正规收集率 c**；`retired_pack_t` 在三个情景中完全相同——c 不影响退役量。
- `collected_pack_t = c × retired_pack_t`，而 `collected ≠ recycled ≠ park feed`：梯次分流 M01 与
  市域→园区链接 D-PARK-LINK 未解锁，本目录不出现"进入再生"或"园区来料"列。
- `li_in_use_kg` / `li_retired_kg` / `li_collected_kg` 仅对 `chemistry=LFP` 有值；
  未细分三元的 `li_status=null_unresolved_D06-NMC`，**不取 622/811 平均、不填 0**。
- 2026—2040 段的 `mode=closed_historical_cohort_release`，只表示 2010—2025 那批电池的剩余寿命释放；
  对园区的年供给贡献只能表述为"该模型覆盖的既有首装队列贡献"（C085 峰值年 4,094.83 t/a ≈ 6.02% of 68,000）。
- 恒等式：`stock_flow_identity_LFP`、`stock_flow_identity_NMC`、`li_identity_LFP` 均须为 PASS
  （结构残差容差 1e-9；Li 物理口径仍以严格 <5e-4 为上限）。

## 8. 数据来源编号

- `SRC031`：规划来料 8 万 t/a（团体规划假设，见 `a_phase1_ide_handoff.json` → `baseline_inputs`）。
- `SRC039` 等：前段组成代理来源（JR23 系列拆解报告），详见交接包 `sources` 与各组分 `source_ids`。
- `SRC040`：LS23 同源粉料路线（LS 湿法/预处理/固废/药剂系数）。
- `SRC043`：ANL19 三元通用电芯模型（全路线 0.98 恢复率口径，`total material recovered / that material in input cells`）。
- `SRC021`：JIANG24 LFP 中试（双氧水 1.2 m³/2 t 粉料、碳酸钠 750 kg/2 t 粉料；表 6 舍入残差 0.000569 > 5e-4）。
- `SRC042`：ND22 全项目能耗参考（`selected_as_plant_energy=false`，不替代本厂活动量）。
- `NEW-MECH2026`：EV I / EV II 黑粉捕集率（同源 EV 模块手工拆解基准）。
- `NEW-STD-LCE`（YS/T 582-2023）、`NEW-STD-FEP`（HG/T 4701-2021）：电池级碳酸锂与磷酸铁产品标准。
- `NEW-POL2026`、`NEW-CIAAW`（CIAAW 2024 原子量）：政策与化学计量常数。
- `R08-1`：危废与一般固废分类贮存要求（`reference_policies`）。
- `DMFA-S011` / `YC_DMFA01_RECON_V2`：dMFA 首装队列条件重建；`DMFA-S001`（WU 2024，Table S1）：
  Weibull 寿命参数；`DMFA-S002`：正规收集率情景与车型配套锂强度。
  完整条目见 `dmfa_parameters.csv` 的 `source` 列与两个数据集 `sources`。

重新生成：`python code_implementation/run_all.py`（10 个脚本串行，无外网依赖，含 6 张 300 DPI 图）。


---

## 二、成员 B（环境因子 / LCA 环境维度）

# 数据字典与来源声明（Data Sources & Dictionary）

> 本文件声明案例三（第十二讲）方向 B（产业园区/工程尺度）成员 B 所维护数据文件的字段定义、
> 参数取值依据与出处。所有数值均需可溯源；凡标注「占位」者，为骨架阶段以文献量级构造的临时值，
> 待成员 A（工序级 MFA）与成员 C（经济/政策模型）交付后校准，不得作为最终结论引用。

---

## 1. 数据文件清单

| 文件 | 生成方式 | 说明 |
| :--- | :--- | :--- |
| `environmental_factors.csv` | 手工整理 | 单位活动量的 GWP100 与水耗环境因子（成员 B 任务一交付） |
| `scenario_results.csv` | `code_implementation/scenario_analysis.py` 自动生成 | 3267 组工况的参数、环境/经济结果与不可行原因 |

---

## 2. `environmental_factors.csv` 字段字典

| 字段 | 含义 |
| :--- | :--- |
| `factor_id` | 因子唯一编号（PWR/HEAT/RG/TR/PC 前缀） |
| `category` | 因子类别：electricity / heat / reagent / transport / pollution_control |
| `factor_name` | 因子英文名（与 `lca_model.py` 中活动量键对齐） |
| `unit_flow` | 活动量计量单位（kWh / MJ / kg / t·km / m³ / t） |
| `gwp_kgco2e_per_unit` | 单位活动量的 GWP100 上游隐含排放（kg CO₂e） |
| `water_l_per_unit` | 单位活动量的水资源消耗（L） |
| `source` | 参数出处（文献 / 数据库 / 标准） |
| `note` | 补充说明 |

### 2.1 电力因子

| 因子 | GWP (kg CO₂e/kWh) | 水耗 (L/kWh) | 出处 |
| :--- | :---: | :---: | :--- |
| 绿电（风 70% / 光 30%） | 0.035 | 0.20 | IRENA 2020；Ecoinvent 3.9 |
| 区域电网（全国基准） | 0.556 | 2.00 | 文献 6（Ma et al. 2024, *Nat. Commun.* 15:7641）电网因子 0.314–0.749 中值 |
| 高碳电网（煤电为主） | 0.749 | 2.50 | 文献 6 上界 |
| 低碳电网（水电为主） | 0.314 | 1.50 | 文献 6 下界 |

### 2.2 热能因子

| 因子 | GWP (kg CO₂e/MJ) | 水耗 (L/MJ) | 出处 |
| :--- | :---: | :---: | :--- |
| 天然气直燃 | 0.067 | 0.10 | GREET 2021；文献 4（Machala et al. 2025, *Nat. Commun.* 16:988） |
| 中低压蒸汽 | 0.210 | 1.00 | Ecoinvent 3.9（参考值，待自主检索精确化） |

### 2.3 化学试剂因子（上游隐含）

| 因子 | GWP (kg CO₂e/kg) | 水耗 (L/kg) | 出处 |
| :--- | :---: | :---: | :--- |
| 硫酸 H₂SO₄（浸出剂） | 0.150 | 5.00 | Ecoinvent 3.9（参考值，待精确化） |
| 双氧水 H₂O₂（还原剂） | 1.100 | 12.00 | Ecoinvent 3.9（参考值，待精确化） |
| 氢氧化钠 NaOH（中和/共沉淀） | 1.050 | 9.00 | Ecoinvent 3.9（参考值，待精确化） |
| 碳酸钠 Na₂CO₃（沉锂） | 0.950 | 7.00 | Ecoinvent 3.9（参考值，待精确化） |
| 石灰 CaO（除氟/中和） | 0.780 | 3.00 | Ecoinvent 3.9（参考值，待精确化） |

### 2.4 运输与污染治理因子

| 因子 | GWP | 水耗 | 出处 |
| :--- | :---: | :---: | :--- |
| 柴油重卡运输 | 0.120 kg CO₂e/t·km | 0.05 L/t·km | 文献 5（Zhang et al. 2025, *Nat. Commun.* 16:6661）；GREET 2021 |
| 常规废水处理 | 0.300 kg CO₂e/m³ | 0 | Ecoinvent 3.9（参考值，待精确化） |
| 含氟高盐废水深度处理 | 0.800 kg CO₂e/m³ | 0 | GB 31573-2015；文献 4（参考） |
| 危废尾渣固化填埋 | 0.400 kg CO₂e/t | 0.50 L/t | Ecoinvent 3.9（参考值，待精确化） |

---

## 3. 原生矿产基准（1 t 电池级 Li₂CO₃）

| 基准 | GWP (kg CO₂e/t) | 水耗 (L/t) | 出处 |
| :--- | :---: | :---: | :--- |
| 盐湖卤水提锂 | 4000 | 470,000 | 文献 1（Peiseler et al. 2024, *Nat. Commun.* 15:10301）LCE 供应曲线（卤水低排放/高蒸发耗水平台）；公开 LCA 文献量级 |
| 硬岩锂辉石提锂 | 9000 | 170,000 | 文献 1 LCE 供应曲线（锂辉石约为盐湖中位值 3 倍）；公开 LCA 文献量级 |

> 注：两基准的绝对数值为公开 LCA 文献量级的骨架取值，正式撰写第 5 章前须以
> 文献 1 开源仓库（DOI 10.5281/zenodo.13936832）或自主检索的盐湖/锂辉石 LCA 数据精确化。

---

## 4. 政策准入红线参数（成员 C 政策引擎引用）

| 参数 | 阈值 | 出处 |
| :--- | :---: | :--- |
| 冶炼锂回收率 | ≥ 90% | 工信部《新能源汽车废旧动力电池综合利用行业规范条件（2024 年本）》 |
| 镍/钴/锰回收率 | ≥ 98% | 同上 |
| 电极粉料回收率 | ≥ 98% | 同上 |
| 氟固化率 | ≥ 99.5% | 同上 |
| 碳酸锂单位综合能耗 | < 2200 kgce/t | 同上 |
| 工艺废水循环利用率 | ≥ 90% | 同上 |
| 再生锂最低掺混比例 | 6%（2031）/ 12%（2036） | 欧盟 Regulation (EU) 2023/1542 |
| 锂回收率（欧盟阶段目标） | 50%（2027）/ 80%（2031） | 欧盟 Regulation (EU) 2023/1542 |

---

## 5. 外部情景参数（与决策变量分离）

| 参数 | 取值 | 出处 |
| :--- | :---: | :--- |
| 区域电网碳强度 grid_ef | 0.314 / 0.556 / 0.749 kg CO₂e/kWh | 文献 6（Ma et al. 2024） |
| 碳酸锂价格 lithium_price_usd | 10,000 / 22,000 / 50,000 USD/t | 文献 2（Yao et al. 2025, *Nat. Energy* 10:404–416） |
| 工艺能效等级 energy_efficiency | 0.80 / 1.00 / 1.20 | 占位（代表低效/基准/高效产线） |

---

## 6. 占位参数与接口（待成员 A / C 校准）

以下参数为骨架阶段占位值，含来源声明，正式集成前必须替换为实证数据：

| 参数 | 占位值 | 状态 |
| :--- | :--- | :--- |
| 工序活动量 `DEFAULT_ACTIVITIES`（1 t Li₂CO₃ 电/热/试剂/运输/废物） | 见 `lca_model.py` | 待成员 A 工序级 MFA 交付替换 |
| 工艺配比活动量缩放 `build_activities()` | 见 `scenario_analysis.py` | 同上 |
| 锂回收率–工艺配比映射（0.90 + 0.09·pm） | 占位线性式 | 待成员 A 回收率数据校准 |
| LCOR 成本项（电价、试剂、工艺溢价） | 见 `lcor_stub()` | 待成员 C 经济模型替换 |
| 汇率 USD_CNY = 7.2 | 占位 | 待财务口径统一 |
| 折标系数（1 kWh=0.1229 kgce 等） | 标准值 | GB/T 2589 综合能耗计算通则 |

---

## 7. 自主检索与合规参考（需成员补充不少于 4 项）

1. 工信部《新能源汽车废旧动力电池综合利用行业规范条件（2024 年本）》（工信部公告 2024 年第 42 号）
2. 欧盟《电池与废电池法规》Regulation (EU) 2023/1542
3. GB/T 33598-2017《车用动力电池回收利用 拆解规范》
4. GB 31573-2015《无机化学工业污染物排放标准》
5. GB/T 2589《综合能耗计算通则》（折标系数依据）
6. 文献 4 开源仓库（OSF: `zvame`）与文献 1 开源仓库（Zenodo 13936832）

---

## 三、成员 C（经济参数 / LCOR·MAC / 政策引擎）

C 的数据位于 `data_cohort/` 顶层与 `data_cohort/final_20261104/`，文件清单：

- `final_20261104\cost_breakdown_base.csv`
- `final_20261104\economic_parameters.csv`
- `final_20261104\economic_parameters_final.csv`
- `final_20261104\environmental_inventory_R1.csv`
- `final_20261104\key_cases.csv`
- `final_20261104\lfp_wet_stage_balance.csv`
- `final_20261104\mass_balance_checks.csv`
- `final_20261104\material_flow_R1.csv`
- `final_20261104\policy_parameters.json`
- `final_20261104\product_credits_R1.csv`
- `final_20261104\revenue_breakdown_base.csv`
- `final_20261104\scenarios_final.csv`
- `final_20261104\sensitivity_final.csv`
- `final_20261104\source_register.csv`
- `final_20261104\summary.json`
- `policy_parameters.json`
- `tea_case_template.json`

价格证据以 `final_20261104/` 内价格/来源登记为准；政策阈值与任务书口径见 `policy_parameters.json`；情景全集与最终结果见 `final_20261104/scenarios_final.csv`。

---

## 四、统一口径（R1）

- 规划情景 R1：再生入口 **60,579.50 t/a**、LCE-eq 产量基数三方一致。
- 未分配 Li 损耗拆分口径差异见 `report/Environmental_Planning_Report.md` 附录第 7 项，需组长裁定统一。
