from engine.rules import RuleRepository
from engine.legal_qualification import LegalQualificationEngine
from pathlib import Path


def engine():
    return LegalQualificationEngine(RuleRepository(Path('legal_rules/rules.json')))


def test_qualification_never_auto_concludes():
    out = engine().qualify([], [], 'ALG-08-09-829')
    assert out['human_review_required'] is True
    assert 'Ajouter au moins un événement juridiquement pertinent' in out['global_missing']
    assert all(c['status'] != 'validated' for c in out['candidates'])


def test_notification_supports_rule_candidate_but_requires_review():
    events=[{'id':'evt-1','event_type':'notification','title':'Notification','event_date':'2026-03-14','description':'Acte notifié','effect_status':'validated'}]
    out=engine().qualify(events, [], 'ALG-08-09-829')
    c=next(x for x in out['candidates'] if x['rule_id']=='ALG-08-09-829')
    assert c['confidence'] >= .8
    assert c['human_review_required'] is True
    assert c['status']=='candidate'


def test_validated_date_proposal_remains_candidate():
    import json
    docs=[{'id':'doc-1','filename':'notification.pdf','extraction_json':json.dumps({'proposals':[{'kind':'date','value':'2026-03-14','status':'validated'}]})}]
    out=engine().qualify([], docs, 'ALG-08-09-829')
    c=next(x for x in out['candidates'] if x['category']=='candidate_date')
    assert c['status']=='candidate'
    assert c['human_review_required'] is True
