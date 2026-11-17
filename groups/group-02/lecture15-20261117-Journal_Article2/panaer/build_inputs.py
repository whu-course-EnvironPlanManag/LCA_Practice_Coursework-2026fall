from pathlib import Path
import json
import pandas as pd
import openpyxl
ROOT=Path(__file__).resolve().parent
from source_paths import configure
S,O=configure(__file__, ['015.xlsx','016.xlsx','017.xlsx','018.xlsx','production_2022.csv','004.csv','005.csv','022.xlsx','011.xlsx','012.xlsx','013.xlsx','014.xlsx'])
regions=['World','China, mainland','United States of America','India']
for num,name in [('015','production'),('016','exports'),('017','imports')]:
    df=pd.read_excel(S.file(f'{num}.xlsx'),sheet_name=0)
    df.columns=[int(str(c)) if str(c).isdigit() else str(c).strip() for c in df.columns]
    df=df[df.Country.isin(regions)][['Country','Product',*range(1961,2023)]]
    df.to_csv(O/f'{name}_1961_2022.csv',index=False,encoding='utf-8-sig')
    print(name,df.shape,df.Country.unique())
coeff=pd.read_excel(S.file('018.xlsx')).iloc[:,:3].dropna(subset=['Product'])
coeff.to_csv(O/'production_coefficients.csv',index=False,encoding='utf-8-sig')
raw=pd.read_csv(S.file('production_2022.csv'),encoding='utf-8-sig')
raw=raw[raw.Area.isin(regions)&raw.Item.isin(['Rice','Wheat','Maize (corn)'])&raw.Element.eq('Production')]
merged=raw.merge(coeff,left_on='Item',right_on='Product',validate='many_to_one')
merged['P_t']=merged.Value*merged.Coefficient
merged.to_csv(O/'typical_crops_2022.csv',index=False,encoding='utf-8-sig')
print(merged[['Area','Item','Value','Coefficient','P_t']].to_string(index=False))
fert=pd.read_csv(S.file('004.csv'),encoding='gb18030',low_memory=False)
print('YEAR',fert.Year.unique()[-6:])
fert['Year']=pd.to_numeric(fert.Year,errors='coerce')
fert=fert[fert.Element.eq('Agricultural Use')]
fert=fert[['Area','Area Code (M49)','Year','Unit','Value','P(t)']]
fert['Value']=pd.to_numeric(fert.Value,errors='coerce')
fert['P(t)']=pd.to_numeric(fert['P(t)'],errors='coerce')
fert.to_csv(O/'fertilizer_use.csv',index=False,encoding='utf-8-sig')
print('fert years',fert.Year.min(),fert.Year.max(),fert[fert.Year.eq(2022)].to_string(index=False))
land=pd.read_csv(S.file('005.csv'),encoding='utf-8-sig')
land=land[land.Area.eq('World')&land.Element.eq('Area')]
land[['Year','Unit','Value']].to_csv(O/'world_cropland.csv',index=False,encoding='utf-8-sig')
wb=openpyxl.load_workbook(S.file('022.xlsx'),data_only=True,read_only=True)
pop=[]
for sheet,year in [('Estimates',2022),('Medium variant',2050)]:
    ws=wb[sheet]
    for row in ws.iter_rows(min_row=18,values_only=True):
        if row[2] in ['World','China','India','United States of America'] and row[10]==year:
            pop.append({'region':row[2],'year':year,'population':row[12]*1000,'source_sheet':sheet,'source':'UN WPP 2024, 1 July'})
pd.DataFrame(pop).to_csv(O/'population.csv',index=False,encoding='utf-8-sig')
print('POP',pop)
for n in ['011','012','013','014']:
    d=pd.read_excel(S.file(f'{n}.xlsx'),sheet_name='Sorted by R²')
    d[d['Variable Combination'].isin(['E + G','B + E','A + J'])].to_csv(O/f'published_regression_{n}.csv',index=False,encoding='utf-8-sig')
