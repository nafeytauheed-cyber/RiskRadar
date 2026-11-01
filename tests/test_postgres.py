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
    run('a',[mid],'corrected');promote('a',mid)
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
