"""Real PostgreSQL only. Never replace these with SQLite/mocked locks."""
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import pytest
from fastapi.testclient import TestClient
from app.platform.db import connect,migrate
from app.platform.admin import bootstrap,register,promote
from app.platform.contracts import Event
from app.platform.service import ingest,claim,prepare,finish,Conflict,LostLease,Overloaded,transition
from app.platform.replay import run
from app.platform.outbox import deliver_once
from app.main import app
from simulator.generate import generate

pytestmark=pytest.mark.postgres

@pytest.fixture(autouse=True)
def database():
    if not os.environ.get('DATABASE_URL'):pytest.skip('DATABASE_URL required for real PostgreSQL')
    if os.environ.get('RISKRADAR_TEST_DATABASE')!='1':pytest.fail('Set RISKRADAR_TEST_DATABASE=1 for disposable database')
    migrate()
    with connect() as c:c.execute('TRUNCATE tenants,model_versions CASCADE')
    bootstrap('a','degradation','original','a'*40);bootstrap('b','degradation','original','b'*40)
    mid=register('benchmarks/scientific/model.json');promote('a',mid);promote('b',mid)
    yield


def event(i=1):
    e=[e for e in generate(cycles=20,start=datetime.now(timezone.utc).timestamp()-3600)[0] if e['equipment_id']=='degradation'][i-1]
    e.pop('received_at');e['observed_at']=datetime.fromtimestamp(e['observed_at'],timezone.utc).isoformat()
    return Event(**e)


def test_duplicate_conflict_atomicity_and_capacity():
    e=event();assert not ingest('a',e)['duplicate'];assert ingest('a',e)['duplicate']
    e.values['temperature']+=1
    with pytest.raises(Conflict):ingest('a',e)
    with pytest.raises(Overloaded):ingest('a',event(2),limit=1)
    with connect() as c:
        assert c.execute('SELECT count(*) AS n FROM events').fetchone()['n']==1
        assert c.execute('SELECT count(*) AS n FROM jobs').fetchone()['n']==1


def test_concurrent_ingestion():
    e=event()
    with ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:ingest('a',e),range(8)))
    assert sum(not r['duplicate'] for r in results)==1


def test_stale_lease_crash_recovery_and_idempotent_commit():
    ingest('a',event());j=claim();old_model,old_result=prepare(j)
    with connect() as c:c.execute("UPDATE equipment SET lease_until=now()-interval '1 second'")
    fresh=claim();assert fresh['token']>j['token']
    with pytest.raises(LostLease):finish(j,old_model,old_result)
    mid,r=prepare(fresh);assert finish(fresh,mid,r)
    assert not finish(fresh,mid,r)  # commit succeeded, process died before returning
    assert claim() is None
    with connect() as c:assert c.execute('SELECT count(*) AS n FROM predictions').fetchone()['n']==1


def test_equipment_serialization():
    ingest('a',event());ingest('a',event(2))
    with ThreadPoolExecutor(2) as pool:jobs=list(pool.map(lambda _:claim(),range(2)))
    assert sum(j is not None for j in jobs)==1


def test_tenant_isolation_and_api_validation():
    ingest('a',event())
    with TestClient(app) as client:
        assert client.get('/api/equipment').status_code==401
        assert client.post('/api/events',headers={'Authorization':'Bearer '+'a'*40},content=b'x'*17000).status_code==413
        r=client.get('/api/equipment/degradation',headers={'Authorization':'Bearer '+'b'*40})
        assert r.status_code==200 and r.json()['predictions']==[]
        assert client.get('/api/metrics',headers={'Authorization':'Bearer '+'b'*40}).json()['jobs']==[]


