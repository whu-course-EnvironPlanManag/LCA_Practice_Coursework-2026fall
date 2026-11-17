from pathlib import Path
import pandas as pd
import json
from source_paths import configure
S,D=configure(__file__, ['production_2022.csv','018.xlsx','004.csv','005.csv','022.xlsx'])
raw=pd.read_csv(S.file('production_2022.csv'),encoding='utf-8-sig')
coef=pd.read_excel(S.file('018.xlsx')).iloc[:,:3].dropna(subset=['Product'])
print('coeff',coef.columns.tolist(),coef.head(3).to_string(index=False))
sel=raw[raw.Area.eq('World')&raw.Element.eq('Production')].copy()
join=sel.merge(coef,left_on='Item',right_on='Product',validate='many_to_one')
join['P_t']=join.Value*join.Coefficient
join.to_csv(D/'world_products_2022_joined.csv',index=False,encoding='utf-8-sig')
print(join.groupby('Category').P_t.sum().to_string())
land=pd.read_csv(S.file('005.csv'),encoding='utf-8-sig')
print('land areas',land.Area.unique()[:12])
f=pd.read_csv(S.file('004.csv'),encoding='gb18030',low_memory=False)
f=f[f.Element.eq('Agricultural Use')]
print('fert1961',f[f.Year.eq(1961)].Value.sum()*.4364/1e6)
print('area count',f.Area.nunique())
# Preserve real 2021 inputs; do not relabel these observations as 2022.
f[f.Area.isin(['China, mainland','India','United States of America'])&f.Year.eq(2021)].to_csv(D/'country_fertilizer_2021.csv',index=False,encoding='utf-8-sig')
print('land country',land[land.Year.eq(2022)].Area.unique()[:10])

import openpyxl
wb=openpyxl.load_workbook(S.file('022.xlsx'),read_only=True,data_only=True)
rows=[]
for sheet,year in [('Estimates',2021),('Medium variant',2050)]:
    for row in wb[sheet].iter_rows(min_row=18,values_only=True):
        if row[2] in ['China','India','United States of America'] and row[10]==year:
            rows.append(dict(region=row[2],year=year,population=row[12]*1000,source='UN WPP 2024; 1 July'))
pd.DataFrame(rows).to_csv(D/'country_population_2021_2050.csv',index=False,encoding='utf-8-sig')
