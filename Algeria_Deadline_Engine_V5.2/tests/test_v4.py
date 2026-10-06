from pathlib import Path
from engine.legal_intelligence import LegalIntelligence
import json

ROOT=Path(__file__).resolve().parents[1]

def test_official_sources_rank_for_article_829():
    sources=json.loads((ROOT/'data/legal_sources.json').read_text(encoding='utf-8'))
    li=LegalIntelligence(sources)
    rule={'id':'ALG-08-09-829','article':'829','title':'Délai de recours devant le tribunal administratif','trigger':'notification'}
    out=li.explain(rule,[{'title':'Notification de la décision','event_type':'notification','effect_status':'validated'}])
    assert out['sources']
    assert out['sources'][0]['source_id']=='SRC-JO-2008-21'

def test_validation_warning_is_explicit():
    li=LegalIntelligence([])
    rule={'title':'Force majeure','article':'832','requires_human_validation':True}
    out=li.explain(rule,[{'title':'Force majeure alléguée','event_type':'evenement_interruptif','effect_status':'pending_validation'}])
    codes={x['code'] for x in out['unresolved']}
    assert 'LEGAL_VALIDATION_REQUIRED' in codes
    assert 'EVENT_EFFECT_UNVALIDATED' in codes
