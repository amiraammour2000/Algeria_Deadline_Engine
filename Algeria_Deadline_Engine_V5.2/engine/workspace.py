from __future__ import annotations
from datetime import date
from .evidence_report import EvidenceBasedLegalReport, EvidenceItem

def build_case_report(case, events, documents, evaluation, audit, lang='fr'):
    report = EvidenceBasedLegalReport(str(case['id']), case['title'] or case['reference'])
    report.add_question('Q1', 'Question juridique / Legal question / المسألة القانونية', status='open')
    for e in events:
        report.add_fact('F-'+e['id'][:8], e['title'], e.get('description') or e['event_date'].isoformat(), event_id=e['id'], verified=e.get('effect_status')=='validated')
    scenarios = evaluation.get('scenarios', []) if evaluation else []
    if not scenarios:
        scenarios = [{'id':'S1','name':'Évaluation principale','rule_id':evaluation.get('rule_id') if evaluation else None,'description':'Scénario principal','assumptions':[]}]
    for i,s in enumerate(scenarios):
        sid=s.get('id') or f'S{i+1}'
        report.add_scenario(sid, s.get('name') or s.get('label') or sid, rule_id=s.get('rule_id'), fact_ids=[f['id'] for f in report.facts], status='candidate')
    if evaluation:
        sid=scenarios[0].get('id') or 'S1'
        report.add_computation(evaluation.get('calculation_id','CALC'), scenario_id=sid, start=str(evaluation.get('start_date') or evaluation.get('start') or ''), end=str(evaluation.get('deadline') or ''), mode=str(evaluation.get('mode') or 'legal'), result=str(evaluation.get('status') or ''), confidence=float(evaluation.get('confidence') or 0))
    for d in documents:
        report.add_evidence(EvidenceItem('E-'+d['id'][:8], 'document', d['filename'], document_id=d['id'], hash=d['sha256'], verified=True))
    if evaluation:
        evidence_ids=[e.id for e in report.evidence]
        report.add_conclusion('K1', f"Statut: {evaluation.get('status','—')}; échéance: {evaluation.get('deadline','—')}", status='candidate', scenario_ids=[s.get('id') or 'S1' for s in scenarios], evidence_ids=evidence_ids, human_review_required=True)
    return report.build()
