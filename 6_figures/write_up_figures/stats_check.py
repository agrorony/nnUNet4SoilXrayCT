from common import *
jars=respiration(); cm=cmic(); corg=corg_percent()
out=[]
def report(name, groups):
    a=anova(groups); asm=assumptions(groups)
    lt=cld(groups,tukey_pvalues(groups)) if a['p']<0.05 else ['a']*3
    ll=cld(groups,lsd_pvalues(groups)) if a['p']<0.05 else ['a']*3
    m=[round(float(np.mean(g)),2) for g in groups]; se=[round(float(stats.sem(g)),2) for g in groups]
    line=(f"{name:22s} F({a['df1']},{a['df2']})={a['F']:.2f}, {ptxt(a['p'])}, eta2={a['eta2']:.2f} | Shapiro p={asm['shapiro_p']:.3f}, Brown-Forsythe p={asm['bf_p']:.3f} | "
          f"means L/V/S {m} SE {se} | Tukey {''.join(x+' ' for x in lt)}| LSD {''.join(x+' ' for x in ll)}| pairs L-V, L-S, V-S: LSD p {np.round(lsd_pvalues(groups)[[0,0,1],[1,2,2]],4).tolist()} Tukey p {np.round(tukey_pvalues(groups)[[0,0,1],[1,2,2]],4).tolist()}")
    print(line); out.append(line)
report('cumulative CO2-C', [[jars[j]['cum'] for j in soil_jars(jars,s)] for s in ORDER])
for k,p in enumerate(['d1-3','d4-7','d8-10','d11-15']):
    report('rate '+p, [[jars[j]['rate'][k] for j in soil_jars(jars,s)] for s in ORDER])
report('Cmic', [list(cm[s].values()) for s in ORDER])
q={s:[jars[j]['rate'][3]/cm[s][int(j[1])]*1000/24 for j in soil_jars(jars,s)] for s in ORDER}
report('qCO2 (d11-15)', [q[s] for s in ORDER])
cc={s:[cm[s][r]/(corg[s]*1e4)*100 for r in sorted(cm[s])] for s in ORDER}
report('Cmic/Corg %', [cc[s] for s in ORDER])
open('out/stats_tukey_vs_lsd.txt','w').write('\n'.join(out)+'\n')
