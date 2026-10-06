import json
from engine.document_intelligence import DocumentIntelligence

def test_extracts_multilingual_legal_candidates():
    text='Notification du 14/03/2026. Article 829 de la loi n° 08-09. Cour suprême.\nالمحكمة العليا بتاريخ 2026-04-02'
    a=DocumentIntelligence().propose(text)
    assert any(x.kind=='date' and x.value=='2026-03-14' for x in a)
    assert any(x.kind=='legal_reference' for x in a)
    assert any(x.kind=='jurisdiction' for x in a)

def test_arabic_language_detection():
    assert DocumentIntelligence.detect_language('المحكمة العليا ومجلس الدولة') == 'ar'

def test_binary_analysis_is_hash_stable():
    a=DocumentIntelligence().analyze('DOC-1','x.txt',b'Article 12\n14/03/2026','text/plain')
    b=DocumentIntelligence().analyze('DOC-1','x.txt',b'Article 12\n14/03/2026','text/plain')
    assert a.sha256==b.sha256
    assert a.proposals[0].status=='candidate'
