import argparse
import json
import logging
import signal
import time
from .service import claim, prepare_features, finish_features, prepared_inference, finish, fail, LostLease

log=logging.getLogger('riskradar.worker')


def once(phase=None):
    job=claim(phase=phase)
    if not job: return False
    try:
        if job['phase']=='features':
            model,results=prepare_features(job)
            finish_features(job,model,results)
        else:
            model,results=prepared_inference(job)
            finish(job,model,results)
        log.info(json.dumps({'event':'job_done','job_id':job['job_id']}))
    except LostLease:
        log.warning(json.dumps({'event':'lease_lost','job_id':job['job_id']}))
    except Exception as exc:
        fail(job,exc)
        log.error(json.dumps({'event':'job_failed','job_id':job['job_id'],'error':type(exc).__name__}))
    return True


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['features','inference'])
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    while not stopping:
        try:
            if not once(args.phase): time.sleep(.5)
        except Exception as exc:
            log.error(json.dumps({'event':'worker_unavailable','error':type(exc).__name__})); time.sleep(1)

if __name__=='__main__': main()
