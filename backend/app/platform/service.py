"""Short PostgreSQL transactions with equipment-level fencing.

The lease is an execution permit, not a lock held during inference.
Every effect is committed in one transaction after rechecking its fence.
"""
import hashlib
from datetime import datetime, timezone
from psycopg.types.json import Jsonb
from ml.causal import digest, snapshot
from ml.artifact import score, validate
from .db import connect

class Conflict(Exception): pass
class Overloaded(Exception): pass
class LostLease(Exception): pass


def audit(c,tenant,actor,action,details):
    c.execute('INSERT INTO audit_events(tenant_id,actor,action,details) VALUES (%s,%s,%s,%s)',(tenant,actor,action,Jsonb(details)))


def ingest(tenant,event,limit=10000):
    payload=event.model_dump(); hashed=digest(payload)
    with connect() as c:
        # A tenant queue bound must serialize admissions across equipment.
        c.execute('SELECT tenant_id FROM tenants WHERE tenant_id=%s FOR UPDATE',(tenant,))
        eq=c.execute('SELECT * FROM equipment WHERE tenant_id=%s AND equipment_id=%s FOR UPDATE',(tenant,event.equipment_id)).fetchone()
        if not eq: raise KeyError('equipment')
        existing=c.execute('SELECT payload_hash FROM events WHERE tenant_id=%s AND event_id=%s',(tenant,event.event_id)).fetchone()
        if existing:
            if existing['payload_hash']!=hashed: raise Conflict('event_id has different content')
            return {'event_id':event.event_id,'duplicate':True}
        if eq['lifecycle_id']!=event.lifecycle_id: raise Conflict('inactive lifecycle')
        collision=c.execute('SELECT 1 FROM events WHERE tenant_id=%s AND equipment_id=%s AND lifecycle_id=%s AND session_id=%s AND (sequence=%s OR cycle=%s)',(tenant,event.equipment_id,event.lifecycle_id,event.session_id,event.sequence,event.cycle)).fetchone()
        if collision: raise Conflict('sequence or cycle already assigned')
        pending=c.execute("SELECT count(*) AS n FROM jobs WHERE tenant_id=%s AND status IN ('pending','leased')",(tenant,)).fetchone()['n']
        if pending>=limit: raise Overloaded('queue capacity reached')
        c.execute('INSERT INTO events(tenant_id,event_id,equipment_id,lifecycle_id,session_id,sequence,cycle,observed_at,schema_version,payload,payload_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(tenant,event.event_id,event.equipment_id,event.lifecycle_id,event.session_id,event.sequence,event.cycle,event.observed_at,1,Jsonb(payload),hashed))
        c.execute('INSERT INTO jobs(tenant_id,event_id,equipment_id) VALUES (%s,%s,%s)',(tenant,event.event_id,event.equipment_id))
    return {'event_id':event.event_id,'duplicate':False}


def claim(lease_seconds=30):
    with connect() as c:
        eq=c.execute("""SELECT e.* FROM equipment e WHERE (lease_until IS NULL OR lease_until<clock_timestamp())
          AND EXISTS(SELECT 1 FROM jobs j WHERE j.tenant_id=e.tenant_id AND j.equipment_id=e.equipment_id AND j.status IN ('pending','leased'))
          ORDER BY e.tenant_id,e.equipment_id FOR UPDATE SKIP LOCKED LIMIT 1""").fetchone()
        if not eq: return None
        t,e=eq['tenant_id'],eq['equipment_id']
        # Never skip an earlier retry for this equipment.
        j=c.execute("SELECT *,available_at<=clock_timestamp() AS ready FROM jobs WHERE tenant_id=%s AND equipment_id=%s AND status IN ('pending','leased') ORDER BY job_id LIMIT 1 FOR UPDATE",(t,e)).fetchone()
        if not j['ready']: return None
        if j['attempts']>=5:
            c.execute("UPDATE jobs SET status='dead',error='retry budget exhausted' WHERE job_id=%s",(j['job_id'],))
            audit(c,t,'worker','job.dead',{'job_id':j['job_id']}); return None
        eq=c.execute("UPDATE equipment SET lease_token=lease_token+1,lease_until=clock_timestamp()+(%s * interval '1 second') WHERE tenant_id=%s AND equipment_id=%s RETURNING *",(lease_seconds,t,e)).fetchone()
        return c.execute("UPDATE jobs SET status='leased',attempts=attempts+1,token=%s,lease_until=%s WHERE job_id=%s RETURNING *",(eq['lease_token'],eq['lease_until'],j['job_id'])).fetchone()


def event_dict(row):
    return dict(row['payload'],observed_at=row['observed_at'].timestamp(),received_at=row['received_at'].timestamp())


def prepare(job):
    with connect() as c:
        row=c.execute('SELECT * FROM events WHERE tenant_id=%s AND event_id=%s',(job['tenant_id'],job['event_id'])).fetchone()
        model=c.execute('SELECT m.* FROM tenants t JOIN model_versions m ON m.model_id=t.active_model WHERE t.tenant_id=%s',(job['tenant_id'],)).fetchone()
        if not model: raise ValueError('no promoted model')
        validate(model['artifact'],model['model_id'])
        events=c.execute('SELECT * FROM events WHERE tenant_id=%s AND equipment_id=%s AND received_at<=%s ORDER BY id',(job['tenant_id'],job['equipment_id'],row['received_at'])).fetchall()
        # Late data revises already processed affected targets, without deleting originals.
        targets=c.execute("""SELECT DISTINCT e.* FROM events e JOIN predictions p ON p.tenant_id=e.tenant_id AND p.event_id=e.event_id
          WHERE e.tenant_id=%s AND e.equipment_id=%s AND p.scope='live' AND e.lifecycle_id=%s AND e.session_id=%s
          AND e.cycle>=%s AND e.cycle<%s AND e.observed_at>=%s AND e.received_at<=%s""",
          (job['tenant_id'],job['equipment_id'],row['lifecycle_id'],row['session_id'],row['cycle'],row['cycle']+10,row['observed_at'],row['received_at'])).fetchall()
    byid={r['event_id']:r for r in [row]+targets}
    results=[]
    for target in byid.values():
        f=snapshot([event_dict(r) for r in events],event_dict(target),row['received_at'].timestamp())
        output=score(model['artifact'],f)
        output.update({'quality_state':f['quality_state'],'horizon_cycles':model['artifact']['horizon'],'calibration':model['artifact']['calibration']['version'],'baseline':model['artifact']['baseline'],'policy':'hysteresis-v1','model_id':model['model_id'],'revision_reason':'original' if target['event_id']==row['event_id'] else 'late_observation'})
        results.append((target,f,output))
    return model['model_id'],results


def finish(job,model_id,results):
    with connect() as c:
        eq=c.execute('SELECT *,lease_until>clock_timestamp() AS valid FROM equipment WHERE tenant_id=%s AND equipment_id=%s FOR UPDATE',(job['tenant_id'],job['equipment_id'])).fetchone()
        j=c.execute('SELECT * FROM jobs WHERE job_id=%s FOR UPDATE',(job['job_id'],)).fetchone()
        if j['status']=='done': return False # crash after commit: no duplicate effects
        if eq['lease_token']!=job['token'] or not eq['valid'] or j['token']!=job['token'] or j['status']!='leased': raise LostLease()
        for target,f,output in results:
            tenant=job['tenant_id']; eid=target['event_id']
            c.execute('INSERT INTO feature_snapshots(tenant_id,snapshot_id,content) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(tenant,f['sha256'],Jsonb(f)))
            rev=c.execute("SELECT coalesce(max(revision),-1)+1 AS n FROM predictions WHERE tenant_id=%s AND event_id=%s AND scope='live' AND model_id=%s",(tenant,eid,model_id)).fetchone()['n']
            p=c.execute('INSERT INTO predictions(tenant_id,event_id,revision,model_id,snapshot_id,output) VALUES (%s,%s,%s,%s,%s,%s) RETURNING prediction_id',(tenant,eid,rev,model_id,f['sha256'],Jsonb(output))).fetchone()['prediction_id']
            c.execute('INSERT INTO evidence(evidence_id,tenant_id,prediction_id,content) VALUES (%s,%s,%s,%s)',(f'prediction:{p}',tenant,p,Jsonb({'input_refs':f['input_refs'],'kind':'model_evidence','causal_claim':False})))
            if output['revision_reason']=='original':
                update_incident(c,job,target,output,p)
        c.execute("UPDATE jobs SET status='done',lease_until=NULL WHERE job_id=%s",(job['job_id'],))
        c.execute('UPDATE equipment SET lease_until=NULL WHERE tenant_id=%s AND equipment_id=%s',(job['tenant_id'],job['equipment_id']))
        audit(c,job['tenant_id'],'worker','job.committed',{'job_id':job['job_id'],'model_id':model_id})
    return True


def update_incident(c,job,event,output,prediction_id):
    t,e=job['tenant_id'],job['equipment_id']
    c.execute('INSERT INTO processing_state(tenant_id,equipment_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',(t,e))
    state=c.execute('SELECT * FROM processing_state WHERE tenant_id=%s AND equipment_id=%s FOR UPDATE',(t,e)).fetchone()
    if state['last_observed_at'] and event['observed_at']<=state['last_observed_at']: return
    reset=(state['lifecycle_id'],state['session_id'])!=(event['lifecycle_id'],event['session_id'])
    prob=output['failure_probability']
    high=(0 if reset else state['high_streak'])+1 if prob is not None and prob>=.5 else 0
    low=(0 if reset else state['low_streak'])+1 if prob is not None and prob<.3 else 0
    c.execute('UPDATE processing_state SET latest_event_id=%s,latest_cycle=%s,lifecycle_id=%s,session_id=%s,last_observed_at=%s,high_streak=%s,low_streak=%s,version=version+1 WHERE tenant_id=%s AND equipment_id=%s',(event['event_id'],event['cycle'],event['lifecycle_id'],event['session_id'],event['observed_at'],high,low,t,e))
    active=c.execute("SELECT * FROM incidents WHERE tenant_id=%s AND equipment_id=%s AND status<>'resolved'",(t,e)).fetchone()
    if high>=2 and not active:
        iid=c.execute("INSERT INTO incidents(tenant_id,equipment_id,status,opened_prediction) VALUES (%s,%s,'open',%s) RETURNING incident_id",(t,e,prediction_id)).fetchone()['incident_id']
        c.execute("INSERT INTO incident_transitions(tenant_id,incident_id,to_status,note,actor) VALUES (%s,%s,'open','Two consecutive eligible high predictions','worker')",(t,iid))
        c.execute('INSERT INTO outbox(tenant_id,dedupe_key,payload) VALUES (%s,%s,%s)',(t,f'incident:{iid}:open',Jsonb({'incident_id':iid,'equipment_id':e,'prediction_id':prediction_id})))


def fail(job,error):
    with connect() as c:
        eq=c.execute('SELECT * FROM equipment WHERE tenant_id=%s AND equipment_id=%s FOR UPDATE',(job['tenant_id'],job['equipment_id'])).fetchone()
        if eq['lease_token']!=job['token']: return
        c.execute("UPDATE jobs SET status=CASE WHEN attempts>=5 THEN 'dead' ELSE 'pending' END,error=%s,available_at=clock_timestamp()+(%s * interval '1 second'),lease_until=NULL WHERE job_id=%s AND status='leased' AND token=%s",(type(error).__name__,min(60,2**job['attempts']),job['job_id'],job['token']))
        c.execute('UPDATE equipment SET lease_until=NULL WHERE tenant_id=%s AND equipment_id=%s',(job['tenant_id'],job['equipment_id']))


def transition(tenant,incident_id,version,to_status,note,actor):
    allowed={'open':{'acknowledged'},'acknowledged':{'investigating'},'investigating':{'resolved'},'resolved':set()}
    with connect() as c:
        i=c.execute('SELECT * FROM incidents WHERE tenant_id=%s AND incident_id=%s FOR UPDATE',(tenant,incident_id)).fetchone()
        if not i: raise KeyError('incident')
        if i['version']!=version or to_status not in allowed[i['status']]: raise Conflict('stale version or invalid transition')
        c.execute('UPDATE incidents SET status=%s,version=version+1 WHERE incident_id=%s',(to_status,incident_id))
        c.execute('INSERT INTO incident_transitions(tenant_id,incident_id,from_status,to_status,note,actor) VALUES (%s,%s,%s,%s,%s,%s)',(tenant,incident_id,i['status'],to_status,note,actor))
        audit(c,tenant,actor,'incident.transition',{'incident_id':incident_id,'status':to_status})
    return {'version':version+1,'status':to_status}
