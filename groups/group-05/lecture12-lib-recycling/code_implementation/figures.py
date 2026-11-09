"""AI辅助。Prompt：由同一结果表生成图01—10，300DPI以上，颜色与线型冗余，不伪装假设为观测。人工校验待组员确认。"""
from planning import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from test_models import rows
F=BASE/'figures_output';F.mkdir(exist_ok=True)
FONT='/usr/share/fonts/google-droid-sans-fonts/DroidSansFallbackFull.ttf'
if Path(FONT).exists():font_manager.fontManager.addfont(FONT)
plt.rcParams.update({'font.family':['Droid Sans Fallback','DejaVu Sans'],'font.size':10,'axes.unicode_minus':False,'pdf.fonttype':42,'figure.facecolor':'white'})
COL=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00','#555555'];manifest=[]
def save(fig,name,caption,sources):
    for ax in fig.axes:
        ax.spines[['top','right']].set_visible(False)
    fig.savefig(F/(name+'.png'),dpi=320,facecolor='white');fig.savefig(F/(name+'.pdf'),facecolor='white')
    manifest.append(dict(file=name,caption=caption,source_tables=sources,dpi=320));plt.close(fig)
def figaxes(n=2):return plt.subplots(1,n,figsize=(13,4.8) if n==2 else (10,5.5),layout='constrained')
def main():
    ann=rows('annual_dmfa.csv');ar=rows('recommended_annual.csv');chem=rows('chemistry_dmfa.csv');abc=json.loads((O/'anchors.json').read_text());u=json.loads((O/'design_inventory.json').read_text());d=json.loads((O/'design_year.json').read_text());rec=abc['B']
    fig,ax=figaxes();ys=[r['year'] for r in ann]
    ax[0].plot(ys,[r['vehicle_stock']/1e4 for r in ann],color=COL[0],label='重建/预测',linestyle='--')
    obs=read('vehicle_annual_2015_2025.csv');obs=[r for r in obs if r['nev_stock_vehicles']]
    ax[0].scatter([int(r['year']) for r in obs],[float(r['nev_stock_vehicles'])/1e4 for r in obs],color='black',marker='o',label='年末统计观测',zorder=5)
    ax[0].axvline(2025,color='gray',ls=':');ax[0].set(xlabel='年份',ylabel='新能源汽车保有量（万辆）',title='(a) 车辆存量与情景预测');ax[0].legend()
    ax[1].plot(ys,[r['battery_scrap_t']/1e4 for r in ann],color=COL[1],label='退役电池包',marker='o',ms=3)
    ax[1].plot([r['year'] for r in ar],[r['feed_t']/1e4 for r in ar],color=COL[0],ls='--',label='B正规收集量');ax[1].set(xlabel='年份',ylabel='电池包（万吨/年）',title='(b) 退役与收集规模');ax[1].legend()
    save(fig,'fig01_dmfa','图1 广州车辆存量与退役量；虚线为模型情景，圆点为原始年末观测。',['annual_dmfa.csv'])
    fig,ax=figaxes();ys=YEARS
    vals=[[next(r['Li_scrap_kg']/1000 for r in chem if r['year']==y and r['chemistry']==c) for y in ys] for c in CHEMS]
    ax[0].stackplot(ys,*vals,labels=CHEMS,colors=COL);ax[0].set(xlabel='年份',ylabel='退役锂（t Li/年）',title='(a) 原投入化学体系跟踪');ax[0].legend(ncol=2,fontsize=8)
    b=rows('process_balance.csv');b=[r for r in b if r['anchor']=='B' and r['year'] in [2030,2040] and r['element']=='Li'];bottom=np.zeros(2)
    for key,label,c in [('uncollected_t','未正规收集',COL[5]),('process_residue_t','处理残余',COL[1]),('product_t','合格再生产品',COL[0])]:
        val=[r[key] for r in b];ax[1].bar(['2030','2040'],val,bottom=bottom,label=label,color=c);bottom+=val
    ax[1].set(ylabel='锂元素流量（t Li/年）',title='(b) B方案区域锂去向');ax[1].legend()
    save(fig,'fig02_lithium','图2 材料结构与锂去向。未收集部分留在系统边界外，未计作已回收产品。',['chemistry_dmfa.csv','process_balance.csv'])
    fig,ax=figaxes();features=load('raw/DATAV_440100.json')['features']
    for ft in features:
        geom=ft['geometry'];polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
        for poly in polys:
            xy=np.array(poly[0]);ax[0].fill(xy[:,0],xy[:,1],color='#eeeeee',edgecolor='#777777',lw=.5)
        x,y=ft['properties']['centroid'];name=ft['properties']['name'];offset={'越秀区':(-48,12),'荔湾区':(-48,-10),'海珠区':(38,-12),'天河区':(38,12)}.get(name,(0,0));ax[0].annotate(name.replace('区',''),(x,y),xytext=offset,textcoords='offset points',fontsize=8,ha='center',arrowprops=dict(arrowstyle='-',color='#888888',lw=.5) if offset!=(0,0) else None)
    flows=rows('network_assignments.csv')
    for r in flows:ax[0].plot([r['lon'],r['centre_lon']],[r['lat'],r['centre_lat']],color=COL[0],lw=.5+6*r['fraction_total'],alpha=.65)
    centers={(r['centre'],r['centre_lon'],r['centre_lat']) for r in flows}
    for n,x,y in centers:ax[0].scatter(x,y,marker='s',s=80,facecolors='none',edgecolors=COL[1],linewidths=2)
    ax[0].set(xlabel='经度（°）',ylabel='纬度（°）',title='(a) 区级物流分配；方框为集散单元');ax[0].set_aspect(1/np.cos(np.deg2rad(23.2)))
    opts=rows('network_options.csv');ax[1].bar([str(int(r['centres'])) for r in opts],[r['weighted_first_leg_km'] for r in opts],color=COL[0]);ax[1].set(xlabel='集散单元数',ylabel='人口加权首程距离（km）',title='(b) 1—4单元距离比较')
    save(fig,'fig03_network','图3 区级候选网络；采用人口代理和直线距离×1.3，并非厂址测绘或实际行车路线。',['network_assignments.csv','network_options.csv','raw/DATAV_440100.json'])
    allr=rows('all_scenarios.csv');front=rows('pareto_front.csv');price=rec['price_CNY_tLCE'];rr=[r for r in allr if r['price_CNY_tLCE']==price and r['status']=='PASS'];ff=[r for r in front if r['price_CNY_tLCE']==price]
    fig,ax=figaxes();ax[0].scatter([r['NPV_cost_CNY']/1e8 for r in rr],[r['cumulative_Li_t']/1e4 for r in rr],s=9,color='#bbbbbb',alpha=.35,label='可行工况')
    sc=ax[0].scatter([r['NPV_cost_CNY']/1e8 for r in ff],[r['cumulative_Li_t']/1e4 for r in ff],c=[r['cumulative_avoided_tCO2']/1e6 for r in ff],cmap='viridis',s=25,label='双目标非支配集合');fig.colorbar(sc,ax=ax[0],label='累计净减排（百万t CO₂e）')
    for ix,(label,mark,c) in enumerate(zip('ABC',['s','*','^'],COL)):
        r=abc[label];ax[0].scatter(r['NPV_cost_CNY']/1e8,r['cumulative_Li_t']/1e4,marker=mark,s=180,color=c,edgecolors='black');ax[0].annotate(label,(r['NPV_cost_CNY']/1e8,r['cumulative_Li_t']/1e4),xytext=(7,7),textcoords='offset points',weight='bold')
        bars=ax[1].bar(np.arange(2)+(ix-1)*.24,[r['normalized_cost'],r['normalized_Li_loss']],width=.24,color=c,label=label,hatch=['','//','xx'][ix],edgecolor='black',linewidth=.5);ax[1].bar_label(bars,labels=[f'{v:.3f}' if v>1e-10 else '' for v in [r['normalized_cost'],r['normalized_Li_loss']]],padding=3,fontsize=8)
        for j,v in enumerate([r['normalized_cost'],r['normalized_Li_loss']]):
            if abs(v)<1e-10:
                x=j+(ix-1)*.24
                ax[1].scatter(x,0,s=75,marker='D',color=c,edgecolors='black',zorder=6,clip_on=False)
                ax[1].annotate(label+'：0\n该项最优',(x,0),xytext=(0,18),textcoords='offset points',ha='center',fontsize=9,fontweight='bold',color=c)
    ax[0].set(xlabel='规划期折现净成本（亿元）',ylabel='累计再生锂（万t Li）',title='(a) 固定基准价格的双目标前沿投影');ax[1].set(ylabel='前沿范围归一化值（越低越优）',title='(b) ABC距各项最优值的差距',ylim=(0,1.18),xticks=[0,1],xticklabels=['成本差距','回收锂量差距']);ax[1].legend();ax[1].text(.5,-.19,'0 = 该项最优（菱形标记）   1 = 前沿中该项最差',transform=ax[1].transAxes,ha='center',fontsize=9)
    save(fig,'fig07_pareto','图7 ABC从同一基准价格的双目标帕累托集合选择；锂量反向归一化；颜色表示事后评价的净减排。',['all_scenarios.csv','pareto_front.csv','anchors.json'])
    fig,ax=figaxes();li=u['Li_secondary_kg']
    keys=['electricity','heat','reagents','water_supply','transport'];labs=['电力','热能','试剂','供水','运输'];values=[u['gwp_'+k+'_kgCO2e']/li for k in keys]
    ax[0].bar(labs,values,color=COL[:5]);ax[0].set(ylabel='kg CO₂e/kg Li',title='(a) 回收全流程毛排放分项（共同产物未分配）')
    gross=u['gwp_gross_kgCO2e']/li;credit=u['gwp_credit_coproduct_kgCO2e']/li;prim=PRI
    v=[gross,gross-credit,prim['brine']*LCE,prim['spodumene']*LCE]
    ax[1].bar(['回收毛负荷','回收扣副产物信用','盐湖原生Li','锂辉石原生Li'],v,color=[COL[0],COL[2],COL[4],COL[1]]);ax[1].axhline(0,color='gray',lw=.8);ax[1].tick_params(axis='x',labelsize=8);ax[1].set(ylabel='kg CO₂e/kg Li',title='(b) 等量锂产品与系统扩展对照')
    save(fig,'fig04_carbon','图4 2030年B方案碳足迹。副产物信用以替代相应原生材料核算；负值不是厂内负排放。',['design_inventory.json','primary_lithium_baselines.json'])
    fig,ax=figaxes();dy=[r for r in chem if r['year']==2030]
    for g in [i/10 for i in range(11)]:
        uu,_=inventory(dy,rec['recovery'],g,price,rec['collection'],json.loads((O/'network_summary.json').read_text()))
        ax[0].scatter(uu['gwp_gross_kgCO2e']/uu['Li_secondary_kg'],uu['water_consumptive_L']/uu['Li_secondary_kg'],color=COL[0],s=35);ax[0].annotate(f'{g:.0%}',(uu['gwp_gross_kgCO2e']/uu['Li_secondary_kg'],uu['water_consumptive_L']/uu['Li_secondary_kg']),fontsize=7,xytext=(4,3),textcoords='offset points')
    ax[0].set(xlabel='毛碳足迹（kg CO₂e/kg Li）',ylabel='蓝水消耗情景（L/kg Li）',title='(a) 水电替代网电的水—碳权衡')
    waters=[u['water_consumptive_L']/li,24.15*LCE,77*LCE];energies=[u['energy_lifecycle_MJ']/li,33*LCE,218*LCE]
    # 不同量纲分组归一化仅用于对照，各值直接标注。
    pos=np.arange(3);ax[1].bar(pos-.18,np.array(waters)/waters[0],.36,color=COL[0],label='蓝水/B水耗');ax[1].bar(pos+.18,np.array(energies)/energies[0],.36,color=COL[1],label='能耗/B能耗')
    for i,(w,e) in enumerate(zip(waters,energies)):ax[1].text(i-.18,w/waters[0]+.04,f'{w:.0f} L',ha='center',fontsize=8);ax[1].text(i+.18,e/energies[0]+.04,f'{e:.0f} MJ',ha='center',fontsize=8)
    ax[1].set(xticks=pos,xticklabels=['回收B毛负荷','盐湖原生Li','锂辉石原生Li'],ylabel='相对各自B毛负荷（无量纲）',title='(b) 每kg Li的水耗与能耗');ax[1].legend(fontsize=8)
    save(fig,'fig05_water_energy','图5 水—碳权衡与原生对照；盐湖水耗中值24.15 L/kg LCE，范围15.5—32.8；回收毛负荷全部计于锂，副产物未分配。',['design_inventory.json','primary_water_energy.json'])
    fig,ax=figaxes();pr=rows('projects.csv');ax[0].bar([r['project_id'] for r in pr],[r['CAPEX_CNY_2030']/1e8 for r in pr],color=COL[:5]);ax[0].set(ylabel='一期投资（亿元）',title='(a) 2030对应工程投资分配')
    fin=rows('financing.csv');ax[1].plot([r['year'] for r in ar],[r['net_operating_cost_CNY']/1e8 for r in ar],marker='o',label='销售后运营缺口',color=COL[1]);ax[1].plot([r['year'] for r in fin],[r['EPR_service_CNY']/1e8 for r in fin],marker='s',ls='--',label='拟议EPR服务费',color=COL[0]);ax[1].axhline(0,color='gray',lw=.7);ax[1].set(xlabel='年份',ylabel='亿元/年',title='(b) 收支与服务费安排');ax[1].legend(fontsize=8)
    save(fig,'fig06_finance','图6 工程投资与逐年收支，EPR为拟议合同服务费，不是已获得财政补贴。',['projects.csv','financing.csv','recommended_annual.csv'])
    fig,ax=figaxes();sen=rows('sensitivity.csv');labels={'price':'碳酸锂价格','capex_multiplier':'投资倍率','opex_multiplier':'运营费用倍率','product_sales_realization':'销售兑现率','process_heat_MJ_kgcell':'工艺热耗','product_substitution_quality':'材料替代比例'}
    for i,(k,label) in enumerate(labels.items()):
        sr=[r for r in sen if r['parameter']==k];vals=[r['NPV_cost_CNY']/1e8 for r in sr];ax[0].plot([min(vals),max(vals)],[i,i],color=COL[i],lw=5);ax[0].scatter(vals,[i]*len(vals),color=COL[i],s=20)
    ax[0].axvline(rec['NPV_cost_CNY']/1e8,ls='--',color='black');ax[0].set(yticks=range(len(labels)),yticklabels=list(labels.values()),xlabel='固定B的折现净成本（亿元）',title='(a) 单因素压力测试')
    for ix,(label,mark,c) in enumerate(zip('ABC',['s','*','^'],COL)):
        prices=A['price_CNY_tLCE'];an=json.loads((O/'anchors_by_price.json').read_text());ax[1].plot([p/1e4 for p in prices],[an[str(p)][label]['NPV_cost_CNY']/1e8 for p in prices],marker=mark,color=c,label=label)
    ax[1].set(xlabel='外生LCE价格（万元/t）',ylabel='各价格独立寻优后的净成本（亿元）',title='(b) 价格改变后的ABC');ax[1].legend()
    save(fig,'fig08_sensitivity','图8 左侧固定B压力测试；右侧三个外生价格分别重选ABC，两种分析不混用。',['sensitivity.csv','anchors_by_price.json'])
    fig,ax=figaxes();unc=rows('uncertainty.csv')
    for k,c in zip(['future_saturation_vehicles','battery_life_multiplier'],COL):
        low=[];hi=[]
        for y in YEARS:
            vs=[r['scrap_pack_t']/1e4 for r in unc if r['year']==y and r['parameter']==k];low.append(min(vs));hi.append(max(vs))
        ax[0].fill_between(YEARS,low,hi,alpha=.2,color=c,label='普及上限情景' if k.startswith('future') else '电池寿命±20%')
    ax[0].plot(YEARS,[next(r['battery_scrap_t']/1e4 for r in ann if r['year']==y) for y in YEARS],color='black',label='基准');ax[0].set(xlabel='年份',ylabel='退役电池（万吨/年）',title='(a) 独立假设范围，非概率置信区间');ax[0].legend(fontsize=8)
    ax[1].step(YEARS,[r['capacity_tpa']/1e4 for r in ar],where='post',color=COL[0],label='名义能力');ax[1].plot(YEARS,[r['feed_t']/1e4 for r in ar],marker='o',color=COL[1],label='正规收集量');ax[1].plot(YEARS,[r['outsourced_t']/1e4 for r in ar],ls=':',color=COL[2],label='委托处理');ax[1].set(xlabel='年份',ylabel='电池包（万吨/年）',title='(b) B分期建设与委托处理');ax[1].legend(fontsize=8)
    save(fig,'fig09_capacity','图9 退役预测假设范围及B分期能力；2026—2027委托处理量纳入成本与环境账。',['uncertainty.csv','recommended_annual.csv'])
    fig,ax=figaxes();re=rows('reuse_delay.csv');routes=rows('route_comparison.csv')
    ax[0].plot(YEARS,[r['baseline_Li_t'] for r in re],marker='o',color=COL[0],label='主线及时再生');ax[0].plot(YEARS,[r['reuse_delayed_Li_t'] for r in re],marker='s',ls='--',color=COL[1],label='20%延后5年');ax[0].set(xlabel='年份',ylabel='再生锂供应（t Li/年）',title='(a) 梯次利用的供应时间效应');ax[0].legend(fontsize=8)
    for direct,c in zip([0,.25,.5],COL):
        rs=[r for r in routes if r['direct_LFP_share']==direct];ax[1].plot([r['price_CNY_tLCE']/1e4 for r in rs],[r['variable_net_cost_CNY_tpack'] for r in rs],marker='o',color=c,label=f'LFP修复份额{direct:.0%}')
    ax[1].axhline(0,color='gray',lw=.7);ax[1].set(xlabel='LCE情景价格（万元/t）',ylabel='变动净成本（元/t电池包）',title='(b) 湿法与材料修复探索比较');ax[1].legend(fontsize=8)
    save(fig,'fig10_pathways','图10 再利用延迟与技术路径探索。材料修复使用Ma补锂代理，尚未计专线投资及验证费用，不纳入主方案双目标排序。',['reuse_delay.csv','route_comparison.csv'])
    fig,ax=figaxes();env=[r for r in rows('environment_pareto_front.csv') if r['price_CNY_tLCE']==price]
    ax[0].scatter([r['NPV_cost_CNY']/1e8 for r in rr],[r['cumulative_avoided_tCO2']/1e4 for r in rr],s=10,color='#bbbbbb',label='全部可行方案')
    ax[0].scatter([r['NPV_cost_CNY']/1e8 for r in env],[r['cumulative_avoided_tCO2']/1e4 for r in env],s=20,color=COL[0],label='环境—经济前沿')
    for label,c in zip('ABC',COL):
        r=abc[label];ax[0].scatter(r['NPV_cost_CNY']/1e8,r['cumulative_avoided_tCO2']/1e4,marker='s',s=60,color=c,edgecolors='black');ax[0].annotate(label,(r['NPV_cost_CNY']/1e8,r['cumulative_avoided_tCO2']/1e4),xytext=(5,5),textcoords='offset points')
    ax[0].set(xlabel='折现净成本（亿元）',ylabel='累计净减排（万t CO₂e）',title='(a) 成本—净减排辅助前沿');ax[0].legend(fontsize=8)
    bars=ax[1].bar(list('ABC'),[abc[k]['cumulative_gross_tCO2']*1000/(abc[k]['cumulative_Li_t']*1000) for k in 'ABC'],color=COL[:3],edgecolor='black');ax[1].bar_label(bars,fmt='%.2f',padding=3)
    ax[1].set(ylabel='毛碳足迹（kg CO₂e/kg Li）',title='(b) 主方案单位锂碳足迹');ax[1].margins(y=.15)
    save(fig,'fig11_environment','图11 成本—净减排辅助分析及ABC事后碳足迹评价。',['environment_pareto_front.csv','anchors.json'])
    (F/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print('FIGURES',len(manifest))
if __name__=='__main__':main()
