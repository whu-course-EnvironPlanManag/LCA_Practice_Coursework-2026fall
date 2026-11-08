# -*- coding: utf-8 -*-
"""
《环境规划与管理》课后作业 NO.5 —— 轨道 A · 选项 A1
动态物质流分析（Dynamic MFA）：武汉城市圈动力电池金属锂循环
政策干预情景（2026 技改 / 2027 再生锂自给率 ≥ 35% 法规红线）vs 基准情景（Baseline）

模型结构（4 过程 · 7 流 · 1 闭环）：
    F_virgin ──► P1 制造 ──F_prod──► P2 在役(S_use) ──F_eol(12%)──► P3 回收 ──F_loop──┐
                                       │  F_loss_use(1%) │                          │
                                       ▼                  ▼                          │
                                       P4 处置 ◄── 未收集 10% + 冶炼损失 15% ◄─────────┘
闭环抵扣：F_virgin(t) = F_prod(t) − F_loop(t)

参数阶跃（政策情景）：
    t >= 2026：规范收集率 eta_c 0.90 → 0.98，湿法冶炼回收率 eta_r 0.85 → 0.93
               （闭环综合转化率 0.765 → 0.9114）
    法规红线：R_sec(t) >= 35% 自 2027 年起强制
其余参数与基准情景一致：F_prod 年增 8%、S_use(2020)=25,000 t、
年退役率 12%、使用损毁率 1%。
"""
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------- 全局配置 ----------------------------
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
YEARS = np.arange(2021, 2031)          # 2021–2030
N = len(YEARS)

# 基准参数
P0, G = 10_000.0, 0.08                 # 2021 制造需求 / 年增长率
S_USE_0 = 25_000.0                     # 2020 年末在役库存 (t)
R_EOL, R_LOSS = 0.12, 0.01             # 年退役率 / 使用损毁率
ETA_C_BASE, ETA_R_BASE = 0.90, 0.85    # 基准：规范收集率 / 湿法冶炼回收率
# 政策技改参数（A1）
ETA_C_POL, ETA_R_POL = 0.98, 0.93      # 2026 起技改后
T_TECH, T_RULE = 2026, 2027            # 技改年份 / 法规红线生效年份
R_SEC_MIN = 35.0                       # 再生锂自给率红线 (%)


# ---------------------------- 动态 MFA 引擎 ----------------------------
def run_mfa(eta_c_pol=None, eta_r_pol=None, t_tech=None):
    """动态 MFA 逐年递推。

    eta_c_pol/eta_r_pol/t_tech 均为 None 时即基准情景；
    给出技改参数时，自 t_tech 年起闭环综合转化率发生阶跃。
    返回包含全部流与库存指标的 DataFrame。
    """
    eta_c_pol = ETA_C_BASE if eta_c_pol is None else eta_c_pol
    eta_r_pol = ETA_R_BASE if eta_r_pol is None else eta_r_pol

    F_prod = P0 * (1 + G) ** np.arange(N)            # 制造需求（外生指数增长）
    F_eol = np.zeros(N)                              # 年退役量
    F_loss_use = np.zeros(N)                         # 使用损毁（直接进 P4，不可回收）
    F_uncol = np.zeros(N)                            # 未规范收集部分（进 P4）
    F_slag = np.zeros(N)                             # 冶炼渣损失（进 P4）
    F_loop = np.zeros(N)                             # 闭环回流（再生锂）
    F_virgin = np.zeros(N)                           # 原生锂开采
    S_use = np.zeros(N + 1)                          # 在役库存（含 2020 期初）
    S_use[0] = S_USE_0

    for i, yr in enumerate(YEARS):
        upgraded = (t_tech is not None) and (yr >= t_tech)
        eta_c = eta_c_pol if upgraded else ETA_C_BASE
        eta_r = eta_r_pol if upgraded else ETA_R_BASE

        F_eol[i] = R_EOL * S_use[i]                  # F_eol(t) = 0.12 × S_use(t-1)
        F_loss_use[i] = R_LOSS * S_use[i]            # F_loss(t) = 0.01 × S_use(t-1)
        F_loop[i] = F_eol[i] * eta_c * eta_r         # F_loop(t) = F_eol × ηc × ηr
        F_virgin[i] = F_prod[i] - F_loop[i]          # 闭环抵扣原生开采
        F_uncol[i] = F_eol[i] * (1 - eta_c)          # 未收集 → P4
        F_slag[i] = F_eol[i] * eta_c * (1 - eta_r)   # 冶炼渣 → P4
        S_use[i + 1] = S_use[i] + F_prod[i] - F_eol[i] - F_loss_use[i]

    df = pd.DataFrame({
        'Year': YEARS,
        'F_prod': F_prod, 'F_eol': F_eol, 'F_loop': F_loop, 'F_virgin': F_virgin,
        'F_loss_use': F_loss_use, 'F_uncol': F_uncol, 'F_slag': F_slag,
        'F_disp': F_loss_use + F_uncol + F_slag,     # 进入 P4 处置的总流量
        'S_use': S_use[1:],                          # 各年末在役库存
        'R_sec': F_loop / F_prod * 100.0,            # 再生锂自给率 (%)
    })
    return df


