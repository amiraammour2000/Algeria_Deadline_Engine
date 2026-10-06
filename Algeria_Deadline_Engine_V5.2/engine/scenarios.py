from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import uuid

@dataclass
class Scenario:
    id: str
    name: str
    description: str
    facts: Dict[str, Any]
    rule_id: str
    assumptions: List[str]

    @classmethod
    def new(cls, name, description, facts, rule_id, assumptions=None):
        return cls('SCN-'+uuid.uuid4().hex[:10].upper(), name, description, facts, rule_id, assumptions or [])

    def json(self):
        return asdict(self)

class ScenarioEngine:
    """Builds explicit alternative legal hypotheses; it does not choose between them."""
    def __init__(self, rules):
        self.rules = rules

    def generate(self, facts: Dict[str, Any], events: List[Dict[str, Any]], preferred_rule: str | None = None):
        scenarios = []
        if preferred_rule:
            r = self.rules.get(preferred_rule)
            scenarios.append(Scenario.new(
                'Hypothèse principale',
                f"Application de la règle {r['article']} au point de départ retenu.",
                dict(facts), preferred_rule,
                ['Le point de départ saisi est juridiquement exact.']
            ))

        # Article 830 branches are only proposed when the factual record contains the relevant event.
        has_claim = any(e.get('event_type') == 'reclamation' for e in events)
        if has_claim:
            for rid, label, assumption in [
                ('ALG-08-09-830-C', 'Hypothèse — silence sur réclamation', 'La réclamation a été valablement notifiée et aucune réponse n’est intervenue dans les deux mois.'),
                ('ALG-08-09-830-RR', 'Hypothèse — réponse à réclamation', 'Une réponse/rejet a été valablement notifiée au requérant.')
            ]:
                if rid in [r['id'] for r in self.rules.all()]:
                    scenarios.append(Scenario.new(label, self.rules.get(rid)['title'], dict(facts), rid, [assumption]))

        # An interruption is a branch, never an automatic effect.
        interrupting = [e for e in events if e.get('event_type') == 'evenement_interruptif']
        if interrupting and 'ALG-08-09-832' in [r['id'] for r in self.rules.all()]:
            scenarios.append(Scenario.new(
                'Hypothèse — interruption à qualifier',
                'Le dossier contient un événement présenté comme interruptif ; son effet doit être qualifié au regard de l’article 832.',
                dict(facts), preferred_rule or 'ALG-08-09-829',
                ['L’événement relève effectivement d’une cause d’interruption prévue par le texte.', 'La date et les effets de l’interruption sont établis.']
            ))
        return [s.json() for s in scenarios]
