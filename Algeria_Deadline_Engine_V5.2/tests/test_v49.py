import json
from pathlib import Path
from engine.rules import RuleRepository
from engine.legal_research import LegalResearchEngine

ROOT=Path(__file__).resolve().parents[1]

def load(name): return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))

def test_research_returns_registered_official_sources():
    rules=RuleRepository(ROOT/'legal_rules/rules.json')
    engine=LegalResearchEngine(load('legal_sources.json'), rules, load('jurisprudence.json'))
    out=engine.search('article 829 délai recours', 'ALG-08-09-829')
    assert out['human_review_required'] is True
    assert any(x['id']=='SRC-JO-2008-21' for x in out['results'])
    assert all(x['status'] in {'official','verified','unverified'} for x in out['results'])

def test_unverified_jurisprudence_stays_unverified():
    rules=RuleRepository(ROOT/'legal_rules/rules.json')
    engine=LegalResearchEngine(load('legal_sources.json'), rules, load('jurisprudence.json'))
    out=engine.search('jurisprudence')
    assert all(x['status'] != 'verified' or x['kind']=='source' for x in out['results'])

def test_transport_verification_never_mutates_registry():
    rules=RuleRepository(ROOT/'legal_rules/rules.json')
    sources=load('legal_sources.json')
    engine=LegalResearchEngine(sources, rules, [])
    before=engine.sources[0]
    result=engine.verify_url(before.id, timeout=2)
    assert result['id']==before.id
    assert engine.sources[0].url==before.url
