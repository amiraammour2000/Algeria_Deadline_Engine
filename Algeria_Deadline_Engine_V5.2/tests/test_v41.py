from pathlib import Path
import json
from engine.jurisprudence import JurisprudenceRepository
from engine.legal_intelligence import LegalIntelligence

ROOT=Path(__file__).resolve().parents[1]

def test_jurisprudence_registry_does_not_fabricate_authority():
    records=json.loads((ROOT/'data/jurisprudence.json').read_text(encoding='utf-8'))
    repo=JurisprudenceRepository(records)
    out=repo.search('délai notification', {'article':'829','title':'délai de recours'})
    assert out
    assert out[0]['record']['verified'] is False

def test_legal_intelligence_returns_jurisprudence_separately():
    sources=json.loads((ROOT/'data/legal_sources.json').read_text(encoding='utf-8'))
    records=json.loads((ROOT/'data/jurisprudence.json').read_text(encoding='utf-8'))
    li=LegalIntelligence(sources, records)
    rule={'id':'ALG-08-09-829','article':'829','title':'Délai de recours devant le tribunal administratif'}
    out=li.explain(rule, [], 'délai notification')
    assert 'jurisprudence' in out
    assert out['jurisprudence'][0]['record']['source_status']=='official_portal'
