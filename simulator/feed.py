import argparse
import os
import time
from datetime import datetime,timezone
import httpx
from .generate import generate

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://localhost:8000');a=p.parse_args()
    events,_=generate(cycles=20,start=time.time()-1800)
    events=[e for e in events if e['equipment_id']=='degradation']
    headers={'Authorization':'Bearer '+os.environ['RISKRADAR_API_KEY']}
    with httpx.Client(base_url=a.url,headers=headers) as c:
        for e in events:
            e.pop('received_at');e['observed_at']=datetime.fromtimestamp(e['observed_at'],timezone.utc).isoformat()
            r=c.post('/api/events',json=e);r.raise_for_status()
        duplicate=c.post('/api/events',json=events[-1]);duplicate.raise_for_status()
        print({'sent':len(events),'duplicate':duplicate.json()})
