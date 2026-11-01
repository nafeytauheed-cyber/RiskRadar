"""CI-only database stop/restart + backup/restore drill on disposable service."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime,timezone
import psycopg
from app.platform.db import connect
from app.platform.admin import bootstrap,register,promote
from app.platform.contracts import Event
from app.platform.service import ingest,claim,prepare_features,finish_features,prepared_inference,finish
from ml.causal import UNITS


def run(container,output):
    if os.environ.get('RISKRADAR_TEST_DATABASE')!='1':raise SystemExit('disposable DB only')
    tenant='recovery';bootstrap(tenant,'probe','original','recovery-only-'+'x'*40);mid=register('benchmarks/scientific/model.json');promote(tenant,mid)
    event=Event(event_id='before-stop',equipment_id='probe',lifecycle_id='original',session_id='boot',sequence=1,cycle=1,observed_at=datetime.now(timezone.utc).isoformat(),schema_version=1,values={'temperature':65.,'vibration':2.,'pressure':100.,'current':40.,'rpm':1500.},units=dict(UNITS),quality={s:'good' for s in UNITS})
    ingest(tenant,event)
    start=time.perf_counter()
    subprocess.run(['docker','stop',container],check=True,capture_output=True)
    rejected=False
    try:ingest(tenant,event)
    except psycopg.OperationalError:rejected=True
    finally:subprocess.run(['docker','start',container],check=True,capture_output=True)
    deadline=time.monotonic()+30
    while True:
        try:
            with connect() as c:c.execute('SELECT 1')
            break
        except psycopg.OperationalError:
            if time.monotonic()>deadline:raise
            time.sleep(.2)
    assert rejected,'outage was falsely acknowledged'
    job=claim();assert job and job['tenant_id']==tenant
    m,r=prepare_features(job);finish_features(job,m,r)
    job=claim(phase='inference');assert job
    m,r=prepared_inference(job);finish(job,m,r)
    assert ingest(tenant,event)['duplicate']
    dump=subprocess.run(['docker','exec',container,'pg_dump','-U','riskradar','-d','riskradar_test','-Fc'],capture_output=True,check=True).stdout
    subprocess.run(['docker','exec',container,'createdb','-U','riskradar','restore_check'],capture_output=True,check=True)
    subprocess.run(['docker','exec','-i',container,'pg_restore','--no-owner','--exit-on-error','-U','riskradar','-d','restore_check'],input=dump,capture_output=True,check=True)
    original=os.environ['DATABASE_URL'];restored=original.rsplit('/',1)[0]+'/restore_check'
    from psycopg.rows import dict_row
    tables=('events','jobs','predictions','model_versions','outbox','audit_events')
    with connect() as c,psycopg.connect(restored,row_factory=dict_row) as d:
        counts={}
        for table in tables:
            # Fixed internal table names, never caller input.
            n=c.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n'];assert d.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n']==n;counts[table]=n
        hashes=c.execute('SELECT model_id FROM model_versions ORDER BY model_id').fetchall();assert hashes==d.execute('SELECT model_id FROM model_versions ORDER BY model_id').fetchall()
    result={'database_stop_rejected_ingest':rejected,'durable_pending_job_recovered':True,'duplicate_after_restart':True,'restored_table_counts':counts,'model_hashes_preserved':True,'dump_bytes':len(dump),'duration_seconds':time.perf_counter()-start,'limitations':['single PostgreSQL instance on GitHub runner','no replication/failover or network partition drill']}
    Path(output).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--container',required=True);p.add_argument('--output',default='benchmarks/recovery.json');a=p.parse_args();run(a.container,a.output)
