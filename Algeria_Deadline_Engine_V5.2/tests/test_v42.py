from pathlib import Path
import json
from engine.legal_knowledge_graph import LegalKnowledgeGraph
from engine.legal_intelligence import LegalIntelligence

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))

def test_graph_links_rule_to_official_source():
    data=load('legal_knowledge_graph.json')
    g=LegalKnowledgeGraph(data['nodes'], data['edges'])
    out=g.related('RULE-ALG-08-09-829')
    ids={n['id'] for n in out['nodes']}
    assert 'SRC-JO-2008-21' in ids

def test_unverified_jurisprudence_never_becomes_verified():
    data=load('legal_knowledge_graph.json')
    g=LegalKnowledgeGraph(data['nodes'], data['edges'])
    node=g.nodes['JUR-PORTAL-PLACEHOLDER-001']
    assert node.verified is False

def test_legal_intelligence_exposes_graph_trace():
    li=LegalIntelligence(load('legal_sources.json'), load('jurisprudence.json'), load('legal_knowledge_graph.json'))
    rule={'id':'RULE-ALG-08-09-829','article':'829','title':'Délai de recours'}
    out=li.explain(rule, [], 'notification')
    assert out['knowledge_graph']['root']==rule['id']
    assert any(n['id']=='SRC-JO-2008-21' for n in out['knowledge_graph']['nodes'])
