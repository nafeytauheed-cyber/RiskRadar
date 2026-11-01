"""Pinned replay: pure scoring, separate scope, no incident/outbox code path."""
import argparse
from psycopg.types.json import Jsonb
from ml.causal import snapshot, digest, FEATURE_VERSION
from ml.artifact import validate,score
from .db import connect
from .service import event_dict


def compute(events,artifacts,mode):
    if mode not in ('arrival','corrected'): raise ValueError('invalid replay mode')
    if not events: return []
    order=sorted(events,key=lambda e:(e['received_at'],e['event_id'])) if mode=='arrival' else sorted(events,key=lambda e:(e['observed_at'],e['equipment_id'],e['session_id'],e['sequence'],e['event_id']))
    end=max(e['received_at'] for e in events)
    results=[]
    for target in order:
        cutoff=target['received_at'] if mode=='arrival' else end
        f=snapshot(events,target,cutoff,freshness_cutoff=target['received_at'])
        for model_id,a in sorted(artifacts.items()):
            validate(a,model_id)
            results.append({'event_id':target['event_id'],'model_id':model_id,'snapshot':f,'output':dict(score(a,f),quality_state=f['quality_state'],horizon_cycles=a['horizon'],mode=mode)})
    return results


def run(tenant,models,mode):
    with connect() as c:
        # A repeatable-read snapshot pins a complete committed input set.
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        rows=c.execute('SELECT * FROM events WHERE tenant_id=%s ORDER BY id',(tenant,)).fetchall()
        artifacts={}
        for mid in sorted(set(models)):
            row=c.execute('SELECT artifact FROM model_versions WHERE model_id=%s',(mid,)).fetchone()
            if not row: raise ValueError('missing model')
            artifacts[mid]=validate(row['artifact'],mid)
    events=[event_dict(r) for r in rows]
    manifest={'mode':mode,'events':[{'event_id':r['event_id'],'hash':r['payload_hash'],'received_at':r['received_at'].isoformat()} for r in rows], 'models':sorted(artifacts),'feature_version':FEATURE_VERSION,'tolerance':1e-12,'tenant_id':tenant,'replay_version':2}
    run_id='replay:'+digest(manifest)
    result=compute(events,artifacts,mode)
    with connect() as c:
        inserted=c.execute('INSERT INTO replay_runs(run_id,tenant_id,mode,manifest) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING run_id',(run_id,tenant,mode,Jsonb(manifest))).fetchone()
        if not inserted: return run_id
        for r in result:
            f=r['snapshot']
            c.execute('INSERT INTO feature_snapshots(tenant_id,snapshot_id,content) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(tenant,f['sha256'],Jsonb(f)))
            c.execute('INSERT INTO predictions(tenant_id,event_id,revision,scope,model_id,snapshot_id,output) VALUES (%s,%s,0,%s,%s,%s,%s)',(tenant,r['event_id'],run_id,r['model_id'],f['sha256'],Jsonb(r['output'])))
    return run_id

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tenant',required=True);p.add_argument('--models',nargs='+',required=True);p.add_argument('--mode',choices=['arrival','corrected'],required=True)
    a=p.parse_args();print(run(a.tenant,a.models,a.mode))
