"""Independent 2022 manure estimate. Missing species are reported, never set to zero."""
from pathlib import Path
import argparse,csv,json
from run import write_csv
# SI coefficient table printed page 121; kg P/head/year after unit normalization.
COEFFICIENTS={'3.Buffalo.csv':15.2,'5.Cattle.csv':5.6,'9.Goats.csv':.1,'16.Sheep.csv':.1,'10.Horses.csv':6.8,'17.Swine  pigs.csv':2.4,'6.Chickens.csv':135/1000,'7.Ducks.csv':384/1000}

def estimate(root):
    folder=root/'Origin data'/'5.Original data on live animal products (national-level production and trade)'/'Production and stock'
    results=[];missing=[]
    for path in sorted(folder.glob('*.csv')):
        for encoding in ['utf-8-sig','gb18030']:
            try:
                with path.open(encoding=encoding) as f:rows=list(csv.DictReader(f))
                break
            except UnicodeDecodeError:continue
        selected=[r for r in rows if r['Area']=='World' and r['Year']=='2022' and r['Element']=='Stocks' and r['Value']]
        if path.name not in COEFFICIENTS:
            missing.append(dict(file=path.name,status='未赋排磷系数，不纳入合计',records=len(selected),unit=';'.join(r['Unit'] for r in selected),stock=';'.join(r['Value'] for r in selected)))
            continue
        assert len(selected)==1,(path.name,len(selected))
        r=selected[0];assert r['Unit'] in ['An','1000 An'],r
        head=float(r['Value'])*(1000 if r['Unit']=='1000 An' else 1)
        coeff=COEFFICIENTS[path.name]
        results.append(dict(species=r['Item'],source_file=path.name,year=2022,raw_stock=float(r['Value']),raw_unit=r['Unit'],heads=head,coefficient_kg_P_head_year=coeff,manure_Mt_P=head*coeff/1e9,coefficient_source='SI printed p121 kDC; annual stocks used as head-year proxy'))
    assert len(results)==8
    return results,missing

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,default=Path(__file__).resolve().parent.parent/'环境规划与管理-第十五讲20261117'/'source_data');ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'outputs');a=ap.parse_args();a.output.mkdir(exist_ok=True,parents=True)
    rows,missing=estimate(a.data);write_csv(a.output/'manure_independent_2022.csv',rows);write_csv(a.output/'manure_uncovered_species.csv',missing)
    total=sum(r['manure_Mt_P'] for r in rows)
    b=json.loads((a.output/'results.json').read_text());animal=b['categories']['G'];old=animal*(1/.23-1)
    comparison=dict(covered_species=8,covered_manure_Mt=total,old_inferred_manure_Mt=old,covered_vs_old_pct=100*(total/old-1),coverage='Partial species coverage; not a complete global estimate',decision='不以部分物种合计直接替代全口径量；暂保留原模型并标明需统一LBS边界')
    (a.output/'manure_comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2))
    lines=['# 2022年粪便独立核算','', '|物种|存栏（头/只）|系数 kg P/头/年|粪便 Mt P/年|','|---|---:|---:|---:|']
    for r in rows:lines.append(f'|{r["species"]}|{r["heads"]:,.0f}|{r["coefficient_kg_P_head_year"]:.3f}|{r["manure_Mt_P"]:.4f}|')
    lines+=['',f'八类合计{total:.6f} Mt P/年；旧模型PUE反推{old:.6f} Mt P/年，差异{comparison["covered_vs_old_pct"]:.2f}%。','', '仅用World、Stocks和2022非空记录，忽略空白重复行。鸡鸭以千只记录，先转为只；论文系数135、384 kg/千只/年分别转为0.135、0.384 kg/只/年。','', '未覆盖物种不赋零系数，详见manure_uncovered_species.csv。蜜蜂数量不能直接视为普通牲畜头数。年度存栏作为全年平均存栏的代理，具有统计误差。','', '山羊与绵羊主表系数0.1 kg/头/年，与交叉验证表羊1.6存在明显差别。两套参数不可混用以追求特定占比；后续必须按模型路径保留参数来源。','', '由于现模型动物产品G包含更广产品，八类存栏排磷量暂不直接替代其全口径反推量。本次提供独立约束，不据此宣称基线修正完成。']
    (a.output/'粪便独立核算.md').write_text('\n'.join(lines))
    print(json.dumps(comparison,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
