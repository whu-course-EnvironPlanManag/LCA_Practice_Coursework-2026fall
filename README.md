# 《环境规划与管理》实践作业大仓 (2026 Fall)

欢迎来到武汉大学《环境规划与管理》2026 秋季学期课程实践作业仓库！

本仓库采用**年度统一大仓（Annual Monorepo）**架构，全班 15 位同学共划分为 5 个实践小组（每组均为 3 人标准规模），所有课程实践任务包分发、随堂带练与课后小组作业均在此统一协同完成。

---

## 📂 仓库目录结构

```text
LCA_Practice_Coursework-2026fall/
├── starter_materials/                  # 【教师任务发布区 (学生只读，按任务包独立自治)】
│   └── practice2_brightway2.5/         # 瓶装水 LCA 实践任务包 (环境配置、数据清单、答题卡一体化自治)
│       ├── env_bw25.yml                # 本任务专属 Conda 依赖环境清单
│       ├── practice2.ipynb             # 核心答题卡与模型
│       ├── tutorial_documentation.md   # 实操指导手册
│       └── data_collections/           # 前景清单与关联数据 (Excel)
├── groups/                             # 【学生专属区 (各组完全物理隔离)】
│   ├── group-01/                       # 第 1 小组工作空间 (3人)
│   ├── group-02/                       # 第 2 小组工作空间 (3人)
│   ├── group-03/                       # 第 3 小组工作空间 (3人)
│   ├── group-04/                       # 第 4 小组工作空间 (3人)
│   └── group-05/                       # 第 5 小组工作空间 (3人)
├── .github/workflows/                  # 【自动化质量守卫】越界修改自动拦截 CI
├── .gitignore                          # 忽略临时缓存、大文件与虚拟环境
└── README.md                           # 本指南说明
```

---

## 👥 小组划分概览

全班 15 位同学共划分为 5 个实践小组（每组均为 3 人标准规模）：

| 小组编号 | 组员规模 | 组员名单（组员 · 邮箱） | 组内专属目录 | 组长 / 协调人 | 分工与说明 |
| :---: | :---: | :--- | :---: | :---: | :--- |
| **Group 01** | 3 人 | 曾飞杨（曾飞楊，组长 · `1402038948@qq.com`）<br/>陈海滨 (`482029164@qq.com`)<br/>张宏生 (`3454750195@qq.com`) | `groups/group-01/` | 曾飞杨 | 清单校验 / 核心建模 / LCIA 可视化报告 |
| **Group 02** | 3 人 | 强浩峻（组长 · `2245683701@qq.com`）<br/>郭京奥 (`2584278761@qq.com`)<br/>帕娜尔·阿克木 (`2603825979@qq.com`) | `groups/group-02/` | 强浩峻 | 清单校验 / 核心建模 / LCIA 可视化报告 |
| **Group 03** | 3 人 | 白玛卓吉（组长 · `3600138408@qq.com`）<br/>拉姆卓嘎 (`（隐私保护已隐藏）`)<br/>麦迪乃姆·亚森 (`3351939742@qq.com`) | `groups/group-03/` | 白玛卓吉 | 清单校验 / 核心建模 / LCIA 可视化报告 |
| **Group 04** | 3 人 | 邱自强（组长 · `3138654118@qq.com`）<br/>彭冬明 (`PDMMCC@outlook.com`)<br/>边久加措 (`3198599582@qq.com`) | `groups/group-04/` | 邱自强 | 清单校验 / 核心建模 / LCIA 可视化报告 |
| **Group 05** | 3 人 | 明子骅（组长 · `helloxmtx@gmail.com`）<br/>陈和兴 (待补充邮箱)<br/>张晓璐 (`1820433574@qq.com`) | `groups/group-05/` | 明子骅 | 清单校验 / 核心建模 / LCIA 可视化报告 |

---

## 🚀 极速上手：学生作业全流程（三步法）

### 第一步：配置 Brightway 2.5 运行环境（只需一次）
打开 Anaconda Prompt 或终端，在仓库根目录下执行：
```bash
# 1. 基于第六讲任务包内置配置文件创建 Conda 虚拟环境
conda env create -f starter_materials/practice2_brightway2.5/env_bw25.yml

# 2. 激活环境并启动 Jupyter Lab
conda activate env_bw25
jupyter lab
```

### 第二步：领取任务包至本组专属目录
进入本组专属工作区，从公共课件区复制对应的实操练习包：
```bash
# 以第 1 组为例：
cd groups/group-01/

# 复制第六讲任务包到本组目录下
cp -r ../../starter_materials/practice2_brightway2.5 ./
```

