"""
案例一：废弃 PET 瓶机械物理再生 —— 工艺物质流程图
支持两种风格：
  选项 A（默认·新手友好）: schemdraw  — 工业方框工艺流程图（BFD）
  选项 B（进阶·交互式）: plotly    — MFA 桑基图

依赖安装：
  pip install schemdraw plotly kaleido pandas numpy
"""

from pathlib import Path
import pandas as pd

HERE     = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "case_files" / "data_cohort"

mfa_df = pd.read_csv(DATA_DIR / "mfa_mass_balance.csv")
mfa_df = mfa_df[~mfa_df["Stage"].str.startswith("Balance")]   # 去除平衡校验行

# ══════════════════════════════════════════════════════════════════
# 方式 1：schemdraw 方框工艺流程图（选项 A · 零系统依赖）
# ══════════════════════════════════════════════════════════════════
def plot_bfd_with_schemdraw(out_dir: Path, dpi: int = 300):
    """使用 schemdraw 绘制工业方框工艺流程图 (Block Flow Diagram)"""
    try:
        import schemdraw
        from schemdraw.flow import Process, Start, End, Arrow
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
    except ImportError:
        print("⚠️ schemdraw 未安装，请先: pip install schemdraw matplotlib")
        return

    d = schemdraw.Drawing(fontsize=10)

    # ── 1. 原料入口 ──
    d += Start().label("原料\n废弃打包 PET 瓶砖\n(1000 kg)\n含瓶盖/标签/泥沙",
                       halign="center", fontsize=10,
                       color="#FF8C00").fill("#FFE4B5").linewidth(1.2)

    # ── 2. 主流程 5 个工段 ──
    process_steps = [
        ("① 拆包、筛选\n与干式脱标机",           "#D6EAF8"),
        ("② 湿式粉碎\n与热碱洗单元\n(85℃, 1.5% NaOH)", "#D6EAF8"),
        ("③ 密度浮选分离槽\n(水介质 ρ=1.0 g/cm³)",   "#D6EAF8"),
        ("④ 光学色选、\n脱水与干燥系统",           "#D6EAF8"),
        ("⑤ 真空挤出造粒\n与固相增粘 SSP\n(270℃熔融/210℃增粘)", "#D6EAF8"),
    ]

    for label, fill in process_steps:
        d += Arrow().right(color="#34495E", lw=1.5)
        d += Process().label(label, fontsize=10, halign="center",
                             color="#2E86C1").fill(fill).linewidth(1.2)

    # ── 3. 主产品出口 ──
    d += Arrow().right(color="#145A32", lw=1.8)
    d += End().label("主产品\n瓶级 rPET 颗粒\n(800 kg)\n总收率 Y = 80.0%",
                    halign="center", fontsize=11,
                    color="#145A32").fill("#ABEBC6").linewidth(1.5)

    # ── 4. 分支废弃物 & 副产物（用子图叠加标注）──
    fig = d.draw(show=False)

    # 在图上用 ax.text 标注分支物料流（比 schemdraw 原生分支更简洁）
    ax = fig.gca()
    ax.set_title("废弃 PET 瓶机械物理再生 — 方框工艺流程图 (BFD)\n"
                 "基准情景：1000 kg 废瓶砖 → 800 kg 瓶级 rPET 颗粒",
                 fontsize=14, fontweight="bold", pad=22)

    # 分支标注坐标（按 schemdraw 布局自动估计）
    ax.text(0.18, 0.15, "▼ 脱标工段分支\n废标签(PP/PVC) 20 kg\n+ 泥沙灰尘 25 kg\n→ 焚烧 / 填埋",
            ha="center", fontsize=9, color="#C0392B",
            bbox=dict(boxstyle="round,pad=0.3", fc="#FADBD8", ec="#C0392B", lw=0.8))
    ax.text(0.35, 0.15, "▼ 热碱洗工段分支\n洗涤废液 (胶水+COD) 35 kg\n→ 厂内污水站",
            ha="center", fontsize=9, color="#C0392B",
            bbox=dict(boxstyle="round,pad=0.3", fc="#FADBD8", ec="#C0392B", lw=0.8))
    ax.text(0.52, 0.15, "▼ 密度分选工段分支\n副产物：HDPE 瓶盖碎料 75 kg\n(夹带损失 5 kg → 焚烧)\n→ 外售作塑料托盘/管道",
            ha="center", fontsize=9, color="#1E8449",
            bbox=dict(boxstyle="round,pad=0.3", fc="#D5F5E3", ec="#1E8449", lw=0.8))
    ax.text(0.69, 0.15, "▼ 光学色选工段分支\n黄变杂质 + 超细粉 40 kg\n→ 降级造粒 / 焚烧",
            ha="center", fontsize=9, color="#C0392B",
            bbox=dict(boxstyle="round,pad=0.3", fc="#FADBD8", ec="#C0392B", lw=0.8))

    ax.text(0.02, -0.08,
            "📊 数据来源: case_files/data_cohort/mfa_mass_balance.csv\n"
            "⚙️ 绘图库: schemdraw v0.15+ (pure Python / matplotlib backend)",
            transform=ax.transAxes, fontsize=8, color="gray")

    fig.tight_layout()

    out_png = out_dir / "process_flow_diagram_BFD.png"
    out_svg = out_dir / "process_flow_diagram_BFD.svg"
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(out_svg, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)
    print(f"✅ schemdraw BFD 已生成: {out_png}  ({dpi} dpi)")
    print(f"✅ schemdraw BFD 已生成: {out_svg}")

