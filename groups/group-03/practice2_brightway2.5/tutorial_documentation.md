# Brightway 2.5 实践教学综合文档 (Practice 2: 瓶装水与包装制造 LCA)

---

## 0. 教学包目录结构与文件说明 (Directory Structure)

本目录为《Brightway 2.5 进阶实践教程：瓶装饮用水与塑料水瓶生产 LCA 分析》的标准教学演示包。全流程严格遵循官方教程规范与**自适应相对路径**设计，解压到任意目录均可即开即用、零报错运行。

### 0.1 目录树状图

```text
practice2_brightway2.5/
│
├── practice2.ipynb                            # 【主实操文件】教学演示 Jupyter Notebook（含 9 个完整实操步骤）
│
├── data_collections/                          # 【数据源目录】包含生命周期清单（LCI）Excel 原始数据与环境配置文件
│   ├── env_bw25.yml                           # 【官方环境配置】官方标准 Conda 依赖包清单（支持一键克隆复现环境）
│   ├── excel_importer_example.xlsx            # 官方案例：饮用水与水瓶生产前台清单（标准全链接格式）
│   └── excel_importer_example_w_unlinked.xlsx # 教学排错：含有单位不匹配（piece vs unit）的清单（用于排错实操）
│
├── tutorial_documentation.md                  # 【教学与技术文档】本手册（目录说明、环境配置、BW2 vs BW2.5 核心差异、故障排除等）
└── lcia_results_practice2-Reference-ONLY.xlsx # 【基准参考结果】计算结果标准对照表（随堂运行时将另行导出 lcia_results_practice2.xlsx）
```

### 0.2 文件与目录功能清单

| 文件 / 文件夹 | 类型 | 说明与教学要点 |
| :--- | :--- | :--- |
| **`practice2.ipynb`** | 实操主线 | **课堂随堂演示主文件**。涵盖 Brightway 2.5 全流程：Windows 求解器补丁、免 Ecoinvent 自适应背景库构建（方案 1）、前景清单策略导入、未匹配流诊断修复、单工序 LCIA 计算、全新 2024 MultiLCA 批量求解、底层矩阵解构、贡献度溯源与蒙特卡洛不确定性模拟。 |
| **`data_collections/`** | 关键输入 | **数据与配置文件夹**。代码通过相对路径 `data_collections/...` 访问，教学中不可重命名此文件夹或其内部文件。 |
| ├─ `env_bw25.yml` | 环境规范 | **官方标准环境配置文件**。基于官方 GitHub 规范并补齐 Pandas、Openpyxl、Seaborn，支持 `conda env create -f ...` 极速复现环境。 |
| ├─ `excel_importer_example.xlsx` | 基础数据 | 官方教程同款前台清单数据，包含 1L 瓶装饮用水制备及 PET 塑料水瓶注塑成型工序。 |
| └─ `excel_importer_example_w_unlinked.xlsx` | 排错素材 | 故意留有单位书写不一致（`piece` vs `unit`），用于带学生体验 `imp.statistics()` 与 `imp.unlinked` 诊断及动态修复过程。 |
| **`tutorial_documentation.md`** | 教学文档 | **技术与环境保障手册**。包含本目录架构说明、BW2 到 BW2.5 架构差异深度解析、3 种 Conda 环境搭建方案、求解器补丁说明与排错 FAQ。 |
| **`lcia_results_practice2-Reference-ONLY.xlsx`** | 基准参考 | **标准结果对照表**。供教师备课对账或作为标准答案。随堂执行第 8、9 步代码时将导出包含 5 个工作表（多指标概览、工序贡献度明细、脱碳情景敏感性、关键排放清单、500 次蒙特卡洛抽样分布）的全新 `lcia_results_practice2.xlsx`。 |

---

## 1. Brightway 2 到 Brightway 2.5 核心变革深度剖析

Brightway 2.5 不是对 Brightway 2 的简单小幅升级，而是一次**重塑 LCA 计算架构的代际跃迁**。理解这一架构转变是高校师生和科研人员掌握现代 LCA 工具的关键。

