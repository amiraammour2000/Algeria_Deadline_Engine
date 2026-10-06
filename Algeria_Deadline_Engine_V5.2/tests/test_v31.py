from datetime import date
from pathlib import Path
from engine.rules import RuleRepository
from engine.calendar import AlgerianCalendar
from engine.deadline import DeadlineEngine
from engine.case_engine import CaseEngine
from engine.documents import Document

ROOT=Path(__file__).resolve().parents[1]

def make_engine():
    rules=RuleRepository(ROOT/'legal_rules/rules.json')
    cal=AlgerianCalendar(ROOT/'data/holidays_2026.json',weekend=(4,5))
    return CaseEngine(rules, DeadlineEngine(cal,rules.ruleset_id,rules.version)), rules

def test_no_silent_weekend_shift():
    engine,rules=make_engine()
    e=engine.evaluate('ALG-08-09-829', {'start_date':'2026-01-01','notification_mentioned':True}, [], today=date(2026,1,2))
    assert str(e['deadline']) == '2026-05-01'

def test_reclamation_creates_two_scenarios():
    engine,rules=make_engine()
    events=[{'event_type':'reclamation','title':'Réclamation','effect_status':'validated','legal_effect':'none','rule_ids':[]}]
    e=engine.evaluate('ALG-08-09-829', {'start_date':'2026-01-01','notification_mentioned':True}, events)
    ids={x['rule_id'] for x in e['scenarios']}
    assert 'ALG-08-09-830-C' in ids and 'ALG-08-09-830-RR' in ids

def test_document_hash():
    d=Document.from_bytes('CASE','a.txt',b'abc')
    assert d.sha256 == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
