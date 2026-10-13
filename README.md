# 《环境规划与管理》实践作业大仓 (2026 Fall)

欢迎来到武汉大学《环境规划与管理》2026 秋季学期课程实践作业仓库！

本仓库采用**年度统一大仓（Annual Monorepo）**架构，全班 14 位同学共划分为 5 个实践小组，所有课程实践任务包分发、随堂带练与课后小组作业均在此统一协同完成。

---

## 📂 仓库目录结构

```text
LCA_Practice_Coursework-2026fall/
├── starter_materials/                  # 【教师任务发布区 (学生只读)】
│   ├── env_bw25.yml                    # 统一 Conda 依赖环境配置
│   └── practice2_brightway2.5/         # 瓶装水 LCA 实践任务包 (课件、Excel前台清单、答题卡)
├── groups/                             # 【学生专属区 (各组完全物理隔离)】
│   ├── group-01/                       # 第 1 小组工作空间 (3人)
│   ├── group-02/                       # 第 2 小组工作空间 (3人)
│   ├── group-03/                       # 第 3 小组工作空间 (3人)
│   ├── group-04/                       # 第 4 小组工作空间 (3人)
│   └── group-05/                       # 第 5 小组工作空间 (2人)
├── .github/workflows/                  # 【自动化质量守卫】越界修改自动拦截 CI
├── .gitignore                          # 忽略临时缓存、大文件与虚拟环境
└── README.md                           # 本指南说明
```

---

## 👥 小组划分概览

全班 14 位同学分为 5 个实践小组（规模为 3、3、3、3、2 人）：

| 小组编号 | 组员规模 | 组内专属目录 | 组长 / 协调人 | 分工与说明 |
| :---: | :---: | :---: | :---: | :--- |
| **Group 01** | 3 人 | `groups/group-01/` | 见组内 README | 清单校验 / 核心建模 / LCIA 可视化报告 |
| **Group 02** | 3 人 | `groups/group-02/` | 见组内 README | 清单校验 / 核心建模 / LCIA 可视化报告 |
| **Group 03** | 3 人 | `groups/group-03/` | 见组内 README | 清单校验 / 核心建模 / LCIA 可视化报告 |
| **Group 04** | 3 人 | `groups/group-04/` | 见组内 README | 清单校验 / 核心建模 / LCIA 可视化报告 |
| **Group 05** | 2 人 | `groups/group-05/` | 见组内 README | 前台清单与建模 / 评价计算与报告解读 |

---

## 🚀 极速上手：学生作业全流程（三步法）

### 第一步：配置 Brightway 2.5 运行环境（只需一次）
打开 Anaconda Prompt 或终端，在仓库根目录下执行：
```bash
# 1. 基于标准配置文件创建 Conda 虚拟环境
conda env create -f starter_materials/env_bw25.yml

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

### 第三步：组内分工协作与成果提交
在 Jupyter Lab 中打开 `groups/group-XX/` 下的答题卡 Notebook，组内分工协同完成。
完成后在终端提交本组成果：
```bash
git add groups/group-01/
git commit -m "submit(group-01): 完成第六讲 Brightway LCA 实践作业"
git push origin main
```
> 💡 建议在 GitHub 网页端通过发起 Pull Request（如 `dev-group-01` ➔ `main`）提交，由老师或助教在线审核与合并。

---

## ⚠️ 协同铁律与防冲突规范

1. **绝对禁止跨组越界**：
   * 各组同学**仅允许**在自己的专属目录（如 `groups/group-01/`）内新增和修改文件。
   * 严禁修改其他小组目录或公共目录 `starter_materials/`（仓库已配置 GitHub Actions 自动守卫，跨组改动将被自动拦截并阻断合并）。
2. **组内文件粒度解耦（防 Jupyter Notebook 冲突）**：
   * Jupyter Notebook（`.ipynb`）文件为复杂 JSON 结构，多人同时修改同一文件极易产生难以修复的代码冲突。
   * **铁律**：组内多位同学务必根据分工分别负责不同的 `.ipynb` 或数据 Excel，避免两人同时改动同一个文件。
3. **严禁提交大文件与缓存**：
   * 请勿提交大型未压缩数据包（> 25MB）、Python 缓存或 `.ipynb_checkpoints` 临时文件夹（已配置 `.gitignore` 自动过滤）。
