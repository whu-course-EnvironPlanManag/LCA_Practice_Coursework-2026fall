# =============================================================================
# 案例一：PET 再生系统 MFA 桑基图 —— 基于 mfa_mass_balance.csv
# =============================================================================
# 使用 Plotly.graph_objects.Sankey 绘制
# 1000 kg 瓶砖 → 各工段去向  (800 kg rPET + 75 kg HDPE + 125 kg 废弃物)
# =============================================================================

import sys
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = CASE_DIR / "case_files" / "data_cohort"
OUT_DIR  = Path(__file__).resolve().parent
OUT_DIR.mkdir(exist_ok=True)

# -----------------------------------------------------------------------------
# 0. 读数据
# -----------------------------------------------------------------------------
df = pd.read_csv(DATA_DIR / "mfa_mass_balance.csv")
print("MFA 源数据:")
print(df.to_string())

# -----------------------------------------------------------------------------
# 1. 构建桑基图节点与流向
# -----------------------------------------------------------------------------
# 我们按照讲义中的 5 个工段层级组织：
#   Stage 0: 原料输入 (1000 kg 瓶砖)
#   Stage 1: 拆包+干式脱标 → 输出标签/泥沙 + 进入热洗
#   Stage 2: 热碱洗       → 输出废液 (35 kg COD) + 进入浮选
#   Stage 3: 密度浮选     → 上浮 HDPE + 下沉 PET 片料
#   Stage 4: 光学色选+干燥 → 输出黄变细粉 + 进入挤出
#   Stage 5: 真空挤出增粘 → 主产品 rPET

nodes = [
    # Stage 0
    {"label": "🟫 废瓶砖原料 (1000 kg)",           "color": "#8b5a2b"},
    # Stage 1: 拆包+干式脱标
    {"label": "⚙️ 拆包/筛选/干式脱标",              "color": "#4682b4"},
    {"label": "🚮 废标签 PP/PVC (20 kg)",          "color": "#999999"},
    {"label": "🏷️ 泥沙/干灰渣 (25 kg)",            "color": "#b08040"},
    # Stage 2: 热碱洗
    {"label": "🔥 湿式粉碎/热碱洗",                 "color": "#4682b4"},
    {"label": "💧 洗涤废液 COD (35 kg)",          "color": "#999999"},
    # Stage 3: 密度浮选
    {"label": "🧪 密度浮选分离槽",                  "color": "#4682b4"},
    {"label": "🟠 HDPE 瓶盖 (80 kg 入)",           "color": "#ffa500"},
    # Stage 4: 光学色选
    {"label": "🔬 光学色选/脱水/干燥",             "color": "#4682b4"},
    {"label": "🌬️ 黄变细粉/超细粉 (40 kg)",        "color": "#999999"},
    # Stage 5: 挤出增粘
    {"label": "🧬 真空挤出/SSP 增粘",              "color": "#4682b4"},
    # 最终产品 & 废弃物
    {"label": "✅ 主产品: rPET 颗粒 (800 kg)",     "color": "#2ecc71"},
    {"label": "💰 副产物: HDPE 回收料 (75 kg)",    "color": "#f1c40f"},
    {"label": "⚠️ HDPE 夹带损失 (5 kg)",           "color": "#999999"},
]

# 建立 label → index 映射
label_to_idx = {n["label"]: i for i, n in enumerate(nodes)}

