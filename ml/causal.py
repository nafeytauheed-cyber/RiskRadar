"""Single causal feature implementation for offline evaluation and serving.

Cycles are device operating counters, not row numbers or elapsed hours.
Lifecycle boundaries must be assigned by the equipment owner after maintenance.
"""
from dataclasses import dataclass
import hashlib
import json
import math

SENSORS = ('temperature', 'vibration', 'pressure', 'current', 'rpm')
UNITS = dict(zip(SENSORS, ('degC', 'mm/s', 'kPa', 'A', 'rpm')))
FEATURE_VERSION = 'causal-v2'
FEATURES = tuple(f'{s}_{stat}' for s in SENSORS for stat in ('mean', 'std', 'slope'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class FeaturePolicy:
    window: int = 10
    min_samples: int = 5
    max_fill_cycles: int = 2
    max_age_seconds: int = 86400


def snapshot(events, target, arrival_cutoff, policy=FeaturePolicy(), freshness_cutoff=None):
    """Only same lifecycle/session, <= observation AND arrival cutoffs.

    Session changes reset warmup. Null/bad samples may be filled for <=2 cycles;
    the timestamp guard also prevents carrying idle values indefinitely.
    Input references include null/bad records that affect quality decisions.
    """
    rows = [e for e in events if all(e[k] == target[k] for k in
            ('equipment_id', 'lifecycle_id', 'session_id'))
            and e['cycle'] <= target['cycle'] and e['observed_at'] <= target['observed_at']
            and e['received_at'] <= arrival_cutoff
            and target['observed_at'] - e['observed_at'] <= policy.max_age_seconds]
    rows.sort(key=lambda e: (e['cycle'], e['observed_at'], e['sequence'], e['event_id']))
    rows = [e for e in rows if e['cycle'] > target['cycle'] - policy.window]
    values, filled, missing = [], False, False
    for sensor in SENSORS:
        samples = []
        last = None
        for e in rows:
            value = e['values'].get(sensor)
            if value is not None and e['quality'].get(sensor) == 'good' and math.isfinite(value):
                last = (e['cycle'], e['observed_at'], value)
            elif last and e['cycle'] - last[0] <= policy.max_fill_cycles and e['observed_at']-last[1] <= policy.max_age_seconds:
                value = last[2]
                filled = True
            else:
                value = None
            if value is not None:
                samples.append((e['cycle'], value))
            if e['event_id'] == target['event_id'] and value is None:
                missing = True
        if len(samples) < policy.min_samples:
            missing = True
        if samples:
            n = len(samples)
            mx = sum(x for x, _ in samples)/n
            my = sum(y for _, y in samples)/n
            denom = sum((x-mx)**2 for x, _ in samples)
            slope = sum((x-mx)*(y-my) for x,y in samples)/denom if denom else 0.
            std = math.sqrt(sum((y-my)**2 for _,y in samples)/max(n-1, 1))
            values.extend((my, std, slope))
        else:
            values.extend((0., 0., 0.))  # unscorable placeholders; never healthy defaults
    freshness_cutoff = arrival_cutoff if freshness_cutoff is None else freshness_cutoff
    age = freshness_cutoff-target['observed_at']
    quality = 'stale' if age > policy.max_age_seconds else ('missing' if missing else ('imputed' if filled else 'good'))
    if len(rows) < policy.min_samples and quality != 'stale':
        quality = 'warmup'
    result = {'feature_version': FEATURE_VERSION, 'features': values, 'quality_state': quality,
              'input_refs': [e['event_id'] for e in rows], 'observation_cutoff': target['observed_at'],
              'arrival_cutoff': arrival_cutoff, 'freshness_cutoff': freshness_cutoff, 'feature_policy': policy.__dict__}
    result['sha256'] = digest(result)
    return result


def label(cycle, failure_cycle, followup_cycle, horizon, intervention_cycle=None):
    """P(failure in (cycle, cycle+H]); return None for censored/intervened rows.

    A failure before an intervention is observable. Post-failure and post-
    intervention rows require a new lifecycle and are excluded here.
    """
    if horizon <= 0 or followup_cycle < cycle:
        return None
    if failure_cycle is not None and cycle >= failure_cycle:
        return None
    if intervention_cycle is not None and cycle >= intervention_cycle:
        return None
    end = cycle + horizon
    if failure_cycle is not None and cycle < failure_cycle <= min(end, followup_cycle):
        if intervention_cycle is None or failure_cycle < intervention_cycle:
            return 1
    if intervention_cycle is not None and intervention_cycle <= end:
        return None
    return 0 if followup_cycle >= end else None
