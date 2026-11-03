from datetime import datetime, timezone
import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ml.causal import SENSORS, UNITS

class Event(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    event_id: str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_.:-]+$')
    equipment_id: str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_.:-]+$')
    lifecycle_id: str=Field(min_length=1,max_length=100)
    session_id: str=Field(min_length=1,max_length=100)
    sequence: int=Field(ge=0,le=2**53-1)
    cycle: int=Field(ge=0,le=2**53-1)
    observed_at: str
    schema_version: Literal[1]
    values: dict[str,float|None]
    units: dict[str,str]
    quality: dict[str,Literal['good','bad','missing']]

    @model_validator(mode='after')
    def validate_event(self):
        if set(self.values)!=set(SENSORS) or self.units!=UNITS or set(self.quality)!=set(SENSORS):
            raise ValueError('explicit sensor values, canonical units and quality required')
        for s,v in self.values.items():
            if v is not None and not math.isfinite(v): raise ValueError('nonfinite telemetry')
            if v is None and self.quality[s]=='good': raise ValueError('null cannot be good')
        t=datetime.fromisoformat(self.observed_at.replace('Z','+00:00'))
        if t.tzinfo is None: raise ValueError('timezone required')
        if t.timestamp()>datetime.now(timezone.utc).timestamp()+300: raise ValueError('clock skew exceeds 5 minutes')
        if t.year<2000: raise ValueError('timestamp outside supported range')
        self.observed_at=t.astimezone(timezone.utc).isoformat()
        return self
