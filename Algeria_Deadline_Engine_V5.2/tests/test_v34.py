from pathlib import Path
from datetime import date
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

def test_evidence_graph_links_case_rule_event_and_document():
    engine, rules = make_engine()
    d = Document.from_bytes('CASE','notification.txt',b'notification 01/01/2026')
    events=[{'id':'EV1','event_type':'notification','title':'Notification','event_date':date(2026,1,1),'effect_status':'validated','legal_effect':'none','rule_ids':[],'source_document':d.id}]
    e=engine.evaluate('ALG-08-09-829', {'start_date':'2026-01-01','notification_mentioned':True}, events, today=date(2026,1,2), documents=[d.json()], case={'id':'CASE','reference':'DOS-001'})
    g=e['evidence_graph']
    assert g['node_count'] >= 5
    assert any(x['relation']=='supported_by' for x in g['edges'])
    assert any(x['relation']=='triggered_by' for x in g['edges'])

def test_pending_event_creates_unresolved_node():
    engine, _ = make_engine()
    events=[{'id':'EV2','event_type':'evenement_interruptif','title':'Force majeure','event_date':date(2026,2,1),'effect_status':'pending_validation','legal_effect':'interruption','rule_ids':[]}]
    e=engine.evaluate('ALG-08-09-829', {'start_date':'2026-01-01','notification_mentioned':True}, events, today=date(2026,1,2), case={'reference':'DOS-002'})
    assert any(n['node_type']=='unresolved' for n in e['evidence_graph']['nodes'])