def test_late_revisions_replay_and_rollback():
    for i in (1,2,3,4,6,7,8):
        ingest('a',event(i));j=claim();mid,r=prepare(j);finish(j,mid,r)
    ingest('a',event(5));j=claim();mid,r=prepare(j);finish(j,mid,r)
    with connect() as c:
        assert c.execute('SELECT count(*) AS n FROM predictions WHERE revision>0').fetchone()['n']>=1
        before=c.execute('SELECT count(*) AS n FROM incidents').fetchone()['n']
        notifications=c.execute('SELECT count(*) AS n FROM outbox').fetchone()['n']
    rid=run('a',[mid],'arrival');assert run('a',[mid],'arrival')==rid
    run('a',[mid],'corrected')
    import copy
    from ml.artifact import load
    from ml.causal import digest
    from psycopg.types.json import Jsonb
    challenger=copy.deepcopy(load('benchmarks/scientific/model.json'));challenger['intercept']+=.1
    other=digest(challenger)
    with connect() as c:c.execute('INSERT INTO model_versions(model_id,artifact) VALUES (%s,%s)',(other,Jsonb(challenger)))
    promote('a',other);promote('a',mid)
    with pytest.raises(ValueError):promote('a','invalid')
    with connect() as c:
        assert c.execute('SELECT count(*) AS n FROM incidents').fetchone()['n']==before
        assert c.execute('SELECT count(*) AS n FROM outbox').fetchone()['n']==notifications
        assert c.execute("SELECT active_model FROM tenants WHERE tenant_id='a'").fetchone()['active_model']==mid


def test_incident_transition_outbox():
    # Inject eligible model outputs at the inference seam, not into transaction logic.
    for i in (1,2):
        ingest('a',event(i));j=claim();mid,r=prepare(j)
        for _,_,o in r:o['failure_probability']=.9
        finish(j,mid,r)
    with connect() as c:
        incident=c.execute('SELECT * FROM incidents').fetchone()
        assert c.execute('SELECT count(*) AS n FROM outbox').fetchone()['n']==1
    with pytest.raises(Conflict):transition('a',incident['incident_id'],9,'acknowledged','inspect','test')
    transition('a',incident['incident_id'],1,'acknowledged','inspect','test')
    transition('a',incident['incident_id'],2,'investigating','checked bearing','test')
    transition('a',incident['incident_id'],3,'resolved','inspection completed','test')
    sent=[];assert deliver_once(lambda payload,key:sent.append(key));assert not deliver_once(lambda *_:None)
    assert len(sent)==1


def test_maintenance_boundary_and_immutable_history():
    import psycopg
    from app.platform.service import record_outcome
    ingest('a',event());job=claim();mid,r=prepare(job);finish(job,mid,r)
    record_outcome('a','degradation','original',20,'maintenance','bearing replaced','repaired','operator')
    with pytest.raises(Conflict):ingest('a',event(2))
    fresh=event(2);fresh.lifecycle_id='repaired';ingest('a',fresh)
    job=claim();mid,r=prepare(job);assert r[0][1]['quality_state']=='warmup';finish(job,mid,r)
    with pytest.raises(psycopg.Error):
        with connect() as c:c.execute('DELETE FROM events')
    with pytest.raises(psycopg.Error):
        with connect() as c:c.execute('UPDATE model_versions SET artifact=\'{}\'::jsonb')


def test_retries_dead_letter_and_clock_order():
    from app.platform.service import fail
    e=event(2);ingest('a',e)
    earlier=event(1);earlier.observed_at=e.observed_at.replace('+00:00','+00:00')
    earlier.sequence=3
    with pytest.raises(Conflict):ingest('a',earlier)
    for _ in range(5):
        j=claim();assert j
        fail(j,RuntimeError('model unavailable'))
        with connect() as c:c.execute('UPDATE jobs SET available_at=now()')
    assert claim() is None
    with connect() as c:assert c.execute('SELECT status FROM jobs').fetchone()['status']=='dead'


def test_worker_process_death_and_restart():
    import subprocess,sys,json
    ingest('a',event())
    script="from app.platform.service import claim; import json,os; print(json.dumps(claim(),default=str),flush=True); os._exit(17)"
    child=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True)
    assert child.returncode==17
    lost=json.loads(child.stdout)
    with connect() as c:c.execute("UPDATE equipment SET lease_until=now()-interval '1 second'")
    replacement=claim();assert replacement['token']>lost['token']
    mid,r=prepare(replacement);finish(replacement,mid,r)
    with connect() as c:assert c.execute('SELECT status FROM jobs').fetchone()['status']=='done'


