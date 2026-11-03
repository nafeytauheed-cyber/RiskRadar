"""Bounded, resumable replay over an immutable database input membership.

Pinning uses one repeatable-read transaction, streaming identities rather than
materializing payloads. Inference runs outside transactions. Each page is a
fenced atomic commit and never calls live incident/notification code.
"""
import argparse
import hashlib
import json

from psycopg.types.json import Jsonb
from psycopg.errors import SerializationFailure

from ml.artifact import score, validate
from ml.causal import digest
from ml.runtimes import descriptors, resolve
from .db import connect
from .service import LostLease, audit, event_dict

MAX_PAGE = 500
MAX_MODELS = 8


def scored(target, context, artifacts, mode, cutoff):
    results = []
    for model_id, artifact in sorted(artifacts.items()):
        validate(artifact, model_id)
        runtime = resolve(artifact['feature_version'])
        features = runtime.snapshot(
            context, target, cutoff, freshness_cutoff=target['received_at'],
        )
        output = dict(
            score(artifact, features), quality_state=features['quality_state'],
            horizon_cycles=artifact['horizon'],
            calibration=artifact['calibration']['version'],
            baseline=artifact['baseline'], policy='hysteresis-v1', mode=mode,
            runtime_sha256=runtime.fingerprint,
        )
        results.append({'event_id': target['event_id'], 'model_id': model_id,
                        'snapshot': features, 'output': output})
    return results


def compute(events, artifacts, mode):
    """Small pure reference implementation used to verify the paged runner."""
    if mode not in ('arrival', 'corrected'):
        raise ValueError('invalid replay mode')
    if not events:
        return []
    key = (lambda e: (e['received_at'], e.get('arrival_order', 0), e['event_id'])) if mode == 'arrival' else (
        lambda e: (e['observed_at'], e['equipment_id'], e['session_id'], e['sequence'], e['event_id']))
    end = max(e['received_at'] for e in events)
    return [result for target in sorted(events, key=key)
            for result in scored(target, events, artifacts, mode,
                                 target['received_at'] if mode == 'arrival' else end)]


def _artifacts(c, models):
    if not models or len(models) > MAX_MODELS or len(set(models)) != len(models):
        raise ValueError('provide 1-8 distinct model IDs')
    artifacts = {}
    for mid in sorted(models):
        row = c.execute('SELECT artifact FROM model_versions WHERE model_id=%s', (mid,)).fetchone()
        if not row:
            raise ValueError('missing model')
        artifacts[mid] = validate(row['artifact'], mid)
    return artifacts


def create(tenant, models, mode, actor='replay-cli'):
    for attempt in range(3):
        try:
            return _create(tenant, models, mode, actor)
        except SerializationFailure:
            if attempt == 2:
                raise


def _create(tenant, models, mode, actor):
    if mode not in ('arrival', 'corrected'):
        raise ValueError('invalid replay mode')
    with connect() as c:
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        if not c.execute('SELECT 1 FROM tenants WHERE tenant_id=%s', (tenant,)).fetchone():
            raise KeyError('tenant')
        artifacts = _artifacts(c, models)
        identity_hash = hashlib.sha256()
        count, arrival_end = 0, None
        with c.cursor(name='replay_identity_stream') as cursor:
            cursor.itersize = 500
            cursor.execute('SELECT id,event_id,payload_hash,received_at FROM events WHERE tenant_id=%s ORDER BY id', (tenant,))
            for row in cursor:
                identity = [row['id'], row['event_id'], row['payload_hash'], row['received_at'].isoformat()]
                identity_hash.update(json.dumps(identity, separators=(',', ':')).encode() + b'\n')
                count += 1
                timestamp = row['received_at'].timestamp()
                arrival_end = timestamp if arrival_end is None else max(arrival_end, timestamp)
        manifest = {
            'mode': mode, 'input_sha256': identity_hash.hexdigest(), 'input_count': count,
            'identity_encoding': 'json-array-lines:id,event_id,payload_hash,received_at;order=id',
            'arrival_end': arrival_end, 'models': sorted(artifacts),
            'runtimes': descriptors(artifacts), 'tolerance': 1e-12,
            'tenant_id': tenant, 'replay_version': 3,
        }
        run_id = 'replay:' + digest(manifest)
        inserted = c.execute(
            'INSERT INTO replay_runs(run_id,tenant_id,mode,manifest,status,total) VALUES (%s,%s,%s,%s,%s,%s) '
            'ON CONFLICT DO NOTHING RETURNING run_id',
            (run_id, tenant, mode, Jsonb(manifest), 'ready' if count else 'complete', count),
        ).fetchone()
        if not inserted:
            return run_id
        order = 'received_at,id,event_id' if mode == 'arrival' else 'observed_at,equipment_id,session_id,sequence,event_id'
        # The ORDER BY is chosen from two fixed internal strings, never caller SQL.
        c.execute(
            f'INSERT INTO replay_inputs(tenant_id,run_id,ordinal,event_id) '
            f'SELECT tenant_id,%s,row_number() OVER(ORDER BY {order}),event_id '
            'FROM events WHERE tenant_id=%s', (run_id, tenant),
        )
        audit(c, tenant, actor, 'replay.created', {'run_id': run_id, 'input_count': count})
    return run_id


