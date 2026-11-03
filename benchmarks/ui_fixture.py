"""Create only isolated disposable UI demo data for CI."""
import os,time
from datetime import datetime,timezone
from app.platform.admin import bootstrap,register,promote
from app.platform.contracts import Event
from app.platform.service import ingest
from app.platform.worker import once
from app.platform.replay import run
from simulator.generate import generate

if __name__=='__main__':
    if os.environ.get('RISKRADAR_TEST_DATABASE')!='1':raise SystemExit('disposable database required')
    bootstrap('ui-demo','degradation','original',os.environ['RISKRADAR_API_KEY'])
    mid=register('benchmarks/scientific/model.json');promote('ui-demo',mid)
    events,_=generate(cycles=20,start=time.time()-1800)
    for e in events:
        if e['equipment_id']!='degradation':continue
        e.pop('received_at');e['observed_at']=datetime.fromtimestamp(e['observed_at'],timezone.utc).isoformat();ingest('ui-demo',Event(**e))
    while once():pass
    run('ui-demo',[mid],'arrival');run('ui-demo',[mid],'corrected')
