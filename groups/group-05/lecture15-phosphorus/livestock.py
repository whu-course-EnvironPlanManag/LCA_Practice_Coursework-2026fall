import csv
import openpyxl
from manure_audit import estimate

def inputs(rev,data,out,write):
    stocks,excluded=estimate(data)
    write(out/'stock.csv',stocks)
    write(out/'excluded.csv',excluded)
    book=openpyxl.load_workbook(next(rev.glob('3.P content*')),read_only=True,data_only=True)
    coefficients={str(r[0]).strip():r[2] for r in book.active.values}
    book.close()
    selected=[]
    tokens=('buffalo','cattle','chickens','ducks','goat','pig with','sheep','horses')
    with next(rev.glob('**/Raw data*/2022.csv')).open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            name=r['Item']
            if r['Area']!='World' or r['Element']!='Production' or r['Unit']!='t' or not r['Value']:continue
            if (name.startswith(('Meat of ','Raw milk of ')) and any(t in name for t in tokens)) or name=='Hen eggs in shell, fresh':
                coef=coefficients[name]
                selected.append(dict(item=name,tons=float(r['Value']),mass_fraction=coef,P_Mt=float(r['Value'])*coef/1e6))
    assert len(selected)>=12 and len(set(x['item'] for x in selected))==len(selected)
    write(out/'animal_products.csv',selected)
    return sum(x['P_Mt'] for x in selected),sum(x['manure_Mt_P'] for x in stocks)
