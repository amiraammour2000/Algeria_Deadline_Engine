from pathlib import Path
import json
from engine.legal_knowledge_graph import LegalKnowledgeGraph
from engine.legal_comparator import LegalComparator

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))

def test_unverified_position_requires_review():
    g=LegalKnowledgeGraph(**{k:load('legal_knowledge_graph.json')[k] for k in ('nodes','edges')})
    out=LegalComparator(g).compare('RULE-ALG-08-09-829')
    assert out['status']=='unresolved'
    assert out['human_review_required'] is True

def test_verified_source_is_not_jurisprudence():
    gdata=load('legal_knowledge_graph.json')
    g=LegalKnowledgeGraph(gdata['nodes'], gdata['edges'])
    out=LegalComparator(g).compare('RULE-ALG-08-09-829')
    assert all(p['kind'] in {'supported','unverified'} for p in out['positions'])
