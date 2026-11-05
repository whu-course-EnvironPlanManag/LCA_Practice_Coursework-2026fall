# 第 3 实践小组（Group 03）工作空间

- **所属课程**：《环境规划与管理》（2026 秋季学期）
- **小组规模**：3 人
- **本组专属工作目录**：`groups/group-03/`

---

## 1. 组员分工表

| 序号 | 姓名 | GitHub 绑定邮箱 / 账号 | 角色定位 | 组内任务分工 |
| :---: | :---: | :---: | :---: | :--- |
| 1 | 白玛卓吉 | `3600138408@qq.com` | 组长 / 协调 | 前台数据清单校核、分支合并与汇总 PR |
| 2 | 拉姆卓嘎 | `（隐私保护已隐藏）` | 核心组员 | Brightway 核心建模、数据库活动链接与矩阵构建 |
| 3 | 麦迪乃姆·亚森 | `3351939742@qq.com` | 核心组员 | LCIA 特征化计算、敏感度分析与结果可视化报告 |

---

## 2. 组内协同指南与防冲突铁律

1. **工作边界**：本组所有代码、数据与文档仅在 `groups/group-03/` 目录下新增与修改，**严禁修改其他小组目录或 `starter_materials/` 目录**。
2. **防冲突解耦**：三位同学请根据分工分别负责不同的 `.ipynb` 或数据 Excel。**切勿两人同时修改同一个文件**。
3. **提交规范**：
   ```zsh
   # 1. 切换到本组工作目录
   cd groups/group-03/

   # 2. 从 starter_materials 复制需要实操的任务包
   cp -r ../../starter_materials/practice2_brightway2.5 ./

   # 3. 提交本组成果至本组专属分支
   git checkout -b dev-group-03
   git add .
   git commit -m "feat(group-03): 完成第六讲 Brightway LCA 实践练习"
   git push origin dev-group-03
   ```
## 环境配置

- 操作系统：macOS（Apple Silicon）
- conda 环境：`bw25`（Python 3.11.17）
- 核心依赖：bw2data 4.7、bw2calc 2.4.0、bw2io、bw2analyzer、bw_processing、matrix_utils
- 运行方式：VS Code Jupyter Notebook，内核选择 `bw25`

## 运行说明

1. 进入 `groups/group-03/practice2_brightway2.5/`
2. 激活环境：`conda activate bw25`
3. 用 VS Code 打开 `practice2.ipynb`，选择内核 `bw25 (Python 3.11.17)`
4. Run All 依次运行 9 个步骤
5. 生成成果：`lcia_results_practice2.xlsx`（5 个工作表）

## 结果解读

### 1. 多指标环境影响概览（1_MultiLCA_Overview）

| 评价体系 | 环境影响类别 | 1L 瓶装水全生命周期 | 单个塑料水瓶包装制备 |
| :--- | :--- | :--- | :--- |
| EF v3.0 | climate change (GWP100) | 0.131643 kg CO2-eq | 0.123093 kg CO2-eq |
| IPCC 2021 | climate change (GWP100) | 0.131227 kg CO2-eq | 0.122677 kg CO2-eq |
| EF v3.0 | water use | 0.077648 m3 | 0.027008 m3 |
| EF v3.0 | acidification (AE) | 8.38e-05 | 8.38e-05 |

结论：1L 瓶装水全生命周期碳足迹约 0.132 kg CO2-eq，其中塑料水瓶包装贡献约 93.5%，**包装环节是碳足迹的主要来源**。

### 2. 工序贡献度分析（2_Process_Contributions）

| 工序 | 绝对贡献 (kg CO2-eq) | 贡献比例 |
| :--- | :--- | :--- |
| PET 瓶级颗粒生产 | 0.073568 | 55.88% |
| 吹塑成型 | 0.027200 | 20.66% |
| 中压电力 | 0.017325 | 13.16% |
| 货运 (16-32t EURO5) | 0.008250 | 6.27% |
| 水瓶生产 | 0.005000 | 3.80% |
| 自来水生产 | 0.000300 | 0.23% |

结论：**PET 树脂原材料占比超一半**，是减碳的首要抓手；包装制造（吹塑+电）合计约 1/3。

### 3. 脱碳情景敏感性分析（3_Decarbonization_Scenarios）

| 情景 | 碳足迹 (kg CO2-eq) | 相对基准降碳 |
| :--- | :--- | :--- |
| 基准 (100% 原生 PET, 32g) | 0.131643 | 0% |
| 轻量化 20% (25.6g) | 0.111489 | -15.31% |
| 50% 再生料 rPET | 0.107733 | -18.16% |
| 轻量化 20% + 70% rPET | 0.089860 | -31.74% |

结论：轻量化与再生料**组合可降碳约 1/3**，包装工程改进潜力显著。

### 4. 蒙特卡洛不确定性分析（5_Monte_Carlo_Distribution）

- 样本数：500 次
- 均值：0.1315 kg CO2-eq；中位数：0.1306 kg CO2-eq
- 95% 置信区间：[0.116, 0.151] kg CO2-eq

结论：碳足迹结果存在约 ±13% 的不确定性区间，主要来自 PET 原料单耗的对数正态分布设定。

## 关键产出文件

| 文件 | 说明 |
| :--- | :--- |
| practice2.ipynb | 完整 9 步骤运行脚本 |
| lcia_results_practice2.xlsx | 5 个工作表结果汇总 |
| lcia_results_practice2-Reference-ONLY.xlsx | 教师基准参考（对照验证一致） |

## 遇到的问题与解决

1. ARM 架构缺少 scikit-umfpack：仅性能警告，不影响计算正确性
2. bw25 环境未安装 jupyterlab：改用 VS Code 内核直接运行，无需补装