import copy
import json
from pathlib import Path
import pytest
from ml.artifact import load, validate, score
from ml.runtimes import resolve, descriptors


def test_historical_features_match_pre_refactor_git_checkpoints():
    golden=json.loads(Path('tests/fixtures/historical_features.json').read_text())
    events=golden['events']
    for version,expected in golden['snapshots'].items():
        assert resolve(version).snapshot(events,events[-1],events[-1]['received_at'])==expected
    assert golden['snapshots']['causal-v1']['features']!=golden['snapshots']['causal-v2']['features']


def test_runtime_allowlist_and_compatibility():
    with pytest.raises(ValueError):resolve('untrusted.module')
    a=load('benchmarks/scientific/model.json')
    old=copy.deepcopy(a);old['feature_version']='causal-v1';validate(old)
    assert not resolve('causal-v1').promotable
    assert len(descriptors({'old':old,'current':a}))==2
    with pytest.raises(ValueError,match='version mismatch'):
        score(a,{'feature_version':'causal-v1','quality_state':'warmup'})
