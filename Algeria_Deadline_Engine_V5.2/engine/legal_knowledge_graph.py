from dataclasses import dataclass, asdict
from typing import Any, Dict, List

@dataclass(frozen=True)
class KnowledgeNode:
    id: str
    type: str
    label: str
    verified: bool = True
    payload: Dict[str, Any] | None = None

@dataclass(frozen=True)
class KnowledgeEdge:
    source: str
    target: str
    relation: str
    confidence: float = 1.0
    basis: str = ""

class LegalKnowledgeGraph:
    """Small, deterministic knowledge graph for legal sources.

    It deliberately models *relations* between sources and propositions rather than
    treating similarity as legal authority. Unverified jurisprudence remains isolated
    from verified conclusions.
    """
    def __init__(self, nodes: List[Dict[str, Any]] | None = None, edges: List[Dict[str, Any]] | None = None):
        self.nodes = {n['id']: KnowledgeNode(**n) for n in (nodes or [])}
        self.edges = [KnowledgeEdge(**e) for e in (edges or [])]

    def add_node(self, node: KnowledgeNode):
        self.nodes[node.id] = node

    def add_edge(self, edge: KnowledgeEdge):
        self.edges.append(edge)

    def neighbors(self, node_id: str, relation: str | None = None) -> List[KnowledgeNode]:
        ids = [e.target for e in self.edges if e.source == node_id and (relation is None or e.relation == relation)]
        return [self.nodes[i] for i in ids if i in self.nodes]

    def related(self, source_id: str, max_hops: int = 2) -> Dict[str, Any]:
        seen = {source_id}
        frontier = [source_id]
        paths = []
        for _ in range(max_hops):
            nxt = []
            for src in frontier:
                for e in self.edges:
                    if e.source == src and e.target not in seen:
                        seen.add(e.target); nxt.append(e.target)
                        paths.append(asdict(e))
            frontier = nxt
            if not frontier:
                break
        return {
            'root': source_id,
            'nodes': [asdict(self.nodes[i]) for i in seen if i in self.nodes],
            'edges': paths,
        }

    def candidates_for_rule(self, rule_id: str, max_hops: int = 2) -> List[Dict[str, Any]]:
        result = self.related(rule_id, max_hops)
        out=[]
        for n in result['nodes']:
            if n['type'] in {'jurisprudence','source','proposition','exception'}:
                out.append(n)
        return out