def claim_page(tenant, run_id, lease_seconds=60):
    with connect() as c:
        row = c.execute(
            'SELECT *,lease_until>clock_timestamp() AS lease_valid FROM replay_runs '
            'WHERE tenant_id=%s AND run_id=%s FOR UPDATE', (tenant, run_id),
        ).fetchone()
        if not row:
            raise KeyError('replay')
        if row['status'] not in ('ready', 'running') or row['lease_valid']:
            return None
        return c.execute(
            "UPDATE replay_runs SET status='running',lease_token=lease_token+1,"
            "lease_until=clock_timestamp()+(%s * interval '1 second') WHERE run_id=%s RETURNING *",
            (lease_seconds, run_id),
        ).fetchone()


def prepare_page(claim, page_size=100):
    if not 1 <= page_size <= MAX_PAGE:
        raise ValueError('page_size must be between 1 and 500')
    manifest = claim['manifest']
    if manifest.get('replay_version') != 3:
        raise ValueError('legacy completed replay is read-only')
    tenant, run_id = claim['tenant_id'], claim['run_id']
    with connect() as c:
        artifacts = _artifacts(c, manifest['models'])
        if descriptors(artifacts) != manifest['runtimes']:
            raise ValueError('pinned runtime fingerprint changed')
        targets = c.execute(
            'SELECT e.*,i.ordinal FROM replay_inputs i JOIN events e USING(tenant_id,event_id) '
            'WHERE i.tenant_id=%s AND i.run_id=%s AND i.ordinal>%s ORDER BY i.ordinal LIMIT %s',
            (tenant, run_id, claim['processed'], page_size),
        ).fetchall()
        window = max(resolve(a['feature_version']).window for a in artifacts.values())
        pages = []
        for target in targets:
            cutoff = target['received_at'].timestamp() if claim['mode'] == 'arrival' else manifest['arrival_end']
            context = c.execute(
                'SELECT e.* FROM events e JOIN replay_inputs i USING(tenant_id,event_id) '
                'WHERE i.tenant_id=%s AND i.run_id=%s AND e.equipment_id=%s '
                'AND e.lifecycle_id=%s AND e.session_id=%s AND e.cycle>%s AND e.cycle<=%s '
                'AND e.received_at<=to_timestamp(%s) ORDER BY e.cycle',
                (tenant, run_id, target['equipment_id'], target['lifecycle_id'], target['session_id'],
                 target['cycle']-window, target['cycle'], cutoff),
            ).fetchall()
            pages.append((event_dict(target), [event_dict(e) for e in context], cutoff))
    # All scoring happens after the read transaction has closed.
    results = [r for target, context, cutoff in pages
               for r in scored(target, context, artifacts, claim['mode'], cutoff)]
    return (targets[-1]['ordinal'] if targets else claim['processed']), results