def test_database_outage_never_acknowledged(monkeypatch):
    # A real refused PostgreSQL connection, not a mock successful transaction.
    monkeypatch.setenv('DATABASE_URL','postgresql://localhost:1/unavailable?connect_timeout=1')
    with TestClient(app,raise_server_exceptions=False) as client:
        response=client.post('/api/events',json=event().model_dump(),headers={'Authorization':'Bearer '+'a'*40})
        assert response.status_code==503


def test_outbox_ambiguous_delivery_retries_same_key():
    from psycopg.types.json import Jsonb
    with connect() as c:c.execute("INSERT INTO outbox(tenant_id,dedupe_key,payload) VALUES ('a','test',%s)",(Jsonb({'id':1}),))
    received=[]
    def ambiguous(payload,key):
        received.append(key)
        raise TimeoutError('receiver succeeded but acknowledgment was lost')
    deliver_once(ambiguous)
    with connect() as c:c.execute('UPDATE outbox SET available_at=now()')
    deliver_once(lambda payload,key:received.append(key))
    assert len(received)==2 and len(set(received))==1
    with connect() as c:assert c.execute('SELECT status FROM outbox').fetchone()['status']=='sent'


def test_durable_feature_inference_stages_and_pinned_model():
    from app.platform.service import prepare_features,finish_features,prepared_inference
    ingest('a',event());ingest('a',event(2))
    assert claim(phase='inference') is None
    j=claim(phase='features');model,features=prepare_features(j)
    assert finish_features(j,model,features)
    assert not finish_features(j,model,features)
    assert claim(phase='features') is None # cannot overtake earlier inference
    j2=claim(phase='inference');assert j2['prepared']['model_id']==model
    m,r=prepared_inference(j2);assert m==model;finish(j2,m,r)
    assert claim(phase='features') is not None


def test_worker_entrypoint_both_stages():
    from app.platform.worker import once
    ingest('a',event())
    assert once('features');assert once('inference');assert not once()
    with connect() as c:assert c.execute('SELECT status FROM jobs').fetchone()['status']=='done'


def test_http_ingestion_and_device_scope():
    with connect() as c:
        c.execute("INSERT INTO api_keys(key_hash,tenant_id,role,equipment_id) VALUES (%s,'a','device','degradation')",(hashlib.sha256(b'device-key-for-test').hexdigest(),))
    with TestClient(app) as client:
        headers={'Authorization':'Bearer device-key-for-test'}
        e=event().model_dump()
        assert client.post('/api/events',json=e,headers=headers).status_code==202
        assert client.post('/api/events',json=e,headers=headers).json()['duplicate']
        e['equipment_id']='not-owned'
        assert client.post('/api/events',json=e,headers=headers).status_code==403
        assert client.get('/api/equipment',headers=headers).status_code==403


def test_prepared_feature_tampering_rejected():
    from app.platform.service import prepare_features,finish_features,prepared_inference
    ingest('a',event());j=claim();mid,r=prepare_features(j);finish_features(j,mid,r)
    inference=claim(phase='inference')
    inference['prepared']['results'][0][1]['features'][0]+=1
    with pytest.raises(ValueError,match='integrity'):prepared_inference(inference)


def test_concurrent_admission_and_two_stage_processing():
    import time
    from app.platform.worker import once
    data=[event(i) for i in range(1,21)]
    def produce():
        for e in data:ingest('a',e)
    def consume():
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            once()
            with connect() as c:
                count=c.execute("SELECT count(*) AS n FROM jobs WHERE status='done'").fetchone()['n']
            if count==20:return
            time.sleep(.01)
        raise AssertionError('concurrent processing failed to drain')
    with ThreadPoolExecutor(3) as pool:
        futures=[pool.submit(produce),pool.submit(consume),pool.submit(consume)]
        for future in futures:future.result()
    with connect() as c:
        assert c.execute("SELECT count(*) AS n FROM predictions WHERE scope='live'").fetchone()['n']==20
        assert c.execute('SELECT max(attempts) AS n FROM jobs').fetchone()['n']==1


