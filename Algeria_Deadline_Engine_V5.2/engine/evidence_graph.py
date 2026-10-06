from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import uuid

@dataclass
class EvidenceNode:
    id: str
    node_type: str
    label: str
    payload: Dict[str, Any]

@dataclass
class EvidenceEdge:
    id: str
    source: str
    target: str
    relation: str
    confidence: float = 1.0

class EvidenceGraph:
    """Traceability graph: conclusion -> scenario/rule -> fact/event -> document."""
    def __init__(self):
        self.nodes: Dict[str, EvidenceNode] = {}
        self.edges: List[EvidenceEdge] = []

    def node(self, node_type, label, payload=None, node_id=None):
        node_id = node_id or f"{node_type[:3].upper()}-{uuid.uuid4().hex[:10]}"
        self.nodes[node_id] = EvidenceNode(node_id, node_type, label, payload or {})
        return node_id

    def edge(self, source, target, relation, confidence=1.0):
        self.edges.append(EvidenceEdge(f"EDG-{uuid.uuid4().hex[:10]}", source, target, relation, confidence))

    def to_dict(self):
        return {
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }

    def unresolved(self):
        return [
            n.payload.get("message", n.label) for n in self.nodes.values()
            if n.node_type in {"unresolved", "candidate"}
        ]

def build_evidence_graph(case, events, documents, evaluation, ruleset):
    g = EvidenceGraph()
    case_id = g.node("case", case.get("reference", case.get("id", "dossier")), case)
    doc_nodes = {}
    for doc in documents or []:
        doc_nodes[doc["id"]] = g.node("document", doc["filename"], doc, doc["id"])

    event_nodes = {}
    for ev in events or []:
        eid = ev.get("id") or f"EV-{uuid.uuid4().hex[:10]}"
        event_nodes[eid] = g.node("event", ev.get("title", ev.get("event_type", "événement")), ev, eid)
        g.edge(case_id, event_nodes[eid], "contains")
        if ev.get("source_document") and ev["source_document"] in doc_nodes:
            g.edge(event_nodes[eid], doc_nodes[ev["source_document"]], "supported_by")
        if ev.get("effect_status") == "pending_validation":
            uid = g.node("unresolved", f"Qualification à valider: {ev['title']}", {"message": f"{ev.get('event_date', 'date inconnue')} — {ev.get('title', ev.get('event_type', 'événement'))}: effet juridique à valider"})
            g.edge(event_nodes[eid], uid, "requires_validation")

    rule = evaluation.get("rule") or {}
    rule_id = rule.get("id") or evaluation.get("rule_id", "unknown-rule")
    rule_node = g.node("rule", f"Article {rule.get('article', '?')} — {rule.get('title', rule_id)}", rule)
    g.edge(case_id, rule_node, "evaluated_under")
    rs_node = g.node("ruleset", f"{ruleset.get('ruleset_id', '')} v{ruleset.get('ruleset_version', '')}", ruleset)
    g.edge(rule_node, rs_node, "versioned_by")

    scenario_nodes = []
    for sc in evaluation.get("scenarios", []):
        sn = g.node("scenario", sc.get("name", sc.get("rule_id", "scénario")), sc)
        scenario_nodes.append(sn)
        g.edge(rule_node, sn, "candidate_scenario")
        sr = sc.get("rule_id")
        if sr and sr != rule_id:
            rn = g.node("rule", sr, {"id": sr})
            g.edge(sn, rn, "uses_rule")
        for ev in events or []:
            if ev.get("event_type") in {"reclamation", "reponse", "recours", "evenement_interruptif", "evenement_suspensif"}:
                if ev.get("id") in event_nodes:
                    g.edge(sn, event_nodes[ev["id"]], "considers_fact")

    conclusion = g.node("conclusion", f"{evaluation.get('status', 'indeterminate')} — {evaluation.get('deadline', 'sans échéance')}", evaluation)
    g.edge(case_id, conclusion, "produces")
    if scenario_nodes:
        for sn in scenario_nodes:
            g.edge(conclusion, sn, "derived_from", evaluation.get("confidence", 1.0))
    else:
        g.edge(conclusion, rule_node, "derived_from", evaluation.get("confidence", 1.0))
    for ev in events or []:
        if ev.get("event_type") == "notification" and ev.get("id") in event_nodes:
            g.edge(rule_node, event_nodes[ev["id"]], "triggered_by")
    return g.to_dict()
