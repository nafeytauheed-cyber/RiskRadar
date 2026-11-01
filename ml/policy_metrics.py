"""Alert grouping evaluation using the serving policy's two-high opening rule."""
import numpy as np


def evaluate_policy(rows, probabilities):
    events=0;groups=0;delays=[];missed=0;false_groups=0;exposure=0
    for eq in sorted({r['equipment_id'] for r in rows}):
        items=[(r,float(p)) for r,p in zip(rows,probabilities) if r['equipment_id']==eq]
        items.sort(key=lambda x:x[0]['cycle'])
        high=0;opened=None;first_warning=None
        for r,p in items:
            if p>=.5:
                events+=1;high+=1
                if first_warning is None:first_warning=r['cycle']
            else:high=0
            if high>=2 and opened is None:opened=r['cycle'];groups+=1
        failure=items[0][0]['failure_cycle']
        exposure+=items[-1][0]['cycle']-items[0][0]['cycle']+1
        if opened is not None:
            if failure is None or not 0<failure-opened<=30:false_groups+=1
            if first_warning is not None:delays.append(opened-first_warning)
        elif first_warning is not None:missed+=1
    return {'warning_events':events,'incident_opens':groups,'reduction_fraction':1-groups/events if events else None,
            'opening_delay_cycles_vs_first_warning':delays,'units_with_warning_but_no_incident':missed,
            'false_incident_opens_per_1000_cycles':false_groups/exposure*1000,
            'assumption':'one unresolved incident per lifecycle; no simulated operator resolutions'}


def selective_error(y,p):
    rows=[]
    for margin in (0,.1,.2,.3,.4):
        chosen=abs(p-.5)>=margin
        rows.append({'confidence_margin':margin,'coverage':float(chosen.mean()),'classification_error':float(((p[chosen]>=.5)!=y[chosen]).mean()) if chosen.any() else None})
    return rows
