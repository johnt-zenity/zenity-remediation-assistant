"""Deployment-selected synthetic profiles. Chat input cannot choose a profile."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Profile:
    key: str
    customer_label: str
    organization: str
    guidance_id: str
    resource_label: str


def load_profile(key='test'):
    if not isinstance(key,str) or not re.fullmatch('[a-z][a-z0-9-]{0,39}',key):
        raise ValueError('Invalid profile key')
    data=json.loads((Path(__file__).parent/'profiles'/f'{key}.json').read_text())
    if set(data) != {'key','customer_label','organization','guidance_id','resource_label'} or data['key']!=key:
        raise ValueError('Invalid profile schema')
    if any(not isinstance(v,str) or not 0<len(v)<=128 or any(ord(c)<32 for c in v) for v in data.values()):
        raise ValueError('Invalid profile value')
    if not data['organization'].startswith('synthetic-') or data['guidance_id']!='external-sharing-fixture-v1':
        raise ValueError('Only synthetic scope and fixture guidance are supported')
    return Profile(**data)

DEFAULT=load_profile()
