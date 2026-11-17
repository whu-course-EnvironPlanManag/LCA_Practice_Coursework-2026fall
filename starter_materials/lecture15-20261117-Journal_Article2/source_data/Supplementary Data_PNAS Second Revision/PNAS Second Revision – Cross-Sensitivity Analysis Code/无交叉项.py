import pandas as pd
import numpy as np
import itertools
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.preprocessing import StandardScaler

# 设置路径
input_path = r"D:\Desktop\数据.xlsx"
output_path = r"D:\Desktop\论文\P返修论文\交叉敏感性分析-生产\敏感性分析_全部组合.xlsx"

# 读取数据
df = pd.read_excel(input_path, skiprows=[1])

# 定义变量
variables = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J','K']
target = '总量'


def standardized_regression(data, var_pair, target_col):
    var1, var2 = var_pair
    X = data[[var1, var2]]
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

    sensitivity_var1 = model_std.params[1]
    sensitivity_var2 = model_std.params[2]

    more_sensitive = var1 if abs(sensitivity_var1) > abs(sensitivity_var2) else var2

    return {
        'variables': var_pair,
        'var1': var1,
        'var2': var2,
        'r2_train': r2_train,
        'r2_test': r2_test,
        'rmse_train': rmse_train,
        'rmse_test': rmse_test,
        'coef_var1': model_original.params[var1],
        'coef_var2': model_original.params[var2],
        'p_var1': model_original.pvalues[var1],
        'p_var2': model_original.pvalues[var2],
        'sensitivity_var1': sensitivity_var1,
        'sensitivity_var2': sensitivity_var2,
        'more_sensitive': more_sensitive,
        'coef_const': model_original.params['const'],
        'p_const': model_original.pvalues['const'],
        'total_sensitivity': abs(sensitivity_var1) + abs(sensitivity_var2)
    }

all_combinations = list(itertools.combinations(variables, 2))
total_combinations = len(all_combinations)

print(f"开始敏感性分析（共 {total_combinations} 种组合）...")
print("=" * 60)

all_results = []
for i, var_pair in enumerate(all_combinations, 1):
    print(f"\n[{i}/{total_combinations}] 分析组合: {var_pair[0]} + {var_pair[1]}")
    result = standardized_regression(df, var_pair, target)
    all_results.append(result)

best_result = max(all_results, key=lambda x: x['r2_test'])

sensitivity_count = {var: 0 for var in variables}
for res in all_results:
    sensitivity_count[res['more_sensitive']] += 1

sorted_by_sensitivity = sorted(all_results, key=lambda x: x['total_sensitivity'], reverse=True)

print("\n" + "=" * 60)
print("【最佳组合】")
print(f"变量: {best_result['var1']} + {best_result['var2']}")
print(f"测试集 R²: {best_result['r2_test']:.4f}")
print(f"\n【敏感性系数】")
print(f"{best_result['var1']}: {best_result['sensitivity_var1']:.4f}")
print(f"{best_result['var2']}: {best_result['sensitivity_var2']:.4f}")
print(f"更敏感的变量: {best_result['more_sensitive']}")
print("\n【变量敏感性统计】")
for var in variables:
    print(f"{var}: 在 {sensitivity_count[var]} 个组合中为最敏感变量")

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
            f'{res["var1"]}_原始系数': res['coef_var1'],
            f'{res["var2"]}_原始系数': res['coef_var2'],
            f'{res["var1"]}_p值': res['p_var1'],
            f'{res["var2"]}_p值': res['p_var2'],
            f'{res["var1"]}_敏感性系数': res['sensitivity_var1'],
            f'{res["var2"]}_敏感性系数': res['sensitivity_var2'],
            '更敏感变量': res['more_sensitive'],
            '敏感性绝对值之和': res['total_sensitivity'],
        })

    df_main = pd.DataFrame(main_data)
    df_main = df_main.sort_values(by='测试集R²', ascending=False)
    df_main.to_excel(writer, sheet_name='按R²排序', index=False)
    sensitivity_data = []
    for res in sorted_by_sensitivity:
        sensitivity_data.append({
            '变量组合': f"{res['var1']} + {res['var2']}",
            f'{res["var1"]}_敏感性': res['sensitivity_var1'],
            f'{res["var2"]}_敏感性': res['sensitivity_var2'],
            '更敏感变量': res['more_sensitive'],
            '敏感性绝对值之和': res['total_sensitivity'],
            '测试集R²': res['r2_test'],
        })

    df_sensitivity = pd.DataFrame(sensitivity_data)
    df_sensitivity.to_excel(writer, sheet_name='按敏感性排序', index=False)

    var_sensitivity_stats = []
    for var in variables:
        var_combos = [res for res in all_results if var in res['variables']]
        sens_values = []
        for res in var_combos:
            if res['var1'] == var:
                sens_values.append(abs(res['sensitivity_var1']))
            else:
                sens_values.append(abs(res['sensitivity_var2']))

        avg_sensitivity = np.mean(sens_values)
        max_sensitivity = np.max(sens_values)
        min_sensitivity = np.min(sens_values)

        var_sensitivity_stats.append({
            '变量': var,
            '平均敏感性': avg_sensitivity,
            '最大敏感性': max_sensitivity,
            '最小敏感性': min_sensitivity,
            '最敏感次数': sensitivity_count[var],
        })

    df_var_stats = pd.DataFrame(var_sensitivity_stats)
    df_var_stats = df_var_stats.sort_values(by='平均敏感性', ascending=False)
    df_var_stats.to_excel(writer, sheet_name='变量敏感性统计', index=False)

    best_detail = [
        {'项目': '最佳变量组合', '值': f"{best_result['var1']} + {best_result['var2']}"},
        {'项目': '测试集R²', '值': best_result['r2_test']},
        {'项目': '训练集R²', '值': best_result['r2_train']},
        {'项目': '测试集RMSE', '值': best_result['rmse_test']},
        {'项目': '训练集RMSE', '值': best_result['rmse_train']},
        {'项目': '常数项', '值': best_result['coef_const']},
        {'项目': '常数项_p值', '值': best_result['p_const']},
        {'项目': f'{best_result["var1"]}_原始系数', '值': best_result['coef_var1']},
        {'项目': f'{best_result["var1"]}_p值', '值': best_result['p_var1']},
        {'项目': f'{best_result["var2"]}_原始系数', '值': best_result['coef_var2']},
        {'项目': f'{best_result["var2"]}_p值', '值': best_result['p_var2']},
        {'项目': f'{best_result["var1"]}_敏感性系数', '值': best_result['sensitivity_var1']},
        {'项目': f'{best_result["var2"]}_敏感性系数', '值': best_result['sensitivity_var2']},
        {'项目': '更敏感变量', '值': best_result['more_sensitive']},
        {'项目': '敏感性绝对值之和', '值': best_result['total_sensitivity']},
    ]

    df_best = pd.DataFrame(best_detail)
    df_best.to_excel(writer, sheet_name='最佳模型', index=False)

print(f"\n✅ 敏感性分析完成！")
print(f"结果文件: {output_path}")
print(f"共分析 {total_combinations} 种组合")
print(f"最佳组合: {best_result['var1']} + {best_result['var2']} (测试集R² = {best_result['r2_test']:.4f})")