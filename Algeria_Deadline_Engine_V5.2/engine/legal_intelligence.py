from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import re
from .jurisprudence import JurisprudenceRepository
from .legal_knowledge_graph import LegalKnowledgeGraph

@dataclass
class LegalSource:
    id: str
    source_type: str
    title: str
    citation: str
    url: str = ""
    status: str = "official"
    relevance: float = 1.0

@dataclass
class LegalFinding:
    source_id: str
    kind: str
    proposition: str
    confidence: float
    basis: str

class LegalIntelligence:
    """Deterministic legal-research layer.

    It ranks stored legal sources against the facts/rule metadata. It does not
    invent jurisprudence and never converts a ranked source into a legal conclusion.
    """
    def __init__(self, sources: List[Dict[str, Any]], jurisprudence: List[Dict[str, Any]] | None = None, knowledge_graph: Dict[str, Any] | None = None):
        self.sources = [LegalSource(**s) for s in sources]
        self.jurisprudence = JurisprudenceRepository(jurisprudence or [])
        self.knowledge_graph = LegalKnowledgeGraph((knowledge_graph or {}).get("nodes", []), (knowledge_graph or {}).get("edges", []))

    def find(self, query: str, rule: Dict[str, Any], events: List[Dict[str, Any]]) -> List[LegalFinding]:
        text = " ".join([query or "", rule.get("title", ""), rule.get("article", ""),
                          rule.get("trigger", ""), " ".join(e.get("title", "") for e in events or [])]).lower()
        findings = []
        for s in self.sources:
            hay = f"{s.title} {s.citation}".lower()
            terms = set(re.findall(r"[a-zàâçéèêëîïôûùüÿñæœ0-9-]+", text))
            overlap = sum(1 for t in terms if len(t) > 3 and t in hay)
            article = str(rule.get('article', '')).strip()
            article_hit = bool(article and re.search(rf'\b{re.escape(article)}\b', hay))
            score = min(0.99, s.relevance * (0.65 + 0.08 * overlap)) if (overlap or article_hit) else 0.0
            if score:
                findings.append(LegalFinding(s.id, "source", s.citation, round(score, 2), s.title))
        findings.sort(key=lambda x: x.confidence, reverse=True)
        return findings[:8]

    def explain(self, rule: Dict[str, Any], events: List[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
        findings = self.find(query or rule.get("title", ""), rule, events)
        jurisprudence = self.jurisprudence.search(query or rule.get("title", ""), rule)
        unresolved = []
        if rule.get("requires_human_validation"):
            unresolved.append({"code": "LEGAL_VALIDATION_REQUIRED", "message": "La règle candidate doit être validée au regard des faits et de la version du texte applicable."})
        if any(e.get("effect_status") == "pending_validation" for e in events or []):
            unresolved.append({"code": "EVENT_EFFECT_UNVALIDATED", "message": "Au moins un événement porte un effet juridique non validé."})
        rule_id = rule.get("id", "")
        graph = self.knowledge_graph.related(rule_id, max_hops=2) if rule_id in self.knowledge_graph.nodes else {"root": rule_id, "nodes": [], "edges": []}
        return {
            "sources": [asdict(x) for x in findings],
            "jurisprudence": jurisprudence,
            "knowledge_graph": graph,
            "unresolved": unresolved,
            "disclaimer": "Les sources classées sont des éléments de recherche. Elles ne constituent pas à elles seules une conclusion juridique."
        }