### 第三步：组内分工协作与成果提交（含各组极简端到端示例）

为帮助非计算机专业同学顺利协作、避免代码与文件冲突，请遵循**「组内文件解耦 + 单一专属分支提交」**原则。

#### 💡 组内协作防冲突黄金准则（新手必读）
1. **不要两人同时修改同一个 `.ipynb`**：Jupyter Notebook 底层是复杂的 JSON 格式，若两人同时编辑同一文件，极易产生难以解决的代码冲突。
2. **组内文件粒度分工推荐**：
   * **负责建模的同学**：在 `practice2_brightway2.5/practice2.ipynb` 中运行并编写核心建模代码。
   * **负责数据的同学**：在 `data_collections/` 中核对并更新前台清单 Excel。
   * **负责报告与分析的同学**：将敏感度分析、结果解读与图表总结整理于组内的 `README.md` 或独立的报告 Markdown/Word 中。
3. **提交与推送**：建议每组由**组长或指定一人**汇总核对后统一提交，或组员完成各自专属文件后依次提交。

---

#### 📌 全班 5 个小组提交实操指南（请找到本组直接复制执行）

<details open>
<summary><b>👉 【第 1 小组 (Group 01)】实操示范（曾飞杨、陈海滨、张宏生）</b></summary>

* **组内分工**：曾飞杨（统筹核对清单与最终 PR）｜ 陈海滨（`practice2.ipynb` 核心建模）｜ 张宏生（LCIA 计算与结果可视化）
* **终端操作（打开终端/Anaconda Prompt 执行）：**
  ```bash
  # 1. 确保处于仓库根目录，先拉取远端最新状态
  git pull origin main

  # 2. 领取任务包到第 1 组（若此前未领取过）
  cd groups/group-01/
  cp -r ../../starter_materials/practice2_brightway2.5 ./

  # 3. 完成作业后，创建并切换至第 1 组专属分支
  git checkout -b dev-group-01

  # 4. 仅暂存第 1 组目录下的成果（铁律：只 add 自己的目录）
  git add .

  # 5. 提交并附带规范备注
  git commit -m "submit(group-01): 第1组完成第六讲 Brightway 实践作业"

  # 6. 推送至 GitHub 远端本组专属分支
  git push origin dev-group-01
  ```
</details>

<details open>
<summary><b>👉 【第 2 小组 (Group 02)】实操示范（强浩峻、郭京奥、帕娜尔·阿克木）</b></summary>

* **组内分工**：强浩峻（统筹核对清单与最终 PR）｜ 郭京奥（`practice2.ipynb` 核心建模）｜ 帕娜尔·阿克木（LCIA 计算与结果可视化）
* **终端操作（打开终端/Anaconda Prompt 执行）：**
  ```bash
  # 1. 确保处于仓库根目录，先拉取远端最新状态
  git pull origin main

  # 2. 领取任务包到第 2 组（若此前未领取过）
  cd groups/group-02/
  cp -r ../../starter_materials/practice2_brightway2.5 ./

  # 3. 完成作业后，创建并切换至第 2 组专属分支
  git checkout -b dev-group-02

  # 4. 仅暂存第 2 组目录下的成果（铁律：只 add 自己的目录）
  git add .

  # 5. 提交并附带规范备注
  git commit -m "submit(group-02): 第2组完成第六讲 Brightway 实践作业"

  # 6. 推送至 GitHub 远端本组专属分支
  git push origin dev-group-02
  ```
</details>

<details open>
<summary><b>👉 【第 3 小组 (Group 03)】实操示范（白玛卓吉、拉姆卓嘎、麦迪乃姆·亚森）</b></summary>

* **组内分工**：白玛卓吉（统筹核对清单与最终 PR）｜ 拉姆卓嘎（`practice2.ipynb` 核心建模）｜ 麦迪乃姆·亚森（LCIA 计算与结果可视化）
* **终端操作（打开终端/Anaconda Prompt 执行）：**
  ```bash
  # 1. 确保处于仓库根目录，先拉取远端最新状态
  git pull origin main

  # 2. 领取任务包到第 3 组（若此前未领取过）
  cd groups/group-03/
  cp -r ../../starter_materials/practice2_brightway2.5 ./

  # 3. 完成作业后，创建并切换至第 3 组专属分支
  git checkout -b dev-group-03

  # 4. 仅暂存第 3 组目录下的成果（铁律：只 add 自己的目录）
  git add .

  # 5. 提交并附带规范备注
  git commit -m "submit(group-03): 第3组完成第六讲 Brightway 实践作业"

  # 6. 推送至 GitHub 远端本组专属分支
  git push origin dev-group-03
  ```
