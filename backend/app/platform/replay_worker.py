"""Optional small replay consumer; live inference has separate worker capacity."""
import logging
import signal
import time
from .db import connect
from .replay import step


def once():
    with connect() as c:
        row=c.execute("SELECT tenant_id,run_id FROM replay_runs WHERE status='ready' OR (status='running' AND lease_until<clock_timestamp()) ORDER BY created_at,run_id LIMIT 1").fetchone()
    if not row:
        return False
    return step(row['tenant_id'],row['run_id'])


def main():
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    while not stopping:
        try:
            if not once():time.sleep(.5)
        except Exception as exc:
            logging.getLogger('riskradar.replay').error('replay worker failed: %s',type(exc).__name__)
            time.sleep(1)

if __name__=='__main__':main()
