import json
from pathlib import Path
from engine.legal_versioning import LegalVersioningEngine

ROOT=Path(__file__).resolve().parents[1]

def load(): return json.loads((ROOT/'data/legal_versions.json').read_text(encoding='utf-8'))

def test_publication_is_not_effective_date():
    e=LegalVersioningEngine(load()['versions'])
    out=e.applicable('ALG-08-09-829','2022-08-01')
    assert out['status']=='unresolved'
    assert out['human_review_required'] is True

def test_confirmed_version_is_selectable():
    data=load()['versions']
    data[0]['effective_from']='2008-05-01'; data[0]['effective_date_status']='confirmed'; data[0]['effective_to']='2022-07-18'
    e=LegalVersioningEngine(data)
    out=e.applicable('ALG-08-09-829','2020-06-01')
    assert out['status']=='selected'
    assert out['selected']['id']=='VER-ALG-08-09-829-2008'

def test_overlap_requires_human_review():
    data=load()['versions']
    for x in data:
        x['effective_from']='2020-01-01'; x['effective_date_status']='confirmed'
    e=LegalVersioningEngine(data)
    out=e.applicable('ALG-08-09-829','2021-01-01')
    assert out['status']=='conflict'
    assert out['human_review_required'] is True

def test_timeline_exposes_amendment_relation():
    e=LegalVersioningEngine(load()['versions'])
    out=e.timeline('ALG-08-09-829')
    assert any('VER-ALG-08-09-829-2008' in x['amends'] for x in out['amendments'])