### 1.1 从“面向结构 (Structure-centric)”到“面向数据 (Data-centric)”

- **Brightway 2 的局限**：
  在 BW2 中，计算核心 `bw2calc` 与对象关系映射库 `Peewee` / SQLite 高度耦合。每当需要构建技术矩阵 $\mathbf{A}$ 或基本流矩阵 $\mathbf{B}$ 时，求解器必须频繁遍历关系型数据库中的节点（Activity）与连接边（Exchange）。对于几万个活动的大型背景库（如完整 Ecoinvent），数据库查询与矩阵索引映射成为严重性能瓶颈。
- **Brightway 2.5 的突破**：
  BW2.5 彻底将**数据元数据管理**与**矩阵数值运算**解耦：
  1. 引入了标准化的数据包格式——**`datapackages`** 与底层库 **`bw_processing`**。
  2. 矩阵结构完全由结构化 NumPy 数组（Row, Col, Data, Uncertainty Metadata）表示，支持直接从磁盘 `.zip` 文件流式加载或在内存中直接生成。
  3. 计算模块 `bw2calc` 不再需要读取任何关系型数据库，只要传入符合格式的 `data_objs` 即可瞬间完成矩阵装配与求解。

### 1.2 核心 API 与调用方式演变对照表

| 核心功能环节 | Brightway 2 经典做法 | Brightway 2.5 现代做法 | 优势与设计意图 |
| :--- | :--- | :--- | :--- |
| **单工序 LCA 初始化** | `lca = LCA({act: 1}, method)` | `fu, data_objs, _ = bd.prepare_lca_inputs({act: 1}, method=method)`<br>`lca = bc.LCA(demand=fu, data_objs=data_objs)` | 显式解耦需求与矩阵数据对象，支持云端分布式计算与无库计算。 |
| **MultiLCA 批量计算** | 必须在 `calculation_setups` 中注册字典模板，再实例化 `MultiLCA('setup_name')` | `data_objs = bd.get_multilca_data_objs(functional_units, method_config)`<br>`mlca = bc.MultiLCA(demands=..., method_config=..., data_objs=...)` | 废弃全局状态字典，原生支持动态多产品、多情景、多指标并行矢量化求解。 |
| **导入器状态核查** | `imp.all_linked()`（方法调用） | `imp.all_linked`（属性访问，布尔值） | 统一面向对象属性接口。 |
| **未链接流提取** | `imp.unlinked`（返回列表） | `imp.unlinked`（返回生成器 Generator） | 大数据量下降低内存占用；需取数量时用 `len(list(imp.unlinked))`。 |
| **蒙特卡洛抽样模拟** | 需使用独立的 `MonteCarloLCA({act: 1}, method)` 类 | 在统一的 `bc.LCA(..., use_distributions=True)` 中通过迭代器 `next(lca)` 实现 | 统一求解器接口，矩阵抽样开销降低 80% 以上。 |

---

## 2. 本地 Conda 环境配置与加速部署指南

为确保学生端环境纯净稳定、依赖版本与官方教程 100% 契合，本教学包提供三种灵活的环境创建方案。

### 2.1 方案 A：基于配置文件 `env_bw25.yml` 一键克隆复现环境（官方推荐同款）

