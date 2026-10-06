from datetime import date
from engine.calendar import AlgerianCalendar
from engine.deadline import DeadlineEngine
from engine.rules import RuleRepository
from engine.case_engine import CaseEngine
from engine.audit import build_audit,verify_audit

def test_four_months():
    e=DeadlineEngine(AlgerianCalendar(), 'X','1'); d,t=e.compute(date(2026,10,10),4,'months'); assert d==date(2027,2,10)

def test_case_engine_blocks_unvalidated_event():
    rules=RuleRepository('legal_rules/rules.json'); ce=CaseEngine(rules,DeadlineEngine(AlgerianCalendar(),'X','1'))
    ev=[{'title':'Force majeure','effect_status':'pending_validation','legal_effect':'interruption','rule_ids':['ALG-08-09-832']}]
    out=ce.evaluate('ALG-08-09-829',{'start_date':'2026-01-01','notification_mentioned':True},ev,date(2026,1,2)); assert out['status']=='indeterminate'

def test_audit_integrity():
    a=build_audit({'id':'1'},[],{'status':'in_progress'}, {'ruleset_id':'X','ruleset_version':'1','rules':[]}); assert verify_audit(a); a['case']['id']='2'; assert not verify_audit(a)