def finish_page(claim, last_ordinal, results):
    with connect() as c:
        current = c.execute(
            'SELECT *,lease_until>clock_timestamp() AS lease_valid FROM replay_runs '
            'WHERE tenant_id=%s AND run_id=%s FOR UPDATE',
            (claim['tenant_id'], claim['run_id']),
        ).fetchone()
        if current['processed'] >= last_ordinal and last_ordinal > claim['processed']:
            return False  # Prior commit succeeded; acknowledgment was lost.
        if (current['status'] != 'running' or not current['lease_valid']
                or current['lease_token'] != claim['lease_token']
                or current['processed'] != claim['processed']):
            raise LostLease('replay page lease lost or cancelled')
        expected = (last_ordinal-claim['processed']) * len(claim['manifest']['models'])
        if last_ordinal > current['total'] or expected <= 0 or len(results) != expected:
            raise ValueError('invalid replay page boundary')
        for result in results:
            features = result['snapshot']
            c.execute(
                'INSERT INTO feature_snapshots(tenant_id,snapshot_id,content) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                (claim['tenant_id'], features['sha256'], Jsonb(features)),
            )
            c.execute(
                'INSERT INTO predictions(tenant_id,event_id,revision,scope,model_id,snapshot_id,output) '
                'VALUES (%s,%s,0,%s,%s,%s,%s)',
                (claim['tenant_id'], result['event_id'], claim['run_id'], result['model_id'],
                 features['sha256'], Jsonb(result['output'])),
            )
        c.execute(
            'UPDATE replay_runs SET processed=%s,status=%s,lease_until=NULL,error=NULL WHERE run_id=%s',
            (last_ordinal, 'complete' if last_ordinal == current['total'] else 'ready', claim['run_id']),
        )
    return True


def step(tenant, run_id, page_size=100):
    if not 1 <= page_size <= MAX_PAGE:
        raise ValueError('page_size must be between 1 and 500')
    claimed = claim_page(tenant, run_id)
    if not claimed:
        return False
    try:
        last, results = prepare_page(claimed, page_size)
        return finish_page(claimed, last, results)
    except LostLease:
        return False
    except Exception as exc:
        with connect() as c:
            c.execute(
                "UPDATE replay_runs SET status='failed',error=%s,lease_until=NULL "
                "WHERE run_id=%s AND lease_token=%s AND status='running'",
                (type(exc).__name__, run_id, claimed['lease_token']),
            )
        raise


def control(tenant, run_id, action, actor='replay-cli'):
    if action not in ('cancel', 'resume'):
        raise ValueError('invalid replay action')
    with connect() as c:
        row = c.execute(
            'SELECT * FROM replay_runs WHERE tenant_id=%s AND run_id=%s FOR UPDATE', (tenant, run_id),
        ).fetchone()
        if not row:
            raise KeyError('replay')
        if row['status'] == 'complete':
            return row['status']
        status = 'cancelled' if action == 'cancel' else 'ready'
        if action == 'resume' and row['status'] not in ('failed', 'cancelled'):
            return row['status']
        c.execute(
            'UPDATE replay_runs SET status=%s,lease_token=lease_token+1,lease_until=NULL,error=NULL WHERE run_id=%s',
            (status, run_id),
        )
        audit(c, tenant, actor, 'replay.'+action, {'run_id': run_id, 'processed': row['processed']})
    return status


def run(tenant, models, mode, page_size=100):
    run_id = create(tenant, models, mode)
    while step(tenant, run_id, page_size):
        pass
    return run_id


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tenant', required=True)
    parser.add_argument('--models', nargs='+')
    parser.add_argument('--mode', choices=['arrival', 'corrected'])
    parser.add_argument('--run-id')
    parser.add_argument('--action', choices=['cancel', 'resume', 'process'], default='process')
    parser.add_argument('--page-size', type=int, default=100)
    args = parser.parse_args()
    if args.run_id:
        if args.action != 'process':
            print(control(args.tenant, args.run_id, args.action))
        if args.action != 'cancel':
            while step(args.tenant, args.run_id, args.page_size):
                pass
        print(args.run_id)
    else:
        if not args.models or not args.mode:
            parser.error('--models and --mode required for a new replay')
        print(run(args.tenant, args.models, args.mode, args.page_size))
