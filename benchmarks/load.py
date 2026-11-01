"""Disposable PostgreSQL load/crash experiment; never run against live data."""
import argparse
import json
import os
import platform
import resource
import time
from datetime import datetime,timezone,timedelta
import numpy as np
from app.platform.admin import bootstrap,register,promote
from app.platform.db import migrate,connect
from app.platform.contracts import Event
from app.platform.service import ingest,claim,prepare,finish
from ml.causal import UNITS


def run(n,output):
    if os.environ.get('RISKRADAR_TEST_DATABASE')!='1':raise SystemExit('disposable database opt-in required')
    migrate();tenant='benchmark-'+str(time.time_ns());bootstrap(tenant,'bench','original','benchmark-'+tenant+'x'*40)
    model=register('benchmarks/scientific/model.json');promote(tenant,model)
    start=time.perf_counter();latencies=[];duplicates=0
    for i in range(n):
        t=time.perf_counter();event=Event(event_id=f'e{i}',equipment_id='bench',lifecycle_id='original',session_id='boot1',sequence=i,cycle=i,observed_at=(datetime.now(timezone.utc)-timedelta(seconds=n-i)).isoformat(),schema_version=1,values={'temperature':65.,'vibration':2.,'pressure':100.,'current':40.,'rpm':1500.},quality={s:'good' for s in UNITS},units=dict(UNITS))
        ingest(tenant,event);duplicates+=int(ingest(tenant,event)['duplicate']);latencies.append(time.perf_counter()-t)
    ingested=time.perf_counter();processed=0
    while True:
        job=claim()
        if job is None:break
        mid,results=prepare(job);finish(job,mid,results)
        assert finish(job,mid,results) is False  # commit/ack ambiguity
        processed+=1
    end=time.perf_counter()
    with connect() as c:
        count=c.execute("SELECT count(*) AS n FROM predictions WHERE tenant_id=%s AND scope='live'",(tenant,)).fetchone()['n']
        assert count==n
    report={'events':n,'duplicate_submissions':duplicates,'processed_jobs_all_tenants':processed,'prediction_count':count,'ingest_seconds':ingested-start,'processing_seconds':end-ingested,'total_seconds':end-start,'ingestion_pair_p50_ms':float(np.quantile(latencies,.5)*1000),'ingestion_pair_p95_ms':float(np.quantile(latencies,.95)*1000),'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'python':platform.python_version(),'platform':platform.platform(),'cpu_count':os.cpu_count(),'workload':'one equipment, sequential synchronous producer/worker, duplicate every event; finish replay after every commit','limitations':['not a capacity claim','no network partition experiment','no sustained soak or multi-host scaling']}
    from pathlib import Path
    Path(output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--events',type=int,default=200);p.add_argument('--output',default='benchmarks/postgres-load.json');a=p.parse_args();run(a.events,a.output)
