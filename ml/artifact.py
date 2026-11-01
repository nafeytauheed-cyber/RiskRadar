"""Data-only immutable logistic artifacts. Never deserialize pickle/joblib."""
import json
import math
from pathlib import Path
import numpy as np
from .causal import FEATURES, FEATURE_VERSION, digest

MAX_BYTES = 1024 * 1024


def validate(a, expected_hash=None):
    if not isinstance(a, dict) or set(a) != {'format', 'features', 'feature_version', 'mean', 'scale', 'coef', 'intercept', 'calibration', 'baseline', 'horizon', 'provenance'}:
        raise ValueError('invalid artifact schema')
    if a['format'] != 'riskradar-logistic-v1' or a['features'] != list(FEATURES) or a['feature_version'] != FEATURE_VERSION:
        raise ValueError('unsupported artifact version/features')
    for key in ('mean', 'scale', 'coef'):
        if len(a[key]) != len(FEATURES) or not all(type(v) in (int,float) and math.isfinite(v) for v in a[key]):
            raise ValueError('invalid numeric array')
    if any(v <= 0 for v in a['scale']) or type(a['horizon']) != int or a['horizon'] <= 0:
        raise ValueError('invalid scale/horizon')
    if set(a['calibration']) != {'slope','intercept','version'}:
        raise ValueError('invalid calibration')
    if not all(type(v) in (int,float) and math.isfinite(v) for v in
               (a['intercept'],a['calibration']['slope'],a['calibration']['intercept'])):
        raise ValueError('nonfinite coefficient')
    if expected_hash and digest(a) != expected_hash:
        raise ValueError('artifact hash mismatch')
    return a


def load(path, expected_hash=None):
    p = Path(path)
    if p.stat().st_size > MAX_BYTES:
        raise ValueError('artifact too large')
    return validate(json.loads(p.read_text()), expected_hash)


def score(a, feature_snapshot):
    validate(a)
    if feature_snapshot['quality_state'] not in ('good', 'imputed'):
        return {'failure_probability': None, 'anomaly_evidence': None, 'hypotheses': [], 'priority': 'inspect_data'}
    x = (np.asarray(feature_snapshot['features'])-a['mean'])/a['scale']
    raw = float(x @ a['coef'] + a['intercept'])
    z = a['calibration']['slope']*raw+a['calibration']['intercept']
    probability = 1/(1+math.exp(-max(-700.,min(700.,z))))
    return {'failure_probability': probability,
            'anomaly_evidence': {'method': 'max_abs_training_z', 'value': float(abs(x).max()), 'is_probability': False},
            'hypotheses': [{'name': 'unknown', 'support': None, 'note': 'No validated fault identification model'}],
            'priority': 'inspect' if probability >= .5 else 'monitor'}
