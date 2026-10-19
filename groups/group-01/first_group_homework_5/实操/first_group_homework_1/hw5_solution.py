# -*- coding: utf-8 -*-
"""
《环境规划与管理》课后作业 NO.5 —— 轨道 A · 选项 A1
欧盟新电池法 / 国家循环经济高标准冲击情景：动力电池金属锂动态 MFA（2021–2030）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
模型结构（四个过程 P1–P4，严格用离散差分方程逐年递推，不假设平衡态）

  P1 制造 : F_virgin(t) + F_loop(t) = F_prod(t)              # 无库存累积
  P2 在役 : S_use(t)  = S_use(t-1) + F_prod(t) - F_loss_use(t) - F_eol(t)
            F_loss_use(t) = S_use(t-1) * LOSS_RATE           # 当年初库存 * 1%
            F_eol(t)      = S_use(t-1) * EOL_RATE            # 当年初库存 * 12%
  P3 回收 : 收集量   = F_eol(t) * ETA_COL
            未收集量 = F_eol(t) * (1 - ETA_COL)  -> P4
            F_loop(t) = F_eol(t) * ETA_COL * ETA_REC          # 再生锂，闭环回流 P1 抵扣原生
            F_slag(t) = F_eol(t) * ETA_COL * (1 - ETA_REC)    # 湿法残渣 -> P4
  P4 处置 : S_disp(t) = S_disp(t-1) + F_loss_use(t)
                        + F_eol(t)*(1-ETA_COL) + F_slag(t)     # 固废累积

  R_sec(t) = F_loop(t) / F_prod(t)                                  # 再生锂自给率

情景设定
  基准情景 : ETA_COL = 0.90, ETA_REC = 0.85  -> 综合闭环 76.5%  （全程）
  政策情景 : ETA_COL = 0.90->0.98, ETA_REC = 0.85->0.93 在 t>=6 (2026) 阶跃
             -> 综合闭环 76.5% -> 91.14%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
rcParams["axes.unicode_minus"] = False

# ============================ 1. 全局参数 ============================
YEARS = list(range(2021, 2031))          # t = 1 … 10 对应 2021 … 2030
N = len(YEARS)

S_USE_0   = 25000.0   # t   2020 年底在役库存 S_use(0)
PROD_2021 = 10000.0   # t   2021 年新电池锂需求 F_prod(2021)
G_PROD    = 0.08      # -   制造需求年均复合增长率
LOSS_RATE = 0.01      # -   使用阶段年事故损毁率
EOL_RATE  = 0.12      # -   年退役率

ETA_COL_BASE, ETA_COL_POL = 0.90, 0.98    # 规范收集率
ETA_REC_BASE, ETA_REC_POL = 0.85, 0.93    # 湿法冶炼锂回收率
POLICY_T  = 6                             # 政策技改生效年份 t=6（2026 年）


# ============================ 2. 情景仿真 ============================
def simulate(policy: bool) -> dict:
    """逐年递推 2021–2030。policy=False 为基准情景，True 为政策技改情景。"""
    s_use    = np.zeros(N)   # 年末在役库存
    s_disp   = np.zeros(N)   # 年末终端处置累积
    f_prod   = np.zeros(N)   # 新电池锂需求
    f_loss   = np.zeros(N)   # 使用阶段事故损毁
    f_eol    = np.zeros(N)   # 退役量
    f_loop   = np.zeros(N)   # 再生锂闭环回流
    f_slag   = np.zeros(N)   # 湿法残渣
    f_virgin = np.zeros(N)   # 原生锂开采需求

    s_use_prev, s_disp_prev = S_USE_0, 0.0

    for i, year in enumerate(YEARS):
        t = i + 1

        # ---- P2 在役库：先算流出，再更新年末库存 ----
        f_prod[i] = PROD_2021 * (1 + G_PROD) ** (t - 1)
        f_loss[i] = s_use_prev * LOSS_RATE
        f_eol[i]  = s_use_prev * EOL_RATE
        s_use[i]  = s_use_prev + f_prod[i] - f_loss[i] - f_eol[i]

        # ---- P3 回收冶炼：政策情景在 t>=6 阶跃 ----
        if policy and t >= POLICY_T:
            eta_col, eta_rec = ETA_COL_POL, ETA_REC_POL
        else:
            eta_col, eta_rec = ETA_COL_BASE, ETA_REC_BASE
        f_loop[i] = f_eol[i] * eta_col * eta_rec
        f_slag[i] = f_eol[i] * eta_col * (1 - eta_rec)

        # ---- P1 制造：闭环抵扣后的原生缺口 ----
        f_virgin[i] = f_prod[i] - f_loop[i]

        # ---- P4 终端处置：事故损毁 + 未收集 + 残渣 ----
        s_disp[i] = s_disp_prev + f_loss[i] + f_eol[i] * (1 - eta_col) + f_slag[i]

        s_use_prev, s_disp_prev = s_use[i], s_disp[i]

    return dict(s_use=s_use, s_disp=s_disp, f_prod=f_prod, f_loss=f_loss,
                f_eol=f_eol, f_loop=f_loop, f_slag=f_slag,
                f_virgin=f_virgin, r_sec=f_loop / f_prod)


base = simulate(policy=False)
pol  = simulate(policy=True)


# ============================ 3. 绘图 ============================
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

# ---- 子图 1：原生锂开采需求量 ----
axes[0].plot(YEARS, base["f_virgin"] / 1000, "o-",  color="#1f77b4",
             lw=2, ms=6, label="基准情景")
axes[0].plot(YEARS, pol["f_virgin"] / 1000,  "s--", color="#d62728",
             lw=2, ms=6, label="政策技改情景")
axes[0].set_title("子图 1  原生锂开采需求量 F_virgin(t) 对比", fontsize=12)
axes[0].set_xlabel("年份")
axes[0].set_ylabel("原生锂开采需求量 F_virgin (kt)")
axes[0].grid(alpha=0.3)
axes[0].legend()

# ---- 子图 2：再生锂自给率 ----
axes[1].plot(YEARS, base["r_sec"] * 100, "o-",  color="#1f77b4",
             lw=2, ms=6, label="基准情景")
axes[1].plot(YEARS, pol["r_sec"] * 100,  "s--", color="#d62728",
             lw=2, ms=6, label="政策技改情景")
axes[1].axhline(35, color="red", ls=":", lw=2, label="35% 法规红线")
axes[1].set_title("子图 2  再生锂自给率 R_sec(t) 对比", fontsize=12)
axes[1].set_xlabel("年份")
axes[1].set_ylabel("再生锂自给率 R_sec (%)")
axes[1].grid(alpha=0.3)
axes[1].legend()

fig.tight_layout()

# 兼容 Jupyter / Spyder / PyCharm 交互区：这些环境不定义 __file__，回退到当前工作目录
try:
    _here = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _here = os.getcwd()
out_png = os.path.join(_here, "hw5_curves.png")
fig.savefig(out_png, dpi=200)
print(f"[图已保存] {out_png}")
plt.show()


# ============================ 4. 逐年账本打印 ============================
print("\n================ 逐年演化账本（单位：t） ================")
print(f"{'年份':<6}{'F_prod':>9}{'F_eol':>9}"
      f" | {'基准F_loop':>11}{'基准F_virgin':>13}{'基准R_sec':>10}"
      f" | {'政策F_loop':>11}{'政策F_virgin':>13}{'政策R_sec':>10}")
print("-" * 100)
for i, y in enumerate(YEARS):
    print(f"{y:<6}{pol['f_prod'][i]:>9.0f}{pol['f_eol'][i]:>9.0f}"
          f" | {base['f_loop'][i]:>11.0f}{base['f_virgin'][i]:>13.0f}"
          f"{base['r_sec'][i]*100:>9.2f}%"
          f" | {pol['f_loop'][i]:>11.0f}{pol['f_virgin'][i]:>13.0f}"
          f"{pol['r_sec'][i]*100:>9.2f}%")
print("（F_prod / F_eol 两情景完全相同：制造需求与在役库退役逻辑不受回收政策影响）")


# ============================ 5. 回答问题 ============================
RED_LINE = 0.35


def first_cross_year(r_sec):
    """返回首个 R_sec >= 红线的年份；若 2021–2030 全程未跨线则返回 None。"""
    return next((y for y, r in zip(YEARS, r_sec) if r >= RED_LINE), None)


cross_pol  = first_cross_year(pol["r_sec"])
cross_base = first_cross_year(base["r_sec"])

# 2026–2030 累计原生锂节约 = Σ(基准 F_virgin - 政策 F_virgin) = Σ(政策 F_loop - 基准 F_loop)
# 注意：系统所有流量的单位均为吨（t），故变量名一律以 _t 结尾，避免单位语义漂移
mask         = np.array([y >= 2026 for y in YEARS])
saved_t      = float(np.sum(base["f_virgin"][mask] - pol["f_virgin"][mask]))   # t
saved_loop_t = float(np.sum(pol["f_loop"][mask] - base["f_loop"][mask]))       # t
assert abs(saved_t - saved_loop_t) < 1e-6, "闭环假设下两条算法应严格相等"

print("\n================ 问题回答 ================")
if cross_pol is None:
    print("Q1. 政策技改情景在 2021–2030 年内未跨过 35% 自给率红线。")
else:
    print(f"Q1. 政策技改情景下首次跨过 35% 自给率红线：{cross_pol} 年"
          f"（R_sec = {pol['r_sec'][cross_pol - 2021] * 100:.1f}%）")
    if cross_base is None:
        print("    · 对照：基准情景在 2021–2030 年内始终未跨线。")
    else:
        print(f"    · 对照：基准情景也在 {cross_base} 年跨线"
              f"（{base['r_sec'][cross_base - 2021] * 100:.1f}%），"
              f"政策情景的优势体现为更高的安全裕度与更低的原生需求。")
print(f"Q2. 2026–2030 年累计为园区节约原生矿石锂开采量："
      f"{saved_t:,.0f} t（≈ {saved_t / 1000:.2f} kt）")
