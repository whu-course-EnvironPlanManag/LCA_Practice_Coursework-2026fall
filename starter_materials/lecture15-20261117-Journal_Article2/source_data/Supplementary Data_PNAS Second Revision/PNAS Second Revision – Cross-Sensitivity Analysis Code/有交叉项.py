import pandas as pd
import numpy as np
import itertools
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.preprocessing import StandardScaler

input_path = r"D:\Desktop\数据1.xlsx"
output_path = r"D:\Desktop\论文\P返修论文\交叉敏感性分析-贸易\交叉敏感性分析_全部组合.xlsx"

df = pd.read_excel(input_path, skiprows=[1])

variables = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'M']
target = '总量'


def cross_sensitivity_analysis(data, var_pair, target_col):
    var1, var2 = var_pair

    data = data.copy()
    X1_centered = data[var1] - data[var1].mean()
    X2_centered = data[var2] - data[var2].mean()
    interaction_term = f"{var1}×{var2}"
    data[interaction_term] = X1_centered * X2_centered

    X = data[[var1, var2, interaction_term]]
    y = data[target_col]
    X_const = sm.add_constant(X)

    scaler_X = StandardScaler()
    scaler_y = StandardScaler()

    X_std = scaler_X.fit_transform(X)
    y_std = scaler_y.fit_transform(y.values.reshape(-1, 1)).flatten()

    X_std_const = sm.add_constant(X_std, has_constant='add')

    X_train, X_test, y_train, y_test = train_test_split(
        X_const, y, test_size=0.3, random_state=42
    )
    X_std_train, X_std_test, y_std_train, y_std_test = train_test_split(
        X_std_const, y_std, test_size=0.3, random_state=42
    )

    model_original = sm.OLS(y_train, X_train).fit()

    model_std = sm.OLS(y_std_train, X_std_train).fit()

    y_pred_train = model_original.predict(X_train)
    y_pred_test = model_original.predict(X_test)
    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))

    coef_var1 = model_original.params[var1]
    coef_var2 = model_original.params[var2]
    coef_interaction = model_original.params[interaction_term]
    p_interaction = model_original.pvalues[interaction_term]

    cross_sensitivity = model_std.params[3]

    if p_interaction < 0.05:
        if cross_sensitivity > 0:
            effect_type = "协同增强"
        else:
            effect_type = "拮抗削弱"
    else:
        effect_type = "无显著交互"

    return {
        'variables': var_pair,
        'var1': var1,
        'var2': var2,
        'r2_train': r2_train,
        'r2_test': r2_test,
        'rmse_train': rmse_train,
        'rmse_test': rmse_test,
        'coef_var1': coef_var1,
        'coef_var2': coef_var2,
        'p_var1': model_original.pvalues[var1],
        'p_var2': model_original.pvalues[var2],

        'coef_interaction': coef_interaction,
        'p_interaction': p_interaction,
        'cross_sensitivity': cross_sensitivity,
        'effect_type': effect_type,

        'coef_const': model_original.params['const'],
        'p_const': model_original.pvalues['const'],

        'total_effect_strength': abs(coef_var1) + abs(coef_var2) + abs(cross_sensitivity)
    }


all_combinations = list(itertools.combinations(variables, 2))
total_combinations = len(all_combinations)

print(f"开始交叉敏感性分析（共 {total_combinations} 种组合）...")
print("=" * 60)

all_results = []
for i, var_pair in enumerate(all_combinations, 1):
    print(f"\n[{i}/{total_combinations}] 分析组合: {var_pair[0]} + {var_pair[1]}")
    result = cross_sensitivity_analysis(df, var_pair, target)
    all_results.append(result)

best_by_r2 = max(all_results, key=lambda x: x['r2_test'])
best_by_cross_sens = max(all_results, key=lambda x: abs(x['cross_sensitivity']))

effect_type_count = {
    '协同增强': sum(1 for res in all_results if res['effect_type'] == '协同增强'),
    '拮抗削弱': sum(1 for res in all_results if res['effect_type'] == '拮抗削弱'),
    '无显著交互': sum(1 for res in all_results if res['effect_type'] == '无显著交互')
}

print("\n" + "=" * 60)
print("【关键发现】")
print(f"预测效果最佳组合: {best_by_r2['var1']} + {best_by_r2['var2']}")
print(f"  测试集R²: {best_by_r2['r2_test']:.4f}")
print(f"  交叉敏感性: {best_by_r2['cross_sensitivity']:.4f}")

print(f"\n交叉敏感性最强组合: {best_by_cross_sens['var1']} + {best_by_cross_sens['var2']}")
print(f"  交叉敏感性: {best_by_cross_sens['cross_sensitivity']:.4f}")
print(f"  交互效应类型: {best_by_cross_sens['effect_type']}")

print(f"\n【交互效应类型统计】")
for effect_type, count in effect_type_count.items():
    perc = count / total_combinations * 100
    print(f"  {effect_type}: {count}个组合 ({perc:.1f}%)")
print("\n" + "=" * 60)
print("正在保存结果到Excel...")

