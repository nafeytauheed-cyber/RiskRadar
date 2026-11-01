"""Reproducible equipment-disjoint experiment on repository synthetic histories.
Run: OPENBLAS_NUM_THREADS=1 python -m ml.evaluate --output experiments/local
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
from .causal import SENSORS, FEATURES, FEATURE_VERSION, snapshot, label, digest
from .artifact import validate, score
from .policy_metrics import evaluate_policy, selective_error


def metrics(y, p):
    return {'precision': float(precision_score(y,p>=.5,zero_division=0)),
            'recall': float(recall_score(y,p>=.5,zero_division=0)),
            'pr_auc': float(average_precision_score(y,p)) if len(set(y))>1 else None,
            'brier': float(brier_score_loss(y,p)), 'log_loss': float(log_loss(y,p,labels=[0,1]))}


def reliability(y,p):
    out=[]
    for lo in np.arange(0,1,.1):
        idx=(p>=lo)&(p<lo+.1 if lo<.9 else p<=1)
        out.append({'lower':float(lo),'n':int(idx.sum()),'predicted':float(p[idx].mean()) if idx.any() else None,'observed':float(y[idx].mean()) if idx.any() else None})
    return out


def build(data_dir):
    hist=pd.read_csv(data_dir/'sensor_readings_history.csv')
    failures=pd.read_csv(data_dir/'failure_history.csv')
    if failures.equipment_id.duplicated().any():
        raise ValueError('ambiguous lifecycle outcomes')
    outcomes=failures.set_index('equipment_id').failure_cycle.to_dict()
    rows=[]
    coverage={'total':len(hist),'eligible':0,'excluded_quality_or_censored':0}
    for eq,g in hist.groupby('equipment_id'):
        events=[]
        for r in g.sort_values('cycle').to_dict('records'):
            observed=pd.Timestamp(r['timestamp'],tz='UTC').timestamp()
            e={'event_id':f'{eq}:{r["cycle"]}', 'equipment_id':eq, 'lifecycle_id':'original', 'session_id':'original',
               'sequence':int(r['cycle']), 'cycle':int(r['cycle']), 'observed_at':observed,'received_at':observed,
               'values':{s:float(r[s]) if pd.notna(r[s]) else None for s in SENSORS},'quality':{s:'good' for s in SENSORS}}
            events.append(e)
            f=snapshot(events[-10:],e,observed)
            y=label(e['cycle'],outcomes.get(eq),int(g.cycle.max()),30)
            if y is not None and f['quality_state'] in ('good','imputed'):
                rows.append({'equipment_id':eq,'cycle':e['cycle'],'label':y,'failure_cycle':outcomes.get(eq), 'features':f['features']})
    coverage['eligible']=len(rows); coverage['excluded_quality_or_censored']=coverage['total']-len(rows)
    return rows,coverage


def run(output):
    start=time.perf_counter(); output=Path(output); output.mkdir(parents=True,exist_ok=True)
    data_dir=Path('backend/app/data'); rows,coverage=build(data_dir)
    ids=sorted({r['equipment_id'] for r in rows}); rng=np.random.default_rng(20261101); rng.shuffle(ids)
    n=len(ids); cuts=[int(n*.5),int(n*.65),int(n*.8)]
    parts=dict(zip(('train','selection','calibration','test'),np.split(np.array(ids),cuts)))
    parts={k:list(v) for k,v in parts.items()}
    arrays={}
    for k,group in parts.items():
        rr=[r for r in rows if r['equipment_id'] in group]
        arrays[k]=(np.array([r['features'] for r in rr]),np.array([r['label'] for r in rr]),rr)
    scaler=StandardScaler().fit(arrays['train'][0]); X={k:scaler.transform(v[0]) for k,v in arrays.items()}
    candidates={}; selection={}
    for c in (.1,1.,10.):
        m=LogisticRegression(C=c,max_iter=1000,random_state=42).fit(X['train'],arrays['train'][1])
        candidates[c]=m; selection[str(c)]=metrics(arrays['selection'][1],m.predict_proba(X['selection'])[:,1])
    best=min(candidates,key=lambda c:selection[str(c)]['log_loss']); m=candidates[best]
    calibrator=LogisticRegression(C=1.,random_state=42).fit(m.decision_function(X['calibration']).reshape(-1,1),arrays['calibration'][1])
    p=calibrator.predict_proba(m.decision_function(X['test']).reshape(-1,1))[:,1]; y=arrays['test'][1]
    boost=GradientBoostingClassifier(n_estimators=80,max_depth=2,random_state=42).fit(X['train'],arrays['train'][1])
    gbcal=LogisticRegression(random_state=42).fit(boost.decision_function(X['calibration']).reshape(-1,1),arrays['calibration'][1])
    pg=gbcal.predict_proba(boost.decision_function(X['test']).reshape(-1,1))[:,1]
    iso=IsolationForest(n_estimators=100,random_state=42,n_jobs=1).fit(X['train'][arrays['train'][1]==0])
    raw=-iso.score_samples(X['test']); trainraw=-iso.score_samples(X['train'][arrays['train'][1]==0]); threshold=float(np.quantile(trainraw,.95))
    z=np.max(abs(X['test']),axis=1); zcut=float(np.quantile(np.max(abs(X['train'][arrays['train'][1]==0]),axis=1),.95))
    # Match one first warning within H cycles before each failure; early alerts count as false alerts.
    lead=[]; false=0; exposure=0
    for eq in parts['test']:
        idx=[i for i,r in enumerate(arrays['test'][2]) if r['equipment_id']==eq]
        rr=[arrays['test'][2][i] for i in idx]; alerts=[r['cycle'] for i,r in zip(idx,rr) if p[i]>=.5]
        failure=rr[0]['failure_cycle']; matched=[c for c in alerts if 0<failure-c<=30]
        if matched: lead.append(failure-min(matched))
        false+=sum(not (0<failure-c<=30) for c in alerts)
        exposure+=max(r['cycle'] for r in rr)-min(r['cycle'] for r in rr)+1
    boot=[]
    for _ in range(300):
        sampled=rng.choice(parts['test'],len(parts['test']),replace=True)
        ii=[i for eq in sampled for i,r in enumerate(arrays['test'][2]) if r['equipment_id']==eq]
        boot.append(brier_score_loss(y[ii],p[ii]))
    provenance={'seed':20261101,'splits':parts,'data':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data_dir.glob('*.csv')},'dataset':'repository synthetic; no external validation','selected_C':best}
    artifact=validate({'format':'riskradar-logistic-v1','features':list(FEATURES),'feature_version':FEATURE_VERSION,'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'coef':m.coef_[0].tolist(),'intercept':float(m.intercept_[0]),'calibration':{'slope':float(calibrator.coef_[0,0]),'intercept':float(calibrator.intercept_[0]),'version':'platt-v1'},'baseline':'training-only-standard-scaler','horizon':30,'provenance':provenance})
    result={'data_provenance':provenance,'coverage':coverage,'selection':selection,'abstention_coverage_error':selective_error(y,p),'incident_policy':evaluate_policy(arrays['test'][2],p),'test':{'logistic_calibrated':metrics(y,p),'gradient_boosting_calibrated':metrics(y,pg), 'isolation_forest':{'precision':float(precision_score(y,raw>=threshold,zero_division=0)),'recall':float(recall_score(y,raw>=threshold,zero_division=0)),'pr_auc':float(average_precision_score(y,raw))},'training_z_threshold':{'precision':float(precision_score(y,z>=zcut,zero_division=0)),'recall':float(recall_score(y,z>=zcut,zero_division=0))}},'reliability':reliability(y,p),'equipment_bootstrap_brier_95pct':np.quantile(boot,[.025,.975]).tolist(),'warning_lead_cycles':lead,'false_alert_events_per_1000_operating_cycles':false/exposure*1000,'chronological_evaluation':'BLOCKED: repository histories all start together; no independent later cohort','limitations':['Synthetic-only; no real equipment validity claim','Bootstrap is imprecise with a small number of test lifecycles','No fault-identification accuracy claimed','Incident policy comparison assumes no operator resolutions within a lifecycle'], 'runtime_seconds':time.perf_counter()-start,'environment':{'python':platform.python_version(),'platform':platform.platform()},'artifact_hash':digest(artifact)}
    exported=np.array([score(artifact,{'quality_state':'good','features':list(v)})['failure_probability'] for v in arrays['test'][0]])
    if not np.allclose(exported,p,atol=1e-12,rtol=1e-12):raise AssertionError('exported serving model differs from offline probabilities')
    result['export_max_probability_error']=float(abs(exported-p).max())
    (output/'model.json').write_text(json.dumps(artifact,indent=2)); (output/'results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='experiments/local'); run(parser.parse_args().output)
