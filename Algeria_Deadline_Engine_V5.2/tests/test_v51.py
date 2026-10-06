import json
from pathlib import Path
from datetime import date
from engine.repository import CaseRepository
from engine.rules import RuleRepository
from engine.calendar import AlgerianCalendar
from engine.deadline import DeadlineEngine
from engine.case_engine import CaseEngine
from engine.legal_qualification import LegalQualificationEngine
from engine.legal_research import LegalResearchEngine
from engine.legal_versioning import LegalVersioningEngine
from engine.legal_knowledge_graph import LegalKnowledgeGraph
from engine.legal_comparator import LegalComparator
from engine.case_orchestrator import LegalCaseOrchestrator

ROOT=Path(__file__).resolve().parents[1]

def services(tmp_path):
    rules=RuleRepository(ROOT/'legal_rules/rules.json')
    sources=json.loads((ROOT/'data/legal_sources.json').read_text(encoding='utf-8'))
    juris=json.loads((ROOT/'data/jurisprudence.json').read_text(encoding='utf-8'))
    gd=json.loads((ROOT/'data/legal_knowledge_graph.json').read_text(encoding='utf-8'))
    graph=LegalKnowledgeGraph(gd['nodes'],gd['edges'])
    cal=AlgerianCalendar(ROOT/'data/holidays_2026.json',weekend=(4,5))
    eng=CaseEngine(rules, DeadlineEngine(cal,rules.ruleset_id,rules.version))
    return LegalCaseOrchestrator(rules=rules, engine=eng,
        qualifier=LegalQualificationEngine(rules), research=LegalResearchEngine(sources,rules,juris),
        versioning=LegalVersioningEngine.from_json(ROOT/'data/legal_versions.json',rules), comparator=LegalComparator(graph))

def test_orchestrator_blocks_unconfirmed_version(tmp_path):
    o=services(tmp_path)
    case={'id':'C1','reference':'DOS-1','title':'Test'}
    events=[{'id':'E1','event_date':date(2026,3,14),'event_type':'notification','title':'Notification','description':'','effect_status':'validated'}]
    out=o.run(case=case,events=events,documents=[],rule_id='ALG-08-09-829',facts={'start_date':'2026-03-14'})
    assert out['readiness']=='blocked'
    assert out['version']['status']=='unresolved'
    assert out['conclusion']['human_review_required'] is True
    assert len(out['snapshot_hash'])==64

def test_orchestrator_produces_trace_and_research(tmp_path):
    o=services(tmp_path)
    out=o.run(case={'id':'C2','reference':'DOS-2','title':'Test'},events=[{'id':'E1','event_date':date(2026,3,14),'event_type':'notification','title':'Notification','effect_status':'validated'}],documents=[],rule_id=None,facts={'start_date':'2026-03-14'})
    assert [x['step'] for x in out['trace']]==[1,2,3,4,6]
    assert out['research']['human_review_required'] is True
    assert out['readiness']=='blocked'
