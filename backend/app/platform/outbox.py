"""At-least-once notifications; receiver must deduplicate Idempotency-Key.

Only a deployment-configured endpoint is allowed, never an event-supplied URL.
A timeout after receiver success can duplicate delivery; five attempts maximum.
"""
import os
import time
import signal
import httpx
from .db import connect


def deliver_once(send=None):
    with connect() as c:
        row=c.execute("SELECT * FROM outbox WHERE (status='pending' AND available_at<=clock_timestamp()) OR (status='leased' AND lease_until<clock_timestamp()) ORDER BY outbox_id FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
        if not row: return False
        if row['attempts']>=5:
            c.execute("UPDATE outbox SET status='dead' WHERE outbox_id=%s",(row['outbox_id'],));return True
        row=c.execute("UPDATE outbox SET status='leased',attempts=attempts+1,lease_token=lease_token+1,lease_until=clock_timestamp()+interval '30 seconds' WHERE outbox_id=%s RETURNING *",(row['outbox_id'],)).fetchone()
    try:
        key=f"{row['tenant_id']}:{row['dedupe_key']}"
        if send: send(row['payload'],key)
        else:
            response=httpx.post(os.environ['NOTIFICATION_URL'],json=row['payload'],headers={'Idempotency-Key':key},timeout=10,follow_redirects=False)
            response.raise_for_status()
        success=True
    except Exception:
        success=False
    with connect() as c:
        c.execute("UPDATE outbox SET status=%s,lease_until=NULL,available_at=clock_timestamp()+interval '30 seconds' WHERE outbox_id=%s AND lease_token=%s AND status='leased' AND lease_until>clock_timestamp()",('sent' if success else ('dead' if row['attempts']>=5 else 'pending'),row['outbox_id'],row['lease_token']))
    return True

if __name__=='__main__':
    if not os.environ.get('NOTIFICATION_URL'): raise SystemExit('NOTIFICATION_URL required; outbox remains durable without delivery')
    stop=False
    def shutdown(*_):
        global stop
        stop=True
    signal.signal(signal.SIGTERM,shutdown);signal.signal(signal.SIGINT,shutdown)
    while not stop:
        try:
            if not deliver_once():time.sleep(.5)
        except Exception:time.sleep(1)