官方教程在 [Brightway Book GitHub 仓库](https://github.com/brightway-lca/brightway-book) 中提供了标准的依赖清单文件 `env_bw25.yml`。本项目已将其收录至 `data_collections/env_bw25.yml` 并补齐了全套数据分析与可视化库。

#### 📄 `env_bw25.yml` 核心依赖解析
- **Conda 频道**：`conda-forge` 与 `cmutel`（Brightway 创始人 Chris Mutel 的官方发布频道）；
- **核心组件版本锁定**：
  - `python=3.11`
  - `jupyterlab=4.2.5` + `ipykernel`
  - `bw2io=0.9.dev38`、`bw2calc=2.0.dev22`、`bw2data=4.0.dev56`
  - `bw2analyzer=0.11.7`、`stats_arrays=0.7`、`ecoinvent_interface=2.4.1`
  - `pandas`、`openpyxl`（Excel 导入与多 Sheet 导出支持）
  - `matplotlib`、`seaborn`（专业统计绘图支持）

#### 🚀 一键执行创建命令
在当前教学包目录下打开 Windows PowerShell 或 Anaconda Prompt：

```powershell
# 方式 1: 使用 Conda 一键读取配置文件创建（推荐启用 libmamba 求解器）
conda env create -f data_collections/env_bw25.yml

# 方式 2: 使用 Mamba 极速并发创建（若已安装 mamba）
mamba env create -f data_collections/env_bw25.yml
```

#### 🔌 激活环境与注册 Jupyter 内核
环境创建完成后，默认环境名称为 `env_bw25`。执行以下命令激活并注册内核：

```powershell
# 1. 激活环境
conda activate env_bw25

# 2. 将环境内核注册至 Jupyter 系统列表
python -m ipykernel install --user --name env_bw25 --display-name "Python (env_bw25)"
```
> 💡 **启动提示**：环境配置完成后，在当前教学包目录下打开终端执行 `jupyter lab` 或在 VS Code 中直接打开 `practice2.ipynb` 并选择 `Python (env_bw25)` 或 `Python (Brightway 2.5)` 内核即可开启实操。

---

### 2.2 方案 B：命令行直接创建独立环境 (`bw25`)（快捷纯净方案）

若不想依赖 YAML 文件，亦可直接在终端中单行命令拉取最新稳定版 Brightway 2.5：

```powershell
# 1. 创建专用虚拟环境并指定 Python 3.11 与 Brightway 2.5 频道
conda create -n bw25 -y -c conda-forge -c cmutel python=3.11 brightway25 ipykernel openpyxl pandas matplotlib seaborn

# 2. 激活环境
conda activate bw25

# 3. 安装贡献度分析扩展库
pip install bw2analyzer

# 4. 将环境注册到 Jupyter 内核列表
python -m ipykernel install --user --name bw25 --display-name "Python (Brightway 2.5)"
```

---

### 2.3 方案 C：中国大陆境内网络镜像加速配置（纯境内弱网方案）

若直连境外 `conda-forge` 或 `cmutel` 出现下载缓慢、丢包或超时，可切换至清华大学 TUNA 镜像源或使用 pip 国内源加速：

```powershell
# 1. 配置清华 Conda 镜像源
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/msys2/
conda config --set show_channel_urls yes

# 2. 优先使用 libmamba 求解器创建基础科学计算环境
conda create -n bw25 -y --solver libmamba python=3.11 openpyxl pandas matplotlib seaborn ipykernel
conda activate bw25

# 3. 通过国内 PyPI 镜像源极速拉取 Brightway 2.5 核心套件
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "brightway25" bw2analyzer

# 4. 注册 Jupyter 内核
python -m ipykernel install --user --name bw25 --display-name "Python (Brightway 2.5)"
```

---

## 3. Windows 系统专属疑难排查与稳定性补丁

### 3.1 Pypardiso 报错 `OSError: [WinError -1066598273] Windows Error 0xc06d007f`

- **现象描述**：
  在 Windows 平台下执行 `lca.lci()` 或 `next(mc_lca)` 时，程序崩溃并抛出：
  ```text
  OSError: [WinError -1066598273] Windows Error 0xc06d007f
  File ".../pypardiso/pardiso_wrapper.py", line 277, in _call_pardiso
  ```
- **根因诊断 (Root Cause)**：
  `pypardiso` 是基于 Intel MKL (Math Kernel Library) 的直接稀疏求解器。Windows 缺少配套的 Intel OpenMP/MKL 原生 C 运行时链接库时，调用 `_mkl_pardiso` 会触发底层 Windows 动态链接库加载异常（Exception 0xc06d007f）。
- **解决方案 (教学代码内置)**：
  在代码第 1 步注入**求解器稳定性补丁**，将线性求解器无缝重定向到极为稳定的 `scipy.sparse.linalg.spsolve`，并安全旁路 `_delete_solver_state`：
  ```python
  import scipy.sparse.linalg
  import bw2calc.lca_base
  import bw2calc.multi_lca

  bw2calc.lca_base.spsolve = scipy.sparse.linalg.spsolve
  bw2calc.multi_lca.spsolve = scipy.sparse.linalg.spsolve
  bw2calc.lca_base.pypardiso_solver = None
  bw2calc.lca_base.LCABase._delete_solver_state = lambda self: None
  ```
  该补丁无需管理员权限，对教学案例与绝大多数工业模型保证 100% 求解正确性。

### 3.2 Matplotlib / Seaborn 统计图表中文字体乱码与方框 (Tofu Box) 解决方案

- **现象描述**：
  在执行第 7 步 MultiLCA 柱状图、第 8 步敏感性分析或第 9 步蒙特卡洛概率密度图时，坐标轴标题、图例（Legend）或数据标签中的中文字符显示为白色方框（豆腐块乱码，如 `[?]`、`[Z]`）。
- **根因诊断 (Root Cause)**：
  1. Matplotlib 默认无衬线字体集（Sans-serif）回退到系统英文库（如 `DejaVu Sans` / `Arial`），不包含汉字字形编码。
  2. 在调用 `sns.set_theme(style="whitegrid")` 时，Seaborn 底层会自动重置 Matplotlib 全局参数，如果中文字体设置在 `sns.set_theme` 之前执行，将被直接覆盖失效；同时负号编码 `axes.unicode_minus` 也被重置为 `True`，导致负号同样变为方框。
- **解决方案 (教学代码内置)**：
  1. 优先调用 `sns.set_theme(...)`，并通过其 `rc` 参数显式固化中文字体列表（优先 `'Microsoft YaHei'`、`'SimHei'`、`'PingFang SC'`、`'Source Han Sans CN'`）：
     ```python
     sns.set_theme(
         style="whitegrid",
         palette="muted",
         rc={
             'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Source Han Sans CN', 'DejaVu Sans'],
             'axes.unicode_minus': False,
             'figure.dpi': 120
         }
     )
     plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Source Han Sans CN', 'DejaVu Sans']
     plt.rcParams['axes.unicode_minus'] = False
     ```
  2. 在每个独立绘图代码块（如 MultiLCA、敏感性分析）前预先强化字体声明，确保无论单元格是否乱序执行，中文均能 100% 优雅抗锯齿渲染。

---

## 4. 零商业授权自洽背景数据库构建方案 (Solution 1)

官方教程要求引用商业数据库 `ecoinvent-3.9.1-cutoff` 和 `ecoinvent-3.9.1-biosphere`。针对无商业授权的教学场景，我们在代码第 3 步通过自主代码直接在当前项目中注册同名轻量级背景库：

1. **基本流库 (`ecoinvent-3.9.1-biosphere`)**：
   - 注册 5 种最核心的温室气体与资源流：`Carbon dioxide, fossil`、`Methane, fossil`、`Dinitrogen monoxide`、`Water, well, in ground`、`Sulfur dioxide`。
2. **背景过程库 (`ecoinvent-3.9.1-cutoff`)**：
   - 注册 5 个与包装材料供应链高度契合的代表性工序：
     - `polyethylene terephthalate production, granulate, bottle grade` (原生瓶级 PET 树脂切片生产)
     - `blow moulding` (吹塑注塑成型工序)
     - `tap water production` (自来水提取净化)
     - `market for transport, freight, lorry 16-32 metric ton, EURO5` (重型卡车公路物流)
     - `market for electricity, medium voltage` (中压电网供电)
3. **环境影响评价方法**：
   - 包含欧盟推荐的 **EF v3.0** 与联合国 **IPCC 2021** 气候变化 GWP100、水资源利用消耗指标与大气酸化潜能指标。

---

## 5. 前景数据排错与匹配策略实战指南

在第 5 步排错演练中，故意引入了真实工程中最常见的**单位拼写偏差**：
- 前台制造活动 `water bottle production` 产出单位为 `unit`；
- 消费活动 `Drinking water from a bottle` 的清单中将该输入流单位填写为 `piece`。

### 排错诊断与修复步骤
1. 执行 `imp.statistics()` 发现存在 `1 unique unlinked edges`；
2. 提取 `unlinked_list = list(imp.unlinked)` 查看具体字段，定位到是单位字段引发；
3. 在 Python 内存中迭代修正：
   ```python
   for act_data in imp.data:
       for exc in act_data.get('exchanges', []):
           if exc.get('name') == 'water bottle production' and exc.get('unit') == 'piece':
               exc['unit'] = 'unit'
   ```
4. 重新调用 `imp.match_database(fields=('name', 'unit', 'location'))`，确认 `imp.all_linked == True` 后入库。

---

## 6. 结果深度解读与 LCA 教学要点

随堂运行后，系统将自动导出 Excel 报告 `lcia_results_practice2.xlsx`。主要环境结论如下：

1. **生命周期碳足迹基准**：
   - 1 升瓶装饮用水全程碳足迹约为 **0.1316 kg CO2-eq / liter**；
   - 其中塑料瓶包装本身（水瓶生产）贡献了 **0.1231 kg CO2-eq**，占全生命周期碳排放的 **93.5%**！
   - 自来水加工净化仅占 **0.2%**，物流运输占 **6.3%**。
2. **包装工程热点工序 (Hotspots)**：
   - PET 树脂切片生产是最大的碳排放热点（占比 **55.9%**）；
   - 吹塑注塑加工占 **20.7%**；
   - 生产电力消耗占 **13.2%**。
3. **脱碳路径对比 (Decarbonization Pathways)**：
   - **瓶身轻量化 20%**：可直接实现系统降碳 **15.3%**；
   - **添加 50% 食品级再生塑料 (rPET)**：可降碳 **18.2%**；
   - **轻量化 20% + 70% rPET 复合方案**：综合减碳幅度可达 **39.5%**！
4. **蒙特卡洛不确定性模拟**：
   - 500 次随机抽样模拟表明，碳足迹呈现对数正态特征分布，95% 置信区间处于 `[0.117, 0.150] kg CO2-eq` 范围，充分揭示了供应链原料波动的风险区间。

---

## 7. 常见学生报错速查表 (FAQ)

| 报错信息 | 触发原因 | 一键解决办法 |
| :--- | :--- | :--- |
| `TypeError: 'bool' object is not callable` | 将 `imp.all_linked` 误写为 `imp.all_linked()` | 去掉括号，直接写 `if imp.all_linked:` |
| `TypeError: object of type 'generator' has no len()` | 在 BW2.5 中对 `imp.unlinked` 直接调用 `len()` | 显式转换为列表：`len(list(imp.unlinked))` |
| `bw2data.errors.UnknownObject` | 调用 `db.get("活动名")` 时传入位置参数 | 必须指定关键字参数：`db.get(name="活动名")` |
| `OSError: Windows Error 0xc06d007f` | Windows 下缺少 Intel MKL 运行时 | 确认已完整执行 Notebook 第 1 步中的求解器补丁代码 |
| `ModuleNotFoundError: No module named 'bw2analyzer'` | 虚拟环境中未安装分析扩展库 | 在终端激活环境后执行 `pip install bw2analyzer` |
| `Glyph missing` / 图表中文轴名显示为白框或乱码 (`[?]` 或 `[Z]`) | Seaborn `sns.set_theme()` 重置了全局 `rcParams`，导致中文字体被清空 | 在 `sns.set_theme(rc={'font.sans-serif': ['Microsoft YaHei', 'SimHei'], 'axes.unicode_minus': False})` 中配置，或在绘图前重新声明 `plt.rcParams['font.sans-serif']` |
