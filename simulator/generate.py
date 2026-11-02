import argparse
import json
from pathlib import Path
import numpy as np
from ml.causal import UNITS,SENSORS

SCENARIOS=('healthy_load','degradation','abrupt','bias','stuck','missing','duplicates','delayed','restart','maintenance','simultaneous','unknown')


def generate(seed=42,cycles=100,start=1760000000.,severity=1.0):
    rng=np.random.default_rng(seed);events=[];truth=[]
    for name in SCENARIOS:
        values=np.array([65.,2.,100.,40.,1500.]);noise=np.array([1.,.1,2.,1.,15.]);stuck=None
        for cycle in range(1,cycles+1):
            x=values+noise*rng.normal(size=5);quality={s:'good' for s in SENSORS}
            if name=='healthy_load': x+=np.sin(cycle/12)*noise*2
            if name in ('degradation','simultaneous'):x[:2]+=np.maximum(0,cycle-40)*np.array([.5,.08])
            if name=='abrupt' and cycle>=80:x[:2]+=np.array([25.,5.])
            if name=='bias':x[0]+=10
            if name=='stuck':
                if stuck is None:stuck=x[1]
                x[1]=stuck
            if name=='unknown':x+=np.sin(cycle*.77)*noise*6
            if name=='simultaneous':x[2]-=max(0,cycle-60)
            if name=='maintenance':x[:2]+=max(0,cycle-30)*np.array([.5,.08]) if cycle<70 else 0
            x=values+(x-values)*severity
            payload={s:float(v) for s,v in zip(SENSORS,x)}
            if name=='missing' and cycle%4==0:payload['vibration']=None;quality['vibration']='missing'
            observed=start+cycle*60
            event={'event_id':f'{seed}:{name}:{cycle}','equipment_id':name,'lifecycle_id':'after-maintenance' if name=='maintenance' and cycle>=70 else 'original','session_id':'restarted' if name=='restart' and cycle>=60 else 'boot1','sequence':cycle-60 if name=='restart' and cycle>=60 else cycle,'cycle':cycle,'observed_at':observed,'received_at':observed+(600 if name=='delayed' and cycle%5==0 else 0),'schema_version':1,'units':dict(UNITS),'quality':quality,'values':payload}
            events.append(event)
            if name=='duplicates' and cycle%7==0:events.append(dict(event))
        truth.append({'equipment_id':name,'failure_cycle':90 if name in ('degradation','abrupt','simultaneous') else None,'intervention_cycle':70 if name=='maintenance' else None,'followup_cycle':cycles,'mechanism':name})
    return sorted(events,key=lambda e:(e['received_at'],e['event_id'])),truth

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=42);p.add_argument('--output',default='experiments/simulator');a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    events,truth=generate(a.seed)
    (out/'telemetry.json').write_text(json.dumps(events));(out/'hidden_outcomes.json').write_text(json.dumps(truth))