# ══════════════════════════════════════════════════════════════════
# 方式 2：plotly 物质流桑基图（选项 B · 交互式）
# ══════════════════════════════════════════════════════════════════
def plot_sankey_with_plotly(out_dir: Path):
    """使用 plotly 绘制 MFA 桑基图（质量通量严格成比例）"""
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("⚠️ plotly 未安装，请先: pip install plotly kaleido")
        return

    # 节点定义（idx → label）
    labels = [
        "原料：废 PET 瓶砖 (1000 kg)",      # 0
        "① 拆包脱标",                       # 1
        "② 热碱洗",                         # 2
        "③ 密度浮选",                       # 3
        "④ 光学色选",                       # 4
        "⑤ 挤出 SSP",                       # 5
        "废标签+泥沙 (45 kg)",              # 6
        "洗涤废液 (35 kg)",                 # 7
        "副产物 HDPE 瓶盖 (75 kg)",          # 8
        "黄变杂质+细粉 (40 kg)",             # 9
        "主产品：瓶级 rPET (800 kg)",        # 10
    ]
    node_colors = [
        "#FF8C00", "#5DADE2", "#5DADE2", "#5DADE2", "#5DADE2", "#5DADE2",
        "#C0392B", "#C0392B", "#27AE60", "#C0392B", "#145A32",
    ]

    # source → target → value (kg)
    sources = [0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 5]
    targets = [1, 2, 6, 3, 7, 4, 8, 10, 5, 9, 10]
    values  = [1000, 955, 45, 920, 35, 845, 75, 5, 805, 40, 800]

    link_colors = [
        "#F5B041", "#85C1E9", "#F1948A", "#85C1E9", "#F1948A",
        "#85C1E9", "#82E0AA", "#F1948A", "#85C1E9", "#F1948A", "#82E0AA"
    ]

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        valueformat=".0f", valuesuffix=" kg",
        node=dict(pad=18, thickness=22,
                  line=dict(color="white", width=1.2),
                  label=labels, color=node_colors,
                  hovertemplate="%{label}<br/>总通量: %{value}<extra></extra>"),
        link=dict(source=sources, target=targets, value=values, color=link_colors,
                  hovertemplate="%{source.label} → %{target.label}"
                                "<br/>%{value} kg<extra></extra>")
    )])

    fig.update_layout(
        title=dict(text="废弃 PET 瓶机械物理再生 — MFA 物质流分析桑基图<br>"
                        "基准情景：1000 kg 废瓶砖 → 800 kg 瓶级 rPET 颗粒",
                   font=dict(size=18), x=0.5),
        font=dict(size=12, family="Helvetica"),
        width=1200, height=680,
        margin=dict(l=20, r=20, t=90, b=40),
        annotations=[dict(text="📊 数据来源: mfa_mass_balance.csv  |  🟠原料  🔵主工序  🟢产品/副产  🔴废弃物",
                          showarrow=False, x=0.5, y=-0.08, xref="paper", yref="paper",
                          font=dict(size=10, color="gray"))]
    )

    out_html = out_dir / "process_flow_diagram_Sankey.html"
    fig.write_html(str(out_html), include_plotlyjs="cdn")
    print(f"✅ plotly Sankey HTML 已生成: {out_html}")

    # kaleido 导出静态图
    try:
        import kaleido
        fig.write_image(str(out_dir / "process_flow_diagram_Sankey.png"), scale=2)
        fig.write_image(str(out_dir / "process_flow_diagram_Sankey.svg"))
        print(f"✅ plotly Sankey PNG / SVG 已生成 (2x 高分辨率 ≥ 300 dpi)")
    except Exception as e:
        print(f"⚠️ kaleido 静态图导出失败: {e}")
        print("   请执行: pip install kaleido")

# ══════════════════════════════════════════════════════════════════
# 主程序
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("案例一：工艺物质流程图绘制")
    print("=" * 65)

    # 方式 A（必选）: schemdraw 方框流程图
    plot_bfd_with_schemdraw(HERE, dpi=300)

    print()

    # 方式 B（可选）: plotly 桑基图
    plot_sankey_with_plotly(HERE)

    # 输出目录文件列表
    print("\n📂 code_implementation/ 目录产出：")
    for f in sorted(HERE.iterdir()):
        if f.name.startswith("process_flow") or f.name.startswith("sensitivity"):
            size_kb = f.stat().st_size / 1024
            print(f"   📄 {f.name}  ({size_kb:.1f} KB)")