import json
import logging
import signal
import time
from .service import claim, prepare, finish, fail, LostLease

log=logging.getLogger('riskradar.worker')


def once():
    job=claim()
    if not job: return False
    try:
        model,results=prepare(job)
        finish(job,model,results)
        log.info(json.dumps({'event':'job_done','job_id':job['job_id']}))
    except LostLease:
        log.warning(json.dumps({'event':'lease_lost','job_id':job['job_id']}))
    except Exception as exc:
        fail(job,exc)
        log.error(json.dumps({'event':'job_failed','job_id':job['job_id'],'error':type(exc).__name__}))
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    while not stopping:
        try:
            if not once(): time.sleep(.5)
        except Exception as exc:
            log.error(json.dumps({'event':'worker_unavailable','error':type(exc).__name__})); time.sleep(1)

if __name__=='__main__': main()
