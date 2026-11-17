import pandas as pd


df = pd.read_csv(
     r'D:\global\trade\exp\data1.csv',
    sep=',',
    header=None,
    names=['Country', 'Year', 'Product', 'Production'],
    dtype={'Country': str, 'Product': str},
    low_memory=False
)


df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')


df['Production'] = pd.to_numeric(df['Production'], errors='coerce')


grouped = df.groupby(['Country', 'Year', 'Product']).sum().reset_index()


pivot_table = grouped.pivot_table(index=['Country', 'Product'], columns='Year', values='Production', fill_value=0)


pivot_table = pivot_table.reset_index()


pivot_table.to_csv('result1.csv', index=False)