def test_late_revision_keeps_original_model_after_promotion():
    import copy
    from ml.artifact import load
    from ml.causal import digest
    from psycopg.types.json import Jsonb
    for i in (1,2,3,4,6,7):
        ingest('a',event(i));j=claim();original,r=prepare(j);finish(j,original,r)
    a=copy.deepcopy(load('benchmarks/scientific/model.json'));a['intercept']+=.2;new=digest(a)
    with connect() as c:c.execute('INSERT INTO model_versions(model_id,artifact) VALUES (%s,%s)',(new,Jsonb(a)))
    promote('a',new)
    ingest('a',event(5));j=claim();active,r=prepare(j);assert active==new;finish(j,active,r)
    with connect() as c:
        revisions=c.execute('SELECT model_id FROM predictions WHERE revision>0').fetchall()
        assert revisions and all(x['model_id']==original for x in revisions)


def test_reopening_requires_two_new_high_observations():
    def high(i):
        ingest('a',event(i));j=claim();mid,r=prepare(j)
        for _,_,o in r:o['failure_probability']=.9
        finish(j,mid,r)
    high(1);high(2)
    with connect() as c:iid=c.execute('SELECT incident_id FROM incidents').fetchone()['incident_id']
    transition('a',iid,1,'acknowledged','ack','operator')
    transition('a',iid,2,'investigating','inspect','operator')
    transition('a',iid,3,'resolved','fixed','operator')
    high(3)
    with connect() as c:assert c.execute('SELECT count(*) AS n FROM incidents').fetchone()['n']==1
    high(4)
    with connect() as c:assert c.execute('SELECT count(*) AS n FROM incidents').fetchone()['n']==2


@pytest.mark.parametrize('mode',['arrival','corrected'])
def test_paged_replay_matches_reference_and_pins_membership(mode):
    from app.platform import replay
    from app.platform.service import event_dict
    for i in (1,2,3,4,6,7,8,9,10,5):ingest('a',event(i))
    with connect() as c:
        rows=c.execute("SELECT * FROM events WHERE tenant_id='a' ORDER BY id").fetchall()
        model=c.execute("SELECT m.* FROM model_versions m JOIN tenants t ON t.active_model=m.model_id WHERE t.tenant_id='a'").fetchone()
    mid=model['model_id']
    expected=replay.compute([event_dict(r) for r in rows],{mid:model['artifact']},mode)
    rid=replay.create('a',[mid],mode)
    assert replay.create('a',[mid],mode)==rid
    claimed=replay.claim_page('a',rid)
    last,results=replay.prepare_page(claimed,2)
    assert last==2 and len(results)==2
    assert replay.finish_page(claimed,last,results)
    assert not replay.finish_page(claimed,last,results)
    ingest('a',event(11))  # arrives after pinning; never enters this replay
    while replay.step('a',rid,3):pass
    with connect() as c:
        progress=c.execute('SELECT * FROM replay_runs WHERE run_id=%s',(rid,)).fetchone()
        actual=c.execute('SELECT p.event_id,p.model_id,p.output,f.content FROM predictions p JOIN feature_snapshots f USING(tenant_id,snapshot_id) WHERE p.scope=%s',(rid,)).fetchall()
        assert progress['status']=='complete' and progress['processed']==progress['total']==10
        assert c.execute('SELECT count(*) AS n FROM incidents').fetchone()['n']==0
        assert c.execute('SELECT count(*) AS n FROM outbox').fetchone()['n']==0
    wanted={(r['event_id'],r['model_id']):(r['snapshot'],r['output']) for r in expected}
    assert {(r['event_id'],r['model_id']):(r['content'],r['output']) for r in actual}==wanted