# 流向 (source → target, value kg)
flows = [
    # Stage 0 → Stage 1
    (label_to_idx["🟫 废瓶砖原料 (1000 kg)"],
     label_to_idx["⚙️ 拆包/筛选/干式脱标"],    1000.0),

    # Stage 1 分流
    (label_to_idx["⚙️ 拆包/筛选/干式脱标"],
     label_to_idx["🚮 废标签 PP/PVC (20 kg)"],   20.0),
    (label_to_idx["⚙️ 拆包/筛选/干式脱标"],
     label_to_idx["🏷️ 泥沙/干灰渣 (25 kg)"],    25.0),
    (label_to_idx["⚙️ 拆包/筛选/干式脱标"],
     label_to_idx["🔥 湿式粉碎/热碱洗"],         955.0),     # 1000-20-25

    # Stage 2
    (label_to_idx["🔥 湿式粉碎/热碱洗"],
     label_to_idx["💧 洗涤废液 COD (35 kg)"],    35.0),
    (label_to_idx["🔥 湿式粉碎/热碱洗"],
     label_to_idx["🧪 密度浮选分离槽"],          920.0),     # 955-35

    # Stage 3 — HDPE 上浮 (80 kg → 75 回收 + 5 损失), PET 下沉 (840 kg)
    (label_to_idx["🧪 密度浮选分离槽"],
     label_to_idx["🟠 HDPE 瓶盖 (80 kg 入)"],    80.0),
    (label_to_idx["🧪 密度浮选分离槽"],
     label_to_idx["🔬 光学色选/脱水/干燥"],     840.0),     # 920-80
    # HDPE 分流
    (label_to_idx["🟠 HDPE 瓶盖 (80 kg 入)"],
     label_to_idx["💰 副产物: HDPE 回收料 (75 kg)"], 75.0),
    (label_to_idx["🟠 HDPE 瓶盖 (80 kg 入)"],
     label_to_idx["⚠️ HDPE 夹带损失 (5 kg)"],     5.0),

    # Stage 4
    (label_to_idx["🔬 光学色选/脱水/干燥"],
     label_to_idx["🌬️ 黄变细粉/超细粉 (40 kg)"], 40.0),
    (label_to_idx["🔬 光学色选/脱水/干燥"],
     label_to_idx["🧬 真空挤出/SSP 增粘"],       800.0),     # 840-40

    # Stage 5 → 主产品
    (label_to_idx["🧬 真空挤出/SSP 增粘"],
     label_to_idx["✅ 主产品: rPET 颗粒 (800 kg)"], 800.0),
]

# -----------------------------------------------------------------------------
# 2. 绘图
# -----------------------------------------------------------------------------
fig = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        pad=18,
        thickness=22,
        line=dict(color="white", width=0.5),
        label=[n["label"] for n in nodes],
        color=[n["color"] for n in nodes],
        hovertemplate="节点: %{label}<extra></extra>",
    ),
    link=dict(
        source=[f[0] for f in flows],
        target=[f[1] for f in flows],
        value= [f[2] for f in flows],
        color=  ["rgba(100,149,237,0.40)"] * len(flows),
        hovertemplate="%{source.label} → %{target.label}<br>流量: %{value:.1f} kg<extra></extra>",
    ),
))

fig.update_layout(
    title=dict(
        text="<b>废弃 PET 瓶机械物理再生系统 · MFA 桑基图</b>"
             "<br><sup>1000 kg 废瓶砖 → 800 kg 瓶级 rPET 颗粒 (收率 80%) · Group 03 · Lecture 9 Case 1</sup>",
        font=dict(size=18), x=0.5),
    font=dict(family="Microsoft YaHei, SimHei, sans-serif", size=13),
    height=720, width=1200,
    margin=dict(l=20, r=20, t=90, b=30),
    paper_bgcolor="white",
)

# 保存 PNG (需 kaleido) 和交互式 HTML
out_png = OUT_DIR / "mfa_sankey_diagram.png"
out_html = OUT_DIR / "mfa_sankey_diagram.html"

try:
    fig.write_image(str(out_png), scale=2)
    print(f"✅ PNG 已保存: {out_png}")
except Exception as e:
    print(f"⚠️ PNG 导出失败 (需 pip install kaleido): {e}")

fig.write_html(str(out_html), include_plotlyjs="cdn")
print(f"✅ HTML 已保存: {out_html}  (浏览器打开即可交互查看)")

print("\n🎉 MFA 桑基图完成！")