</details>

<details open>
<summary><b>👉 【第 4 小组 (Group 04)】实操示范（邱自强、彭冬明、边久加措）</b></summary>

* **组内分工**：邱自强（统筹核对清单与最终 PR）｜ 彭冬明（`practice2.ipynb` 核心建模）｜ 边久加措（LCIA 计算与结果可视化）
* **终端操作（打开终端/Anaconda Prompt 执行）：**
  ```bash
  # 1. 确保处于仓库根目录，先拉取远端最新状态
  git pull origin main

  # 2. 领取任务包到第 4 组（若此前未领取过）
  cd groups/group-04/
  cp -r ../../starter_materials/practice2_brightway2.5 ./

  # 3. 完成作业后，创建并切换至第 4 组专属分支
  git checkout -b dev-group-04

  # 4. 仅暂存第 4 组目录下的成果（铁律：只 add 自己的目录）
  git add .

  # 5. 提交并附带规范备注
  git commit -m "submit(group-04): 第4组完成第六讲 Brightway 实践作业"

  # 6. 推送至 GitHub 远端本组专属分支
  git push origin dev-group-04
  ```
</details>

<details open>
<summary><b>👉 【第 5 小组 (Group 05)】实操示范（明子骅、陈和兴、张晓璐）</b></summary>

* **组内分工**：明子骅（统筹核对清单与最终 PR）｜ 陈和兴（`practice2.ipynb` 核心建模）｜ 张晓璐（LCIA 计算与结果可视化）
* **终端操作（打开终端/Anaconda Prompt 执行）：**
  ```bash
  # 1. 确保处于仓库根目录，先拉取远端最新状态
  git pull origin main

  # 2. 领取任务包到第 5 组（若此前未领取过）
  cd groups/group-05/
  cp -r ../../starter_materials/practice2_brightway2.5 ./

  # 3. 完成作业后，创建并切换至第 5 组专属分支
  git checkout -b dev-group-05

  # 4. 仅暂存第 5 组目录下的成果（铁律：只 add 自己的目录）
  git add .

  # 5. 提交并附带规范备注
  git commit -m "submit(group-05): 第5组完成第六讲 Brightway 实践作业"

  # 6. 推送至 GitHub 远端本组专属分支
  git push origin dev-group-05
  ```
</details>

---

#### 🌐 网页端发起 Pull Request（四步合并指引）

推送成功后，请由组长打开 GitHub 仓库网页完成最终成果提交：

1. **进入仓库首页**：访问 [whu-course-EnvironPlanManag/LCA_Practice_Coursework-2026fall](https://github.com/whu-course-EnvironPlanManag/LCA_Practice_Coursework-2026fall)。
2. **点击发起 PR**：首页顶部会出现黄色提示框 `dev-group-0X had recent pushes ...`，直接点击右侧绿色的 **Compare & pull request** 按钮。
3. **核验分支方向**：
   * `base repository: .../LCA_Practice_Coursework-2026fall` ➔ `base: main`
   * `head repository: .../LCA_Practice_Coursework-2026fall` ➔ `compare: dev-group-0X`
4. **填写并提交**：
   * 标题填写：`[Group 0X] 提交第六讲实践作业`
   * 点击 **Create pull request** 绿色按钮。
5. **自动化质量检查**：页面会自动运行机器人卫士（`.github/workflows/boundary_check.yml`）。若全绿通过 ✅，说明改动完全在专属组目录内，老师/助教即可在线审阅合并；若出现 ❌，请点击 Details 查看是否误改了组外文件。

---

## ⚠️ 协同铁律与防冲突规范

1. **绝对禁止跨组越界**：
   * 各组同学**仅允许**在自己的专属目录（如 `groups/group-01/`）内新增和修改文件。
   * 严禁修改其他小组目录或公共目录 `starter_materials/`（仓库已配置 GitHub Actions 自动守卫，跨组与越界改动将被自动拦截并阻断合并）。
2. **组内文件粒度解耦（防 Jupyter Notebook 冲突）**：
   * Jupyter Notebook（`.ipynb`）文件为复杂 JSON 结构，多人同时修改同一文件极易产生难以修复的代码冲突。
   * **铁律**：组内多位同学务必根据分工分别负责不同的 `.ipynb` 或数据 Excel，避免两人同时改动同一个文件。
3. **严禁提交大文件与缓存**：
   * 请勿提交大型未压缩数据包（> 25MB）、Python 缓存或 `.ipynb_checkpoints` 临时文件夹（已配置 `.gitignore` 自动过滤）。
