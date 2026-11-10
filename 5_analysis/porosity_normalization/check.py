# Do Gamma and tortuosity differ between soils beyond visible porosity? (2026-10-06)
import csv, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
# Specimen-level Gamma & visible porosity at ~15 um (merged_specimen_level_ct_only.csv + rehovot samp3 from missing_data_20261004)
sp=[('V','specA',15.17,0.7549),('V','specB',21.64,0.8593),('L','5p85_ds15',26.57,0.9361),('L','8p8_ds15',20.34,0.9313),
    ('L','Cu011_samp_2',26.18,0.93),('S','samp2',30.50,0.9889),('S','samp3',40.85,0.9974)]
def fit(X,Y):
    n=len(X);mx=sum(X)/n;my=sum(Y)/n
    b=sum((a-mx)*(c-my) for a,c in zip(X,Y))/sum((a-mx)**2 for a in X);a0=my-b*mx
    r2=1-sum((c-a0-b*a)**2 for a,c in zip(X,Y))/sum((c-my)**2 for c in Y);return a0,b,r2
X=[p/100 for _,_,p,_ in sp]; Y=[math.log(g/(1-g)) for *_,g in sp]
a0,b,r2=fit(X,Y); print(f"Gamma: logit(G) ~ porosity, slope={b:.2f}, R2={r2:.2f}")
for s in 'VLS':
    r=[y-a0-b*x for (k,*_),x,y in zip(sp,X,Y) if k==s]; print(s,'mean residual',round(sum(r)/len(r),2),'| Gamma/porosity',round(sum(g/(p/100) for k,_,p,g in sp if k==s)/len(r),2))
rows=[r for r in csv.DictReader(open(os.path.join(HERE, '..', 'tortuosity', 'tortuosity_subvolumes.csv'))) if r['status']=='ok' and r['cube_size']=='200' and r['phase']=='original']
X=[math.log(float(r['porosity'])) for r in rows]; Y=[math.log(float(r['tortuosity'])) for r in rows]
a0,b,r2=fit(X,Y); print(f"Tortuosity: log(tau) ~ log(porosity), n={len(rows)}, slope={b:.2f}, R2={r2:.2f}")
for s in ['Vertisol','Loess','Sand']:
    r=[y-a0-b*x for x,y,row in zip(X,Y,rows) if row['soil']==s]; print(s,'mean residual (log units)',round(sum(r)/len(r),2),'n',len(r))
