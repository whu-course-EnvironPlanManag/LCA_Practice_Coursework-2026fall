# =============================================================================
# 案例一：PET 再生工艺流程图 —— Block Flow Diagram (BFD)
# =============================================================================
# 使用 graphviz (DOT) 绘制
# 输出: process_flow_diagram.png (300 dpi+)
# =============================================================================

from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(exist_ok=True)

try:
    from graphviz import Digraph
except ImportError:
    print("❌ 缺少 graphviz 库。请执行: pip install graphviz")
    print("   同时需要安装 Graphviz 系统二进制: https://graphviz.org/download/")
    print("   Windows 下载后需把 bin 目录加入 PATH")
    import sys; sys.exit(1)

# -----------------------------------------------------------------------------
# 1. 创建有向图
# -----------------------------------------------------------------------------
g = Digraph("PET_Recycling_BFD", format="png")
g.attr(rankdir="LR", size="16,9", dpi="300", bgcolor="white",
       fontname="Microsoft YaHei", fontsize="12",
       nodesep="0.55", ranksep="0.75")

# 全局节点样式
g.attr("node", shape="box", style="rounded,filled", fontname="Microsoft YaHei",
       fontsize="11", color="#333333", penwidth="1.2")
g.attr("edge", fontname="Microsoft YaHei", fontsize="10", color="#555555")

# -----------------------------------------------------------------------------
# 2. 节点定义
# -----------------------------------------------------------------------------
# === 输入 ===
g.node("raw", label="🔴 原料\n废 PET 瓶砖\n1000 kg", fillcolor="#F8CECC", shape="box")

# === 主工艺链 ===
with g.subgraph(name="cluster_process") as c:
    c.attr(label="PET 机械物理再生工艺主流程", style="rounded,filled",
           fillcolor="#F5F5F5", color="#CCCCCC", fontsize="13", fontname="Microsoft YaHei")

    c.node("p1", label="① 拆包、筛选\n与干式脱标机", fillcolor="#DAE8FC")
    c.node("p2", label="② 湿式粉碎与\n热碱洗单元\n(85℃, 1.5% NaOH)", fillcolor="#DAE8FC")
    c.node("p3", label="③ 密度浮选\n分离槽\n(水介质 ρ=1.0 g/cm³)", fillcolor="#DAE8FC")
    c.node("p4", label="④ 光学色选、\n脱水与干燥系统", fillcolor="#DAE8FC")
    c.node("p5", label="⑤ 真空挤出造粒\n与 SSP 固相增粘\n(270℃ 熔融, 210℃ 增粘)", fillcolor="#DAE8FC")

# === 主产品 ===
g.node("product", label="🟢 主产品\n瓶级 rPET 颗粒\n800 kg (收率 80%)",
       fillcolor="#D5E8D4", shape="box", fontsize="12", fontname="Microsoft YaHei",
       fontcolor="#2d6a4f", penwidth="2")

# === 副产物 ===
g.node("hdpe", label="🟡 副产物\nHDPE 瓶盖碎料\n75 kg", fillcolor="#FFF2CC", shape="box")

# === 废弃物 ===
g.node("waste_label", label="🚮 废标签膜\n(PP/PVC)\n20 kg → 焚烧", fillcolor="#F8F8F8", shape="note")
g.node("waste_dirt",  label="🏷️ 泥沙/干灰渣\n25 kg → 填埋/建材", fillcolor="#F8F8F8", shape="note")
g.node("waste_cod",  label="💧 洗涤废液 COD\n35 kg → 厂内污水站", fillcolor="#F8F8F8", shape="note")
g.node("waste_hdpe", label="⚠️ HDPE 夹带损失\n5 kg → 沉渣焚烧", fillcolor="#F8F8F8", shape="note")
g.node("waste_fines",label="🌬️ 黄变细粉/超细粉\n40 kg → 降级/焚烧", fillcolor="#F8F8F8", shape="note")

# -----------------------------------------------------------------------------
# 3. 流向连线
# -----------------------------------------------------------------------------
# 主工艺链
g.edge("raw",   "p1", label="1000 kg", color="#333333", penwidth="1.5")
g.edge("p1",    "p2", label="955 kg",  color="#333333", penwidth="1.5")
g.edge("p2",    "p3", label="920 kg",  color="#333333", penwidth="1.5")
g.edge("p3",    "p4", label="840 kg",  color="#333333", penwidth="1.5")
g.edge("p4",    "p5", label="800 kg",  color="#333333", penwidth="1.5")
g.edge("p5",    "product", label="800 kg rPET", color="#2d6a4f", penwidth="2.5", arrowsize="1.5")

# HDPE 分支 (从浮选环节上浮)
g.edge("p3",    "hdpe", label="75 kg HDPE 回收", color="#c9a227", penwidth="2", style="solid",
       arrowsize="1.3")

# 废弃物分支
g.edge("p1",    "waste_label", label="20 kg 标签",   style="dashed", color="#999999")
g.edge("p1",    "waste_dirt",  label="25 kg 泥沙",   style="dashed", color="#999999")
g.edge("p2",    "waste_cod",   label="35 kg COD",    style="dashed", color="#999999")
g.edge("p3",    "waste_hdpe",  label="5 kg HDPE 夹带", style="dashed", color="#999999")
g.edge("p4",    "waste_fines", label="40 kg 细粉",   style="dashed", color="#999999")

# -----------------------------------------------------------------------------
# 4. 渲染输出
# -----------------------------------------------------------------------------
out_png  = OUT_DIR / "process_flow_diagram.png"
out_pdf  = OUT_DIR / "process_flow_diagram.pdf"
out_svg  = OUT_DIR / "process_flow_diagram.svg"

try:
    g.render(filename=str(out_png.with_suffix("")), cleanup=True)
    print(f"✅ PNG (300 dpi) 已保存: {out_png}")
except Exception as e:
    print(f"⚠️ PNG 渲染失败: {e}")
    print("   请确认已安装 Graphviz: https://graphviz.org/download/")
    print("   Windows: 下载安装后，把 C:\\Program Files\\Graphviz\\bin 加入 PATH")
    import sys; sys.exit(1)

# SVG 矢量版（可选）
try:
    g.format = "svg"
    g.render(filename=str(out_svg.with_suffix("")), cleanup=True)
    print(f"✅ SVG (矢量) 已保存:   {out_svg}")
except Exception as e:
    print(f"⚠️ SVG 跳过: {e}")

# PDF 版
try:
    g.format = "pdf"
    g.render(filename=str(out_pdf.with_suffix("")), cleanup=True)
    print(f"✅ PDF 已保存:          {out_pdf}")
except Exception as e:
    print(f"⚠️ PDF 跳过: {e}")

print("\n🎉 工艺流程图完成！")