def anchor_check(df_base):
    """铅笔锚点核验（t=1，即 2021 年，课堂板书值）。"""
    r = df_base.iloc[0]
    expect = {'F_eol': 3000.0, 'F_loop': 2295.0, 'F_virgin': 7705.0,
              'S_use': 31750.0, 'R_sec': 22.95}
    got = {'F_eol': r.F_eol, 'F_loop': r.F_loop, 'F_virgin': r.F_virgin,
           'S_use': r.S_use, 'R_sec': r.R_sec}
    print('—' * 78)
    print('[锚点核验] 2021 年（t=1）模型输出 vs 课堂铅笔推导')
    ok = True
    for k, v in expect.items():
        match = abs(got[k] - v) < 1e-6 if k != 'R_sec' else abs(got[k] - v) < 1e-9
        ok &= match
        print(f'  {k:9s} 模型 {got[k]:>12,.2f} | 期望 {v:>12,.2f} | '
              f'{"一致 ✓" if match else "不一致 ✗"}')
    # 边界闭合核验：S_use 逐年递推应满足 S(t) = S(t-1) + F_prod - F_eol - F_loss
    d = df_base.S_use.iloc[0] - (S_USE_0 + df_base.F_prod.iloc[0]
                                 - df_base.F_eol.iloc[0] - df_base.F_loss_use.iloc[0])
    print(f'  {"边界闭合":9s} 残差 {d:>12.2e} | {"守恒 ✓" if abs(d) < 1e-9 else "不守恒 ✗"}')
    print(f'  结论：{"锚点全部一致，可进入情景对比" if ok else "请检查模型"}')
    return ok


