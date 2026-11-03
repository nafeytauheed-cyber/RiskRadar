import copy
import numpy as np
import pytest
from ml.causal import snapshot,label,digest
from ml.artifact import load,score,validate
from simulator.generate import generate
from app.platform.replay import compute

@pytest.fixture
def events():
    rows,_=generate(cycles=20)
    return [r for r in rows if r['equipment_id']=='degradation']

@pytest.fixture
def artifact(): return load('benchmarks/scientific/model.json')


def test_future_cannot_change_past(events,artifact):
    original=snapshot(events[:10],events[9],events[9]['received_at'])
    changed=copy.deepcopy(events)
    for e in changed[10:]:e['values']['temperature']=1e20
    assert snapshot(changed,changed[9],changed[9]['received_at'])==original
    assert score(artifact,original)==score(artifact,snapshot(changed,changed[9],changed[9]['received_at']))


def test_batch_invariance_and_train_serve_parity(events,artifact):
    single=snapshot(events,events[9],events[9]['received_at'])
    offline=[snapshot(events[:i+1],e,e['received_at']) for i,e in enumerate(events)]
    assert single==offline[9]
    assert score(artifact,single)==[score(artifact,s) for s in offline][9]


def test_missing_stale_and_session_reset(events):
    changed=copy.deepcopy(events)
    for e in changed[-4:]:e['values']['vibration']=None;e['quality']['vibration']='missing'
    assert snapshot(changed,changed[-1],changed[-1]['received_at'])['quality_state']=='missing'
    assert snapshot(events,events[-1],events[-1]['received_at']+90000)['quality_state']=='stale'
    changed[-1]['session_id']='new'
    assert snapshot(changed,changed[-1],changed[-1]['received_at'])['quality_state']=='warmup'


def test_late_observation_revises_not_original(events):
    delayed=copy.deepcopy(events);delayed[5]['received_at']=events[-1]['received_at']+1
    f=snapshot(delayed,delayed[9],delayed[9]['received_at'])
    corrected=snapshot(delayed,delayed[9],delayed[5]['received_at'])
    assert delayed[5]['event_id'] not in f['input_refs']
    assert delayed[5]['event_id'] in corrected['input_refs']

@pytest.mark.parametrize('args,expected',[
    ((10,20,30,10),1),((20,20,30,10),None),((10,None,15,10),None),
    ((10,None,30,10),0),((10,30,40,10,15),None),((10,14,40,10,15),1),
    ((10,5,40,10),None),((10,15,12,10),None)])
def test_label(args,expected):assert label(*args)==expected


def test_artifact_rejection(artifact,tmp_path):
    for key,value in [('format','pickle'),('scale',[0]*15),('coef',[float('nan')]*15)]:
        a=copy.deepcopy(artifact);a[key]=value
        with pytest.raises(ValueError):validate(a)
    with pytest.raises(ValueError):validate(artifact,'wronghash')
    p=tmp_path/'evil';p.write_bytes(b'\x80\x04pickle')
    with pytest.raises((ValueError,UnicodeError)):load(p)


def test_replay_deterministic_and_isolated(events,artifact):
    a={digest(artifact):artifact};original=copy.deepcopy(events)
    r=compute(events,a,'arrival')
    assert r==compute(list(reversed(events)),a,'arrival')
    assert events==original
    assert all('incident_id' not in x and 'notification' not in x for x in r)
    corrected=compute(events,a,'corrected')
    assert all(x['snapshot']['features']==y['snapshot']['features'] for x,y in zip(r,corrected))
    assert all(x['snapshot']['input_refs']==y['snapshot']['input_refs'] for x,y in zip(r,corrected))
    assert corrected[0]['snapshot']['arrival_cutoff']==events[-1]['received_at']


def test_idle_gap_requires_new_warmup(events):
    changed=copy.deepcopy(events)
    changed[-1]['observed_at']+=90000
    changed[-1]['received_at']+=90000
    assert snapshot(changed,changed[-1],changed[-1]['received_at'])['quality_state']=='warmup'


def test_grouping_measures_delay():
    from ml.policy_metrics import evaluate_policy
    rows=[{'equipment_id':'x','cycle':i,'failure_cycle':8} for i in range(1,7)]
    result=evaluate_policy(rows,[.1,.6,.7,.8,.2,.9])
    assert result['warning_events']==4 and result['incident_opens']==1
    assert result['opening_delay_cycles_vs_first_warning']==[1]