with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    main_data = []
    for res in all_results:
        main_data.append({
            '变量组合': f"{res['var1']} + {res['var2']}",
            '测试集R²': res['r2_test'],
            '训练集R²': res['r2_train'],
            '测试集RMSE': res['rmse_test'],
            '训练集RMSE': res['rmse_train'],
            f'{res["var1"]}_系数': res['coef_var1'],
            f'{res["var2"]}_系数': res['coef_var2'],
            '交互项系数': res['coef_interaction'],
            f'{res["var1"]}_p值': res['p_var1'],
            f'{res["var2"]}_p值': res['p_var2'],
            '交互项_p值': res['p_interaction'],
            '交叉敏感性系数': res['cross_sensitivity'],
            '交互效应类型': res['effect_type'],
            '效应绝对值之和': res['total_effect_strength'],
        })

    df_main = pd.DataFrame(main_data)
    df_main = df_main.sort_values(by='测试集R²', ascending=False)
    df_main.to_excel(writer, sheet_name='按R²排序', index=False)

    # Sheet 2: 按交叉敏感性排序
    cross_sens_data = []
    for res in sorted(all_results, key=lambda x: abs(x['cross_sensitivity']), reverse=True):
        cross_sens_data.append({
            '变量组合': f"{res['var1']} + {res['var2']}",
            '交叉敏感性系数': res['cross_sensitivity'],
            '绝对值': abs(res['cross_sensitivity']),
            '交互效应类型': res['effect_type'],
            f'{res["var1"]}_系数': res['coef_var1'],
            f'{res["var2"]}_系数': res['coef_var2'],
            '交互项系数': res['coef_interaction'],
            '测试集R²': res['r2_test'],
        })

    df_cross_sens = pd.DataFrame(cross_sens_data)
    df_cross_sens.to_excel(writer, sheet_name='按交叉敏感性排序', index=False)

    var_interaction_stats = []
    for var in variables:
        var_combos = [res for res in all_results if var in res['variables']]

        cross_sens_values = []
        for res in var_combos:
            cross_sens_values.append(abs(res['cross_sensitivity']))

        avg_cross_sensitivity = np.mean(cross_sens_values)
        max_cross_sensitivity = np.max(cross_sens_values)
        min_cross_sensitivity = np.min(cross_sens_values)
        synergy_count = sum(1 for res in var_combos if res['effect_type'] == '协同增强')
        antagonism_count = sum(1 for res in var_combos if res['effect_type'] == '拮抗削弱')

        var_interaction_stats.append({
            '变量': var,
            '平均交叉敏感性': avg_cross_sensitivity,
            '最大交叉敏感性': max_cross_sensitivity,
            '最小交叉敏感性': min_cross_sensitivity,
            '参与协同效应次数': synergy_count,
            '参与拮抗效应次数': antagonism_count,
            '总交互次数': len(var_combos),
        })

    df_var_stats = pd.DataFrame(var_interaction_stats)
    df_var_stats = df_var_stats.sort_values(by='平均交叉敏感性', ascending=False)
    df_var_stats.to_excel(writer, sheet_name='变量交互统计', index=False)

    best_detail = [
        {'项目': '最佳组合（按R²）', '值': f"{best_by_r2['var1']} + {best_by_r2['var2']}"},
        {'项目': '测试集R²', '值': best_by_r2['r2_test']},
        {'项目': '交叉敏感性系数', '值': best_by_r2['cross_sensitivity']},
        {'项目': '交互效应类型', '值': best_by_r2['effect_type']},
        {'项目': f'{best_by_r2["var1"]}_系数', '值': best_by_r2['coef_var1']},
        {'项目': f'{best_by_r2["var2"]}_系数', '值': best_by_r2['coef_var2']},
        {'项目': '交互项系数', '值': best_by_r2['coef_interaction']},
        {'项目': '交互项_p值', '值': best_by_r2['p_interaction']},
    ]

    df_best = pd.DataFrame(best_detail)
    df_best.to_excel(writer, sheet_name='最佳模型', index=False)

    effect_summary = []
    for effect_type in ['协同增强', '拮抗削弱', '无显著交互']:
        type_results = [res for res in all_results if res['effect_type'] == effect_type]
        if type_results:
            best_in_type = max(type_results, key=lambda x: abs(x['cross_sensitivity']))
            effect_summary.append({
                '效应类型': effect_type,
                '组合数量': len(type_results),
                '占比(%)': len(type_results) / total_combinations * 100,
                '最强交叉敏感性': best_in_type['cross_sensitivity'],
                '最强组合': f"{best_in_type['var1']} + {best_in_type['var2']}",
                '平均R²': np.mean([res['r2_test'] for res in type_results]),
            })

    df_effect_summary = pd.DataFrame(effect_summary)
    df_effect_summary.to_excel(writer, sheet_name='效应类型汇总', index=False)

print(f"\n✅ 交叉敏感性分析完成！")
print(f"结果文件: {output_path}")
print(f"共分析 {total_combinations} 种组合")
print(f"\n分布统计:")
for effect_type, count in effect_type_count.items():
    perc = count / total_combinations * 100
    print(f"  {effect_type}: {count}个 ({perc:.1f}%)")