# ---------------------------- 主流程 ----------------------------
if __name__ == '__main__':
    base = run_mfa()                                        # 基准情景
    pol = run_mfa(ETA_C_POL, ETA_R_POL, T_TECH)             # A1 政策技改情景

    # ---------- 控制台输出 1：逐年对比表 ----------
    print('=' * 92)
    print('轨道 A · 选项 A1：再生锂自给率 ≥35% 强制准入 + 2026 回收产线技改情景')
    print('系统拓扑：F_virgin→制造→在役→(退役12% / 损毁1%)→回收→(闭环回流抵扣原生开采)')
    print('=' * 92)
    comp = pd.DataFrame({
        'Year': base.Year,
        'F_prod': base.F_prod.round(0),
        'F_eol': base.F_eol.round(0),
        'F_loop_base': base.F_loop.round(0),
        'F_virgin_base': base.F_virgin.round(0),
        'Rsec_base%': base.R_sec.round(2),
        'F_loop_pol': pol.F_loop.round(0),
        'F_virgin_pol': pol.F_virgin.round(0),
        'Rsec_pol%': pol.R_sec.round(2),
        'S_use': base.S_use.round(0),
    })
    with pd.option_context('display.width', 200, 'display.max_columns', None):
        print(comp.to_string(index=False))
    base.to_csv(os.path.join(OUT_DIR, 'hw5_baseline.csv'), index=False)
    pol.to_csv(os.path.join(OUT_DIR, 'hw5_policy.csv'), index=False)

    # ---------- 控制台输出 2：政策问答 ----------
    over = pol.loc[pol.R_sec >= R_SEC_MIN]
    cross_year = int(over.Year.iloc[0]) if len(over) else None
    save = (base.F_virgin - pol.F_virgin)[base.Year.between(T_TECH, 2030)]
    print('=' * 92)
    print('【问题 1】政策情景下 R_sec 何时跨过 35% 法规红线？')
    if cross_year:
        v = pol.loc[pol.Year == cross_year, 'R_sec'].iloc[0]
        prev = pol.loc[pol.Year == cross_year - 1, 'R_sec'].iloc[0]
        print(f'  → {cross_year} 年首次达标：R_sec = {v:.2f}% ≥ 35%'
              f'（{cross_year - 1} 年为 {prev:.2f}%）；法规 2027 年生效，'
              f'{"如期合规" if cross_year <= T_RULE else "存在 1 年过渡期缺口"}。')
    else:
        print('  → 2021–2030 年内未跨过 35% 红线。')
    print('【问题 2】2026–2030 年累计节约原生矿石锂开采量')
    print(f'  → 合计 {save.sum():,.0f} t（≈ {save.sum() / 1000:.2f} kt）；'
          f'其中 2030 年当年节约 {save.iloc[-1]:,.0f} t。')
    print('=' * 92)

    anchor_check(base)

    # ---------------------------- 绘图 ----------------------------
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 10.6), dpi=150)
    c_base, c_pol, c_prod, c_red = 'tab:blue', 'tab:red', 'black', 'crimson'
    (ax1, ax2), (ax3, ax4) = axes

    # —— 子图 1：原生锂开采需求 F_virgin 对比 ——
    ax1.plot(base.Year, base.F_virgin, '--o', color=c_base, lw=2,
             label='Baseline virgin mining $F_{virgin}$')
    ax1.plot(pol.Year, pol.F_virgin, '-s', color=c_pol, lw=2,
             label='Policy (A1) virgin mining $F_{virgin}$')
    ax1.fill_between(base.Year, pol.F_virgin, base.F_virgin,
                     color=c_pol, alpha=0.12, label='Saved virgin ore Li')
    ax1.axvline(T_TECH, color='gray', ls=':', lw=1.4)
    ax1.axvline(T_RULE, color=c_red, ls=':', lw=1.4)
    ax1.annotate('2026 tech retrofit\n$\\eta_c0.90\\to0.98$, $\\eta_r0.85\\to0.93$',
                 xy=(T_TECH, base.F_virgin.iloc[5]), xytext=(2026.15, 8000),
                 fontsize=8.5, color='dimgray',
                 arrowprops=dict(arrowstyle='->', color='gray', lw=1))
    ax1.annotate(f'{T_RULE} rule: $R_{{sec}}\\geq35\\%$',
                 xy=(T_RULE, pol.F_virgin.iloc[6]), xytext=(2027.2, 9400),
                 fontsize=8.5, color=c_red,
                 arrowprops=dict(arrowstyle='->', color=c_red, lw=1))
    if cross_year:
        ax1.annotate(f'cumulative saving 2026–2030\n= {save.sum():,.0f} t',
                     xy=(0.03, 0.06), xycoords='axes fraction', fontsize=9,
                     bbox=dict(boxstyle='round,pad=0.35', fc='#fdecea', ec=c_pol, lw=0.8))
    ax1.set_title('Fig 1  Virgin Li Mining Demand: Baseline vs Policy (A1)', fontweight='bold')
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Virgin lithium flow (t/yr)')
    ax1.grid(True, ls=':', alpha=0.6)
    ax1.legend(loc='upper left', fontsize=8.5)

    # —— 子图 2：再生锂自给率 R_sec 对比（标 35% 红线）——
    ax2.plot(base.Year, base.R_sec, '--o', color=c_base, lw=2,
             label='Baseline $R_{sec}$')
    ax2.plot(pol.Year, pol.R_sec, '-s', color=c_pol, lw=2,
             label='Policy (A1) $R_{sec}$')
    ax2.axhline(R_SEC_MIN, color=c_red, ls='-', lw=1.8, label='35% regulatory red line')
    ax2.axvline(T_RULE, color=c_red, ls=':', lw=1.4)
    if cross_year:
        ax2.plot([cross_year], [pol.R_sec.iloc[cross_year - 2021]], 'r*', ms=14, zorder=5)
        ax2.annotate(f'{cross_year} first crosses 35%\n'
                     f'($R_{{sec}}$ = {pol.R_sec.iloc[cross_year - 2021]:.2f}%)',
                     xy=(cross_year, pol.R_sec.iloc[cross_year - 2021]),
                     xytext=(2022.2, 46.6), fontsize=9, color=c_red,
                     arrowprops=dict(arrowstyle='->', color=c_red, lw=1))
    ax2.text(2021.1, R_SEC_MIN + 1.2, f'{R_SEC_MIN:.0f}% red line (mandatory from 2027)',
             color=c_red, fontsize=8.5)
    ax2.set_title('Fig 2  Secondary Li Self-Supply Ratio $R_{sec}$', fontweight='bold')
    ax2.set_xlabel('Year')
    ax2.set_ylabel('$R_{sec}$ (%)')
    ax2.set_ylim(18, 50)
    ax2.grid(True, ls=':', alpha=0.6)
    ax2.legend(loc='lower right', fontsize=8.5)

    # —— 子图 3：在役库存 S_use 演化 ——
    ax3.plot(base.Year, base.S_use / 1000, '-o', color=c_base, lw=2,
             label='Baseline in-use stock $S_{use}$')
    ax3.plot(pol.Year, pol.S_use / 1000, '-s', color=c_pol, lw=2,
             label='Policy (A1) in-use stock $S_{use}$')
    ax3.axvline(T_TECH, color='gray', ls=':', lw=1.4)
    ax3.set_title('Fig 3  In-Use Stock Evolution $S_{use}$', fontweight='bold')
    ax3.set_xlabel('Year')
    ax3.set_ylabel('In-use stock (kt Li)')
    ax3.grid(True, ls=':', alpha=0.6)
    ax3.legend(loc='upper left', fontsize=8.5)
    ax3.annotate('higher EOL outflow after retrofit\nslightly reduces stock growth',
                 xy=(0.03, 0.88), xycoords='axes fraction', fontsize=8, color='dimgray')

    # —— 子图 4：闭环回流 F_loop 与总需求 F_prod ——
    ax4.plot(base.Year, base.F_prod, ':', color=c_prod, lw=2,
             label='Total demand $F_{prod}$ (+8%/yr)')
    ax4.plot(base.Year, base.F_loop, '--o', color=c_base, lw=2,
             label='Baseline closed-loop $F_{loop}$')
    ax4.plot(pol.Year, pol.F_loop, '-s', color=c_pol, lw=2,
             label='Policy (A1) closed-loop $F_{loop}$')
    ax4.axvline(T_TECH, color='gray', ls=':', lw=1.4)
    ax4.set_title('Fig 4  Demand vs Closed-Loop Secondary Supply', fontweight='bold')
    ax4.set_xlabel('Year')
    ax4.set_ylabel('Lithium flow (t/yr)')
    ax4.grid(True, ls=':', alpha=0.6)
    ax4.legend(loc='upper left', fontsize=8.5)

    fig.suptitle('Dynamic MFA of Li in EV Batteries, Wuhan Metropolitan Circle (2021–2030)\n'
                 'HW5 Track A · Option A1: 35% $R_{sec}$ mandate & 2026 recycling retrofit',
                 fontsize=12.5, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    png = os.path.join(OUT_DIR, 'hw5_curves.png')
    fig.savefig(png, dpi=150)
    print(f'图表已保存: {png}')
    print(f'明细数据已保存: hw5_baseline.csv / hw5_policy.csv')
