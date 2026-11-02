"""Seeded multi-equipment duplicate/delay workload on disposable PostgreSQL."""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from pathlib import Path
import numpy as np
from app.platform.admin import bootstrap,register,promote
from app.platform.contracts import Event
from app.platform.service import ingest
from app.platform.worker import once
from app.platform.db import connect
from ml.causal import UNITS


def run(output='benchmarks/concurrency.json'):
    if os.environ.get('RISKRADAR_TEST_DATABASE')!='1':raise SystemExit('disposable DB required')
    tenant='concurrency';n=50;equipments=4;latencies=[];lock=threading.Lock();done=threading.Event()
    for i in range(equipments):bootstrap(tenant,f'unit-{i}','original','concurrency-demo-'+'x'*40)
    promote(tenant,register('benchmarks/scientific/model.json'))
    start=time.perf_counter();base=datetime.now(timezone.utc)-timedelta(hours=1)
    def produce(unit):
        rng=np.random.default_rng(7300+unit)
        order=np.concatenate([rng.permutation(np.arange(i,min(i+5,n))) for i in range(0,n,5)])
        for i in order:
            e=Event(event_id=f'{unit}:{i}',equipment_id=f'unit-{unit}',lifecycle_id='original',session_id='boot',sequence=int(i),cycle=int(i),observed_at=(base+timedelta(seconds=int(i)*10)).isoformat(),schema_version=1,values={'temperature':65.+i*.1,'vibration':2.,'pressure':100.,'current':40.,'rpm':1500.},quality={s:'good' for s in UNITS},units=dict(UNITS))
            before=time.perf_counter();ingest(tenant,e);assert ingest(tenant,e)['duplicate']
            with lock:latencies.append(time.perf_counter()-before)
    def consume():
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            worked=once()
            if not worked:
                with connect() as c:
                    left=c.execute("SELECT count(*) AS n FROM jobs WHERE tenant_id=%s AND status!='done'",(tenant,)).fetchone()['n']
                if done.is_set() and left==0:return
                time.sleep(.01)
        raise AssertionError('multi-equipment workload did not drain')
    with ThreadPoolExecutor(6) as pool:
        workers=[pool.submit(consume) for _ in range(2)]
        producers=[pool.submit(produce,i) for i in range(equipments)]
        for f in producers:f.result()
        done.set()
        for f in workers:f.result()
    with connect() as c:
        originals=c.execute("SELECT count(*) AS n FROM predictions WHERE tenant_id=%s AND scope='live' AND output->>'revision_reason'='original'",(tenant,)).fetchone()['n']
        revisions=c.execute("SELECT count(*) AS n FROM predictions WHERE tenant_id=%s AND scope='live' AND revision>0",(tenant,)).fetchone()['n']
        assert originals==n*equipments
        dead=c.execute("SELECT count(*) AS n FROM jobs WHERE tenant_id=%s AND status='dead'",(tenant,)).fetchone()['n'];assert dead==0
        attempts=c.execute('SELECT max(attempts) AS n FROM jobs WHERE tenant_id=%s',(tenant,)).fetchone()['n']
    report={'seed_base':7300,'equipment':equipments,'unique_events':n*equipments,'duplicate_events':n*equipments,'producer_threads':4,'consumer_threads':2,'delay_model':'shuffle each consecutive five-cycle block','original_predictions':originals,'late_revisions':revisions,'dead_jobs':dead,'max_inference_attempts':attempts,'duration_seconds':time.perf_counter()-start,'ingestion_pair_p95_ms':float(np.quantile(latencies,.95)*1000),'limitations':['short bounded contention test','direct service calls, not HTTP latency','not a throughput capacity or soak claim']}
    Path(output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':run()
