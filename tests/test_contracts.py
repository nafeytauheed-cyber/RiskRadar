import copy
from datetime import datetime,timezone
import pytest
from app.platform.contracts import Event
from simulator.generate import generate


def payload():
    e=generate(cycles=1)[0][0];e.pop('received_at');e['observed_at']=datetime.fromtimestamp(e['observed_at'],timezone.utc).isoformat();return e


def test_good_event():assert Event(**payload()).schema_version==1

@pytest.mark.parametrize('change',[{'tenant_id':'spoof'}, {'received_at':'spoof'}, {'schema_version':2}, {'observed_at':'2025-01-01'}, {'sequence':-1}])
def test_bad_event(change):
    with pytest.raises(ValueError):Event(**dict(payload(),**change))


def test_nonfinite_units_and_flags():
    for kind in ('nonfinite','units','null'):
        e=payload()
        if kind=='nonfinite':e['values']['rpm']=float('inf')
        if kind=='units':e['units']['temperature']='F'
        if kind=='null':e['values']['rpm']=None
        with pytest.raises(ValueError):Event(**e)
