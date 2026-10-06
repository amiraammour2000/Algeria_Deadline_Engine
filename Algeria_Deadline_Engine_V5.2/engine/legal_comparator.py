from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import re

@dataclass(frozen=True)
class LegalPosition:
    id: str
    label: str
    kind: str
    proposition: str
    support_ids: List[str]
    confidence: float

class LegalComparator:
    """Compare candidate legal positions without pretending to resolve disputes.

    The comparator uses explicit graph relations and verified status. Similarity
    or keyword overlap is never treated as authority. Contradiction must be
    declared in the knowledge graph; otherwise the result is 'unresolved'.
    """
    def __init__(self, knowledge_graph):
        self.graph = knowledge_graph

    def compare(self, rule_id: str, scenario_id: str | None = None) -> Dict[str, Any]:
        related = self.graph.related(rule_id, max_hops=3)
        nodes = {n['id']: n for n in related['nodes']}
        edges = related['edges']
        positions: List[LegalPosition] = []
        for n in nodes.values():
            if n['type'] not in {'jurisprudence','proposition','exception'}:
                continue
            payload = n.get('payload') or {}
            proposition = payload.get('proposition') or payload.get('solution') or n['label']
            kind = 'unverified' if not n.get('verified', False) else 'supported'
            supports = [e['source'] for e in edges if e['target'] == n['id'] and e['relation'] in {'supports','confirms','nuances','distinguishes','contradicts'}]
            confidence = 0.9 if n.get('verified', False) else 0.25
            positions.append(LegalPosition(n['id'], n['label'], kind, proposition, supports, confidence))

        contradictions = []
        nuances = []
        confirmations = []
        for e in edges:
            if e['relation'] == 'contradicts' and e['source'] in nodes and e['target'] in nodes:
                contradictions.append(e)
            elif e['relation'] == 'nuances' and e['source'] in nodes and e['target'] in nodes:
                nuances.append(e)
            elif e['relation'] == 'confirms' and e['source'] in nodes and e['target'] in nodes:
                confirmations.append(e)

        if contradictions:
            status = 'contradicted'
        elif nuances:
            status = 'nuanced'
        elif confirmations:
            status = 'supported'
        else:
            status = 'unresolved'

        labels = {
            'supported': 'Établi / soutenu par les sources reliées',
            'nuanced': 'Nuancé : plusieurs positions ou limites doivent être examinées',
            'contradicted': 'Contradiction explicite dans le graphe',
            'unresolved': 'Non résolu : aucune relation suffisante pour conclure'
        }
        return {
            'rule_id': rule_id,
            'scenario_id': scenario_id,
            'status': status,
            'classification': labels[status],
            'positions': [asdict(p) for p in positions],
            'confirmations': confirmations,
            'nuances': nuances,
            'contradictions': contradictions,
            'human_review_required': status in {'nuanced','contradicted','unresolved'} or any(not p.confidence >= .8 for p in positions),
            'disclaimer': 'Comparaison structurée, non avis juridique. Une relation de similarité ne vaut pas autorité; seules les relations explicites et les sources vérifiées peuvent soutenir une conclusion.'
        }
