from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import re

@dataclass(frozen=True)
class QualificationCandidate:
    id: str
    category: str
    label: str
    rule_id: Optional[str]
    trigger: Optional[str]
    evidence_ids: List[str]
    rationale: List[str]
    confidence: float
    status: str = 'candidate'
    human_review_required: bool = True
    missing: List[str] = None

    def json(self):
        d = asdict(self)
        d['missing'] = self.missing or []
        return d

class LegalQualificationEngine:
    """Assist legal qualification from validated case facts and document proposals.

    It deliberately produces hypotheses, not legal conclusions. Keyword matches are
    only signals; a candidate becomes usable only after human validation and adequate
    evidence. The engine is deterministic and every rationale is traceable to an event,
    document proposal or rule metadata.
    """
    EVENT_MAP = {
        'acte_administratif': ('administrative_act', 'Acte administratif'),
        'notification': ('notification', 'Notification'),
        'reclamation': ('reclamation', 'Réclamation administrative'),
        'reponse': ('reply', 'Réponse administrative'),
        'recours': ('appeal', 'Recours contentieux'),
        'evenement_interruptif': ('interruptive_event', 'Événement interruptif'),
        'evenement_suspensif': ('suspensive_event', 'Événement suspensif'),
    }

    def __init__(self, rules_repository):
        self.rules = rules_repository

    def qualify(self, events: List[Dict[str, Any]], documents: List[Dict[str, Any]],
                selected_rule_id: Optional[str] = None) -> Dict[str, Any]:
        candidates: List[QualificationCandidate] = []
        event_kinds = []
        for e in events:
            kind, label = self.EVENT_MAP.get(e.get('event_type'), (e.get('event_type'), e.get('title', 'Événement')))
            event_kinds.append((kind, label, e))
            candidates.append(self._event_candidate(e, kind, label))

        analyses = []
        for d in documents:
            raw = d.get('extraction_json') or '{}'
            try:
                import json
                data = json.loads(raw)
            except Exception:
                data = {}
            analyses.append((d, data))
            for p in data.get('proposals', []):
                if p.get('status') == 'validated':
                    candidates.extend(self._proposal_candidates(d, p))

        for rule in self.rules.all():
            if selected_rule_id and rule['id'] != selected_rule_id:
                continue
            candidates.append(self._rule_candidate(rule, event_kinds, analyses))

        # A rule candidate is stronger when its trigger has matching case events.
        for c in list(candidates):
            if c.category != 'legal_regime':
                continue
            candidates = self._replace(candidates, c, self._score_rule_candidate(c, event_kinds, analyses))

        missing = self._global_missing(event_kinds, analyses, selected_rule_id)
        return {
            'schema': 'legal-qualification/v1',
            'candidates': [c.json() for c in candidates],
            'global_missing': missing,
            'human_review_required': True,
            'validated_count': sum(c.status == 'validated' for c in candidates),
            'candidate_count': len(candidates),
            'disclaimer': 'Qualification assistée uniquement. Aucun rapprochement lexical ne constitue une autorité juridique et aucune proposition ne devient un fait ou une conclusion sans validation humaine.'
        }

    def _event_candidate(self, e, kind, label):
        verified = e.get('effect_status') == 'validated'
        rationale = [f"Événement {e.get('id','')}: {label}", f"Date: {e.get('event_date','—')}"]
        if e.get('description'):
            rationale.append(f"Description: {e['description'][:220]}")
        return QualificationCandidate(
            id=f"Q-E-{e.get('id','')[:12]}", category='fact_qualification',
            label=label, rule_id=None, trigger=kind,
            evidence_ids=[e.get('id')] if e.get('id') else [], rationale=rationale,
            confidence=0.90 if verified else 0.65,
            status='validated' if verified else 'candidate',
            human_review_required=not verified,
            missing=[] if verified else ['Validation de l’effet juridique de l’événement']
        )

    def _proposal_candidates(self, d, p):
        value = str(p.get('value',''))
        kind = p.get('kind')
        out=[]
        if kind == 'date':
            out.append(QualificationCandidate(
                id=f"Q-D-{d.get('id','')[:8]}-{re.sub(r'[^0-9]','',value)}",
                category='candidate_date', label=f'Date extraite : {value}', rule_id=None,
                trigger='date', evidence_ids=[d.get('id')],
                rationale=[f"Pièce: {d.get('filename','')}", f"Extraction validée: {value}"],
                confidence=0.94, status='candidate', human_review_required=True,
                missing=['Validation humaine de la date et de sa signification juridique']
            ))
        elif kind == 'legal_reference':
            out.append(QualificationCandidate(
                id=f"Q-L-{d.get('id','')[:8]}-{abs(hash(value))%100000}",
                category='legal_reference', label=value, rule_id=None, trigger='legal_reference',
                evidence_ids=[d.get('id')], rationale=[f"Référence détectée dans {d.get('filename','')}: {value}"],
                confidence=0.82, status='candidate', human_review_required=True,
                missing=['Vérification de la référence et de sa version applicable']
            ))
        elif kind == 'jurisdiction':
            out.append(QualificationCandidate(
                id=f"Q-J-{d.get('id','')[:8]}-{abs(hash(value))%100000}",
                category='jurisdiction', label=value, rule_id=None, trigger='jurisdiction',
                evidence_ids=[d.get('id')], rationale=[f"Juridiction détectée dans {d.get('filename','')}: {value}"],
                confidence=0.78, status='candidate', human_review_required=True,
                missing=['Validation de la juridiction compétente']
            ))
        return out

    def _rule_candidate(self, rule, event_kinds, analyses):
        trigger = rule.get('trigger')
        matched = self._trigger_match(trigger, event_kinds)
        rationale = [f"Règle {rule['id']} — article {rule.get('article','—')}: {rule.get('title','')}"]
        if trigger: rationale.append(f"Déclencheur attendu: {trigger}")
        if matched: rationale.append('Un ou plusieurs événements du dossier correspondent au déclencheur.')
        else: rationale.append('Aucun déclencheur suffisant n’est encore établi dans la chronologie.')
        missing=[] if matched else ['Établir le fait déclencheur conformément au texte applicable']
        if rule.get('requires_human_validation', True): missing.append('Validation juridique humaine')
        return QualificationCandidate(
            id=f"Q-R-{rule['id']}", category='legal_regime', label=rule.get('title',rule['id']),
            rule_id=rule['id'], trigger=trigger, evidence_ids=[e.get('id') for _,_,e in event_kinds if self._trigger_match(trigger, [(self.EVENT_MAP.get(e.get('event_type'), (e.get('event_type'),'')), '', e)])],
            rationale=rationale, confidence=0.82 if matched else 0.35, status='candidate',
            human_review_required=True, missing=missing
        )

    def _score_rule_candidate(self, c, event_kinds, analyses):
        matched = self._trigger_match(c.trigger, event_kinds)
        confidence = 0.86 if matched else 0.35
        missing = [x for x in (c.missing or []) if x != 'Validation juridique humaine']
        if not matched and 'Établir le fait déclencheur conformément au texte applicable' not in missing:
            missing.append('Établir le fait déclencheur conformément au texte applicable')
        return QualificationCandidate(c.id,c.category,c.label,c.rule_id,c.trigger,c.evidence_ids,c.rationale,
            confidence,c.status,True,missing+['Validation juridique humaine'])

    @staticmethod
    def _replace(items, old, new):
        return [new if x.id == old.id else x for x in items]

    @staticmethod
    def _trigger_match(trigger, event_kinds):
        if not trigger: return False
        names = {k for k,_,_ in event_kinds}
        if trigger == 'notification_individual_or_publication_collective_or_regulatory':
            return 'notification' in names or 'administrative_act' in names
        if trigger == 'within_article_829_period':
            return 'reclamation' in names
        if trigger == 'notification_reclamation_to_authority':
            return 'reclamation' in names
        if trigger == 'expiry_of_two_month_reclamation_period':
            return 'reclamation' in names
        if trigger == 'notification_of_rejection':
            return 'reply' in names
        if trigger == 'notification':
            return 'notification' in names
        return trigger in names

    @staticmethod
    def _global_missing(event_kinds, analyses, selected_rule_id):
        missing=[]
        if not event_kinds: missing.append('Ajouter au moins un événement juridiquement pertinent')
        if not analyses: missing.append('Associer au moins une pièce lorsque la qualification dépend d’un document')
        if not selected_rule_id: missing.append('Sélectionner ou valider le régime juridique applicable')
        missing.append('Valider humainement les propositions de qualification avant calcul définitif')
        return missing
