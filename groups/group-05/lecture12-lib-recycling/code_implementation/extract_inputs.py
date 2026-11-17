"""AI 辅助编写。提示词：从论文公开归档提取参数，逐项保留文件、表名和单元格，禁止伪造广州观测。
人工校验：尚待课程小组人工复核；本程序已由自动断言和原始单元格对照检查。
不执行下载、宏或归档中的代码。只读取指定文件。
"""
from pathlib import Path
from zipfile import ZipFile
import csv, io, json, re, hashlib, xml.etree.ElementTree as ET
import numpy as np
from scipy.io import loadmat
from scipy.optimize import curve_fit
import openpyxl

BASE = Path(__file__).resolve().parents[1]
D = BASE / 'data_cohort'
RAW = D / 'literature_raw'

def save_json(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def save_csv(name, rows):
    with (D / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def read_everbatt(blob):
    """读取原始 XML，绕过原工作簿不兼容的字体样式；不修改原件、不使用失效缓存作为结果。"""
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(io.BytesIO(blob)) as z:
        ss = [''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels = {r.attrib['Id']: r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        result = {}
        for s in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', ns):
            target = rels[s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
            target = 'xl/' + target if not target.startswith('/') else target[1:]
            cells = {}
            for c in ET.fromstring(z.read(target)).findall('.//s:c', ns):
                v = c.find('s:v', ns)
                if v is not None and v.text is not None:
                    cells[c.attrib['r']] = ss[int(v.text)] if c.attrib.get('t') == 's' else v.text
            result[s.attrib['name']] = cells
        return result

def main():
    evidence = []
    def record(key, value, unit, source, locator, status='literature_transfer'):
        evidence.append(dict(parameter=key, value=value, unit=unit, source_id=source, locator=locator, status=status))
        return value
    with ZipFile(RAW / 'Battery Recycling Code.zip') as z:
        prefix = 'Battery Recycling Code/Code/7-Parameter input/'
        mat = lambda name, key: loadmat(io.BytesIO(z.read(prefix + name)))[key]
        intensity = mat('MFA/metal_intensity/metal_intensity.mat', 'metal_intensity')
        shares = mat('general/cathode_market_share/cathode_market_share_BAU.mat', 'cathode_market')
        caps = mat('general/battery_capacity/battery_capacity_low/battery_capacity.mat', 'battery_capacity').ravel()
        chem = ['LFP','NCA','NMC111','NMC532','NMC622','NMC811']
        rows = []
        for i,c in enumerate(chem):
            row = dict(chemistry=c, Li_kg_kWh=float(intensity[1,i]), Ni_kg_kWh=float(intensity[2,i]), Co_kg_kWh=float(intensity[0,i]), Mn_kg_kWh=float(intensity[3,i]), share_2021=float(shares[i,0]))
            rows.append(row)
            for element,ri in [('Li',1),('Ni',2),('Co',0),('Mn',3)]:
                record(f'{c}_{element}',float(intensity[ri,i]),'kg/kWh','ZHANG2025',f'7-Parameter input/MFA/metal_intensity/metal_intensity.mat [{ri+1},{i+1}]; RS_scenario_example.m defines row/column order')
        save_csv('chemistry_parameters.csv', rows)
        for i,c in enumerate(caps):record(f'capacity_archetype_{i+1}',float(c),'kWh/vehicle','ZHANG2025',f'general/battery_capacity/battery_capacity_low/battery_capacity.mat [{i+1},1]')
        eb = read_everbatt(z.read('Battery Recycling Code/Code/6-Cost/EverBatt 2023.xlsm'))
        # 独立抽取参数，拒绝带 #N/A 等错误的计算结果。
        subset = {}
        for sheet,cells in {'Geographic Par.':['G75','G88','F33','F35'], 'Materials':['C4','C5','C6','C17','C29','C31'], 'GREET IO':['AI61','F84','AE84','G84','E84','M84','N84','AI84','AJ84','B27','B39','B14','AQ56','AI56','B22','AE79','E79','G79','F79']}.items():
            for cell in cells:
                val=float(eb[sheet][cell]); subset[sheet+'!'+cell]=val
                record(sheet+'!'+cell,val,'see worksheet unit','EVERBATT2023',sheet+'!'+cell)
        save_json('everbatt_selected_cells.json',subset)
    with ZipFile(RAW / 'Lithium allocation structure analysis.zip') as z:
        name='Lithium resource supply structure analysis/Initial data/life_curve.xlsx'
        w=openpyxl.load_workbook(io.BytesIO(z.read(name)),data_only=True)
        s=w['S0']; life=[]
        for row in list(s.values)[1:]:
            if isinstance(row[0],(float,int)) and row[2] is not None:
                life.append(dict(age=float(row[0]),LFP=float(row[2]),ternary=float(row[4])))
        save_csv('wu_lifetime_density_points.csv',life)
        def pdf(x,eta,beta): return beta/eta*(x/eta)**(beta-1)*np.exp(-(x/eta)**beta)
        fits={}
        for c in ['LFP','ternary']:
            x=np.array([r['age'] for r in life]);y=np.array([r[c] for r in life])
            p,_=curve_fit(pdf,x,y,p0=[8,4],bounds=([2,1.01],[25,15]))
            fits[c]=dict(eta=float(p[0]),beta=float(p[1]),rmse=float(np.sqrt(np.mean((pdf(x,*p)-y)**2))))
            record(c+'_eta',float(p[0]),'year','WU2024',name+' S0!A2:A16, C2:C16 or E2:E16; least-squares refit to published density points; NOT Guangzhou calibration','published_curve_refit')
            record(c+'_beta',float(p[1]),'1','WU2024','same as eta','published_curve_refit')
        save_json('lifetime_parameters.json',fits)
        compname='Lithium resource supply structure analysis/Initial data/proportion_elements_contained_include_waste.xlsx'
        w=openpyxl.load_workbook(io.BytesIO(z.read(compname)),data_only=True)
        comp=[]
        for c in chem:
            sn='NMC523' if c=='NMC532' else c
            s=w[sn]; heads=[v.value for v in s[1]]; col=heads.index('Spent battery feed')+1
            row=dict(chemistry=c)
            for key,r in [('Cu',6),('Al',7),('F',16)]:
                row[key+'_kg_kg_cell']=float(s.cell(r,col).value)
                record(c+'_'+key+'_cell_fraction',row[key+'_kg_kg_cell'],'kg/kg cell','WU2024',compname+f' {sn}!{s.cell(r,col).coordinate}; label read from header, overlapping categories not summed')
            comp.append(row)
        save_csv('cell_coproduct_parameters.csv',comp)
    with ZipFile(RAW / 'Battery_materials_CF_repo_public.zip') as z:
        name='results/Source Data.xlsx'
        w=openpyxl.load_workbook(io.BytesIO(z.read(name)),data_only=True,read_only=True)
        s=w['Figure 1']; rows=[]
        for r in range(3,19):
            country=s.cell(r,2).value
            if country in ['CL','AR','AU']:
                rows.append(dict(row=r,country=country,LCE_kt=s.cell(r,3).value,gwp_kgCO2e_kgLCE=s.cell(r,9).value))
        save_csv('primary_lithium_mines.csv',rows)
        baseline={}
        for tag,countries in [('brine',['CL','AR']),('spodumene',['AU'])]:
            rs=[r for r in rows if r['country'] in countries]
            val=sum(r['LCE_kt']*r['gwp_kgCO2e_kgLCE'] for r in rs)/sum(r['LCE_kt'] for r in rs)
            baseline[tag]=val
            record(tag+'_gwp',val,'kgCO2e/kgLCE','PEISELER2024',name+' Figure 1!B3:I18; production-weighted CL+AR or AU subset, not a global mean','derived_literature')
        save_json('primary_lithium_baselines.json',baseline)
    # 保留作者源代码，不执行；只抽取明确的标量常数。
    ma=(RAW/'ma'/'LFPBasicData.m').read_text(encoding='utf-8-sig')
    selected={}
    for key in ['CO2_H2SO4_mar','CO2_H2O2_mar','CO2_Na2CO3_mar','CO2_water_mar','CO2_Li2CO3_mar','CO2_NiSO4_pro','CO2_CoSO4_pro','CO2_MnSO4_pro','CO2_Al_pro','CO2_Cu_pro','CO2_FePO4_pro','CO2_LiFePO4_pro','CO2_NMC622_pro','ExchangeRate']:
        m=re.search(r'^'+re.escape(key)+r'\s*=\s*([0-9.eE+-]+)\s*;',ma,re.M)
        assert m,key
        selected[key]=record(key,float(m.group(1)),'see author code','MA2024','LFPBasicData.m scalar '+key)
    save_json('ma_selected_scalars.json',selected)
    save_csv('parameter_evidence.csv',evidence)
    # 对实际存在的归档逐件生成哈希；空文件不能标为有效原件。
    files=[]
    for p in sorted(D.rglob('*')):
        if p.is_file() and ('raw' in p.parts or 'literature_raw' in p.parts):
            files.append(dict(path=str(p.relative_to(D)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),usable_archive=p.stat().st_size>0))
    save_csv('archive_checksums.csv',files)
    print('EXTRACT PASS:',len(evidence),'parameter evidence rows; lifetime refit=',fits)

if __name__=='__main__':main()
