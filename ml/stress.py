"""Frozen-artifact stress test on a different simulator, never used for tuning."""
import argparse
import json
from pathlib import Path
import numpy as np
from ml.artifact import load,score
from ml.causal import snapshot,label,digest
from ml.evaluate import metrics
from simulator.generate import generate


def run(path,output):
    a=load(path);report={'artifact_hash':digest(a),'seeds':[9001,9002,9003],'held_out_severity':[.6,1.0,1.6],'purpose':'mechanism stress, not independent industrial validation','chronological_cohort_start':1893456000,'results':{},'limitations':['Simulator is authored in this repository, not independently collected','All listed mechanisms are held out from model fitting; no tuning from these results','Fixed failure cycles are simulator outcomes, not clinical or engineering failure definitions']}
    for seed,severity in zip(report['seeds'],report['held_out_severity']):
        events,truth=generate(seed=seed,start=1893456000.,severity=severity)
        outcomes={r['equipment_id']:r for r in truth};seen={};byeq={}
        for e in events:
            if e['event_id'] in seen:continue
            seen[e['event_id']]=e
            t=outcomes[e['equipment_id']]
            y=label(e['cycle'],t['failure_cycle'],t['followup_cycle'],a['horizon'],t['intervention_cycle'])
            f=snapshot(list(seen.values()),e,e['received_at']);s=score(a,f)
            stats=byeq.setdefault(e['equipment_id'],{'total':0,'abstained':0,'y':[],'p':[]})
            if y is None:continue
            stats['total']+=1
            if s['failure_probability'] is None:stats['abstained']+=1
            else:stats['y'].append(y);stats['p'].append(s['failure_probability'])
        report['results'][str(seed)]={name:dict(total=v['total'],abstained=v['abstained'],coverage=(v['total']-v['abstained'])/v['total'] if v['total'] else 0,metrics=metrics(np.array(v['y']),np.array(v['p'])) if v['y'] else None) for name,v in byeq.items()}
    Path(output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',default='benchmarks/scientific/model.json');p.add_argument('--output',default='benchmarks/stress.json');a=p.parse_args();run(a.model,a.output)
