"""Uji ketahanan parameter Donchian di 3 periode (python -m research.trend_grid)."""
import itertools

import numpy as np
import pandas as pd

from research.run_scan import dataset
from research.data import resample
from research.alt import donchian
m15=dataset('m15_2012')[0]; m5=dataset('m5_2025')[0]
cut=pd.Timestamp('2018-01-01',tz='UTC')
periods={'DEV':(m15[m15.index<cut],0.30),'OOS1':(m15[m15.index>=cut],0.30),'OOS2':(resample(m5,'15min'),0.25)}
rows=[]
for tf,rule in [('M30','30min'),('H1','60min'),('H4','240min')]:
    frames={k:(resample(d,rule),sp) for k,(d,sp) in periods.items()}
    for ne,nx,sa in itertools.product([30,40,55,70,100],[10,15,20,30],[2.0,2.5,3.0,3.5]):
        if nx>=ne: continue
        row={'tf':tf,'ne':ne,'nx':nx,'sa':sa}
        for k,(d,sp) in frames.items():
            for mult,tag in [(1,''),(2,'_2xspread')]:
                if tag and k=='DEV': continue
                t=donchian(d,sp*mult,ne,nx,20,sa); r=t.R.to_numpy()
                row[k+tag]=r.mean() if len(r) else np.nan
                if not tag: row['n_'+k]=len(r)
        rows.append(row)
r=pd.DataFrame(rows)
pd.set_option('display.width',250)
for tf in ['M30','H1','H4']:
    x=r[r.tf==tf]
    print(f"{tf}: {len(x)} varian | DEV>0: {(x.DEV>0).mean()*100:.0f}% | OOS1>0: {(x.OOS1>0).mean()*100:.0f}% | OOS2>0: {(x.OOS2>0).mean()*100:.0f}% | semua>0: {((x.DEV>0)&(x.OOS1>0)&(x.OOS2>0)).mean()*100:.0f}% | rata2 exp DEV {x.DEV.mean():+.3f} OOS1 {x.OOS1.mean():+.3f} OOS2 {x.OOS2.mean():+.3f} | spread 2x OOS1 {x['OOS1_2xspread'].mean():+.3f} OOS2 {x['OOS2_2xspread'].mean():+.3f}")
# seleksi hanya dari DEV: top-5 DEV per tf, lihat OOS
print('\nTop 8 berdasarkan DEV saja (lalu lihat OOS):')
print(r.sort_values('DEV',ascending=False).head(8)[['tf','ne','nx','sa','n_DEV','DEV','n_OOS1','OOS1','n_OOS2','OOS2','OOS1_2xspread']].round(3).to_string(index=False))

