# 参考文献与数据来源索引（references index）

> 本索引汇总最终报告《Environmental_Planning_Report.md》第 7 章引用的全部参考文献与原始源文件，
> 供评审按图索骥。相对路径均以本文件所在目录（`report/`）为基准。

---

## 一、预编译核心文献（任务书 §2.1，文献 1–6，PDF 全文）

六篇 2024—2025 年学术论文原文已复制至 `references/` 目录，与报告第 7.1 节逐一对应：

| 报告编号 | 著录（第一作者·年份·期刊·卷:文号） | 原文 PDF（相对 report/） |
| :--- | :--- | :--- |
| 文献 1 | Peiseler L, et al. (2024). *Nature Communications*, 15:10301 | `references/Carbon footprint distributions of lithium-ion batteries and their materials.pdf` |
| 文献 2 | Yao Z, Benson S M, Chueh W C (2025). *Nature Energy*, 10:404–416 | `references/Critically assessing sodium-ion technology roadmaps and scenarios for techno-economic competitiveness against lithium-ion batteries.pdf` |
| 文献 3 | Wu Y, et al. (2024). *Communications Earth & Environment*, 5:503 | `references/Impact of circular economy on the long-term allocation structure of primary and secondary lithium.pdf` |
| 文献 4 | Machala M, et al. (2025). *Nature Communications*, 16:988 | `references/Life cycle comparison of industrial-scale lithium-ion battery recycling and mining supply chains.pdf` |
| 文献 5 | Zhang B, et al. (2025). *Nature Communications*, 16:6661 | `references/Lithium-ion battery recycling relieves the threat to material scarcity amid China’s electric vehicle ambitions.pdf` |
| 文献 6 | Ma R, et al. (2024). *Nature Communications*, 15:7641 | `references/Pathway decisions for reuse and recycling of retired lithium-ion batteries considering economic and environmental functions.pdf` |

---

## 二、成员方源文件溯源

| 归属 | 源文件 | 相对路径（相对 report/） | 报告引用 |
| :--- | :--- | :--- | :--- |
| A | 最终采用数据来源与参考文献 | `references/A_最终采用数据来源与参考文献_20261104.md` | §7.2 |
| A | 三方合并数据来源与溯源登记 | `../data_cohort/README_data_sources.md` | §7.3、§7.5 |
| B | 环境排放因子清单 | `../data_cohort/environmental_factors.csv` | §7.3 |
| B | 中期建模说明 | `../drafts/B_B_中期建模说明.md` | §7.3 |
| C | 经济参数与来源登记 | `../data_cohort/final_20261104/source_register.csv` | §7.4 |
| C | 经济参数终表 | `../data_cohort/final_20261104/economic_parameters_final.csv` | §7.4 |
| C | 政策红线阈值 | `../data_cohort/final_20261104/policy_parameters.json` | §7.4 |
| C | 绿电数据来源、方法与假设登记 | `references/green_electricity_sources.md` | §7.6 |

---

## 三、报告正文引用的交叉数据文件

| 用途 | 相对路径（相对 report/） | 引用位置 |
| :--- | :--- | :--- |
| 园区物料流（33 条流股） | `../data_cohort/final_20261104/material_flow_R1.csv` | §2.3、§3.2 |
| 质量平衡校核 | `../data_cohort/final_20261104/mass_balance_checks.csv` | §3.2 |
| 重点工程投资与关键工况 | `../data_cohort/final_20261104/key_cases.csv` | §4.3 |
| 年度运营费用明细 | `../data_cohort/final_20261104/cost_breakdown_base.csv` | §4.4 |
| 经济参数与情景全集 | `../data_cohort/final_20261104/scenarios_final.csv` | §5.3 |
| 绿电比例对照（50/80/100%） | `../data_cohort/final_20261104/green_ratio_comparison.csv` | §5.4 |
| 水电季节形状（R3–R6） | `../data_cohort/final_20261104/hydro_seasonal_shape.csv` | §5.4 |
| 绿电情景调度（A/B/C/D） | `../data_cohort/final_20261104/seasonal_green_dispatch.csv` | §5.4 |
| 投资成本明细草稿 | `../drafts/C_final_20261104_ch04_investment_cost.md` | §4.3 |

---

## 四、自主拓展检索（不少于 4 项，详见报告 §7）

1. 工业和信息化部《新能源汽车废旧动力电池综合利用行业规范条件（2024 年本）》（公告 2024 年第 42 号，2025-01-01 施行）
2. 欧盟《电池与废电池法规》Regulation (EU) 2023/1542
3. GB 31573-2015《无机化学工业污染物排放标准》
4. GB/T 2589《综合能耗计算通则》
5. 湖南朗赛/湖南金瑞废旧磷酸铁锂电池回收项目环境影响报告书（2023）
6. ANL EverBatt 回收成本与环境影响模型（2019）、JRC 梯次利用可持续评估（2018）、CIAAW 原子量（2024）

### 绿电比例改进新增来源（R1–R7，见 §7.6）

| 编号 | 来源 | URL | 用途 |
| :--- | :--- | :--- | :--- |
| R1 | 国家能源局华中监管局, 湖北省发改委, 湖北省能源局. 湖北省电力中长期市场实施细则 | https://hzj.nea.gov.cn/dtyw/tzgg/202604/t20260414_299623.html | 绿电交易周期/双边协商24时段/环境价值结算量取小（第58/59/98条、附件绿色电力） |
| R2 | 国家能源局. 可再生能源绿色电力证书管理实施细则（试行） | https://henb.nea.gov.cn/xxgk/zcfg/202602/t20260203_295284.html | 绿证=1,000 kWh/存量水电划转/生产消费年份一致（第16/24/31条） |
| R3 | 中国长江电力. 2025年第一季度发电量完成情况公告 | https://static.cninfo.com.cn/finalpage/2025-04-08/1223023068.PDF | 三峡/葛洲坝 Q1 发电量（季节形状） |
| R4 | 中国长江电力. 2025年第二季度发电量完成情况公告 | https://static.cninfo.com.cn/finalpage/2025-07-10/1224117796.PDF | 三峡/葛洲坝 Q2 发电量（季节形状） |
| R5 | 中国长江电力. 2025年第三季度发电量完成情况公告 | https://static.cninfo.com.cn/finalpage/2025-10-13/1224707186.PDF | 三峡/葛洲坝 Q3 发电量（季节形状） |
| R6 | 中国长江电力. 2025年第四季度发电量完成情况公告 | https://static.cninfo.com.cn/finalpage/2026-01-06/1224918156.PDF | 三峡/葛洲坝 Q4 发电量（季节形状） |
| R7 | 生态环境部, 国家统计局, 国家能源局. 2024年全国电力碳足迹因子 | https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202510/W020251024569470952545.pdf | 全国电力/水/风/光/输配电碳足迹因子 |

> 上述 R1–R7 的参数级元数据与「官方原值 / 单位换算 / 研究者分配 / 组内假设 / 模型输出 / 未取得」区分见 [green_electricity_sources.md](references/green_electricity_sources.md)。