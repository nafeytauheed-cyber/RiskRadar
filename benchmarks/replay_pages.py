"""Measure bounded replay pages on a disposable PostgreSQL dataset."""
import json
import os
import time
import tracemalloc
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.platform.admin import bootstrap, register, promote
from app.platform.contracts import Event
from app.platform.db import connect
from app.platform.service import ingest
from app.platform import replay
from ml.causal import UNITS


def run(count=500, page_size=25):
    if os.environ.get('RISKRADAR_TEST_DATABASE') != '1':
        raise SystemExit('disposable database required')
    tenant = 'replay-pages'
    bootstrap(tenant, 'unit', 'original', 'benchmark-replay-'+'x'*40)
    mid = register('benchmarks/scientific/model.json')
    promote(tenant, mid)
    base = datetime.now(timezone.utc)-timedelta(seconds=count+1)
    for i in range(count):
        ingest(tenant, Event(
            event_id=f'page:{i}', equipment_id='unit', lifecycle_id='original',
            session_id='boot', sequence=i, cycle=i,
            observed_at=(base+timedelta(seconds=i)).isoformat(), schema_version=1,
            values={'temperature':65.,'vibration':2.,'pressure':100.,'current':40.,'rpm':1500.},
            units=dict(UNITS), quality={s:'good' for s in UNITS},
        ))
    with connect() as c:
        before = {table:c.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n']
                  for table in ('incidents','outbox')}
    start = time.perf_counter()
    tracemalloc.start()
    rid = replay.create(tenant, [mid], 'arrival')
    maximum_results, pages = 0, 0
    while True:
        job = replay.claim_page(tenant, rid)
        if not job:
            break
        last, results = replay.prepare_page(job, page_size)
        maximum_results = max(maximum_results, len(results))
        assert len(results) <= page_size
        replay.finish_page(job, last, results)
        pages += 1
        if pages == 1:
            replay.control(tenant, rid, 'cancel')
            assert not replay.step(tenant, rid, page_size)
            replay.control(tenant, rid, 'resume')
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    with connect() as c:
        row = c.execute('SELECT status,processed,total FROM replay_runs WHERE run_id=%s',(rid,)).fetchone()
        assert row == {'status':'complete','processed':count,'total':count}
        for table,n in before.items():
            assert c.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n']==n
        assert c.execute('SELECT count(*) AS n FROM predictions WHERE scope=%s',(rid,)).fetchone()['n']==count
        # Fixture telemetry jobs are not live workload for subsequent recovery drills.
        # Process them through the real workers rather than deleting or marking done.
    result = {'events':count,'models':1,'page_size':page_size,'pages':pages,
              'max_page_results':maximum_results,'peak_traced_python_bytes':peak,
              'duration_seconds':time.perf_counter()-start,'cancel_resume_verified':True,
              'live_incidents_outbox_unchanged':True,
              'limitations':['short single-instance workload','tracemalloc excludes native/database memory',
                             'pinning still scans input identities in one database snapshot']}
    Path('benchmarks/replay-pages.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    from app.platform.worker import once
    while once():
        pass


if __name__=='__main__':
    run()