def test_replay_cancel_resume_stale_fence():
    from app.platform import replay
    ingest('a',event())
    with connect() as c:mid=c.execute("SELECT active_model FROM tenants WHERE tenant_id='a'").fetchone()['active_model']
    rid=replay.create('a',[mid],'arrival')
    old=replay.claim_page('a',rid);last,results=replay.prepare_page(old,1)
    assert replay.claim_page('a',rid) is None
    assert replay.control('a',rid,'cancel')=='cancelled'
    with pytest.raises(LostLease):replay.finish_page(old,last,results)
    assert not replay.step('a',rid)
    with pytest.raises(KeyError):replay.control('b',rid,'resume')
    replay.control('a',rid,'resume');old=replay.claim_page('a',rid)
    with connect() as c:c.execute("UPDATE replay_runs SET lease_until=now()-interval '1 second' WHERE run_id=%s",(rid,))
    new=replay.claim_page('a',rid)
    with pytest.raises(LostLease):replay.finish_page(old,last,results)
    last,results=replay.prepare_page(new,1);replay.finish_page(new,last,results)
    assert not replay.step('a',rid)


def test_replay_runtime_drift_fails_closed(monkeypatch):
    from app.platform import replay
    ingest('a',event())
    with connect() as c:mid=c.execute("SELECT active_model FROM tenants WHERE tenant_id='a'").fetchone()['active_model']
    rid=replay.create('a',[mid],'arrival')
    monkeypatch.setattr(replay,'descriptors',lambda _: {})
    with pytest.raises(ValueError,match='fingerprint'):replay.step('a',rid)
    with connect() as c:
        assert c.execute('SELECT status FROM replay_runs WHERE run_id=%s',(rid,)).fetchone()['status']=='failed'
        assert c.execute('SELECT count(*) AS n FROM predictions WHERE scope=%s',(rid,)).fetchone()['n']==0
    monkeypatch.undo();replay.control('a',rid,'resume');assert replay.step('a',rid)


def test_replay_api_pagination_and_authorization():
    from app.platform import replay
    for i in range(1,5):ingest('a',event(i))
    with connect() as c:
        mid=c.execute("SELECT active_model FROM tenants WHERE tenant_id='a'").fetchone()['active_model']
        c.execute("INSERT INTO api_keys(key_hash,tenant_id,role) VALUES (%s,'a','reader')",(hashlib.sha256(b'reader-token').hexdigest(),))
    admin={'Authorization':'Bearer '+'a'*40}
    with TestClient(app) as client:
        rid=client.post('/api/replays',json={'models':[mid],'mode':'arrival'},headers=admin).json()['run_id']
        assert client.get('/api/replays/'+rid,headers={'Authorization':'Bearer '+'b'*40}).status_code==404
        assert client.post('/api/replays/'+rid+'/cancel',json={},headers={'Authorization':'Bearer reader-token'}).status_code==403
        while replay.step('a',rid,1):pass
        page=client.get('/api/replays/'+rid+'?limit=2',headers=admin).json()
        assert len(page['predictions'])==2 and page['next_after'] is not None
        next_page=client.get('/api/replays/'+rid+f"?limit=2&after={page['next_after']}",headers=admin).json()
        assert len(next_page['predictions'])==2 and next_page['next_after'] is None
        assert not {r['prediction_id'] for r in page['predictions']} & {r['prediction_id'] for r in next_page['predictions']}
        assert client.get('/api/replays/'+rid+'?limit=501',headers=admin).status_code==422


def test_historical_model_replay_and_promotion_guard():
    from ml.artifact import load
    from ml.causal import digest
    from psycopg.types.json import Jsonb
    from app.platform import replay
    a=load('benchmarks/scientific/model.json');a['feature_version']='causal-v1';old=digest(a)
    with connect() as c:
        c.execute('INSERT INTO model_versions(model_id,artifact) VALUES (%s,%s)',(old,Jsonb(a)))
        current=c.execute("SELECT active_model FROM tenants WHERE tenant_id='a'").fetchone()['active_model']
    with pytest.raises(ValueError,match='historical-only'):promote('a',old)
    for i in range(1,7):ingest('a',event(i))
    rid=replay.run('a',[old,current],'corrected',page_size=2)
    with connect() as c:
        rows=c.execute('SELECT f.content FROM predictions p JOIN feature_snapshots f USING(tenant_id,snapshot_id) WHERE p.scope=%s',(rid,)).fetchall()
    assert len(rows)==12
    assert {r['content']['feature_version'] for r in rows}=={'causal-v1','causal-v2'}
