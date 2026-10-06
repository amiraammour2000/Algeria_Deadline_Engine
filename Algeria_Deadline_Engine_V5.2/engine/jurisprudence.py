from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import re

@dataclass
class JurisprudenceRecord:
    id: str
    court: str
    chamber: str
    date: str
    reference: str
    title: str
    question: str
    solution: str
    legal_basis: List[str]
    source_url: str
    source_status: str = 'official_portal'
    verified: bool = False
    notes: str = ''

class JurisprudenceRepository:
    def __init__(self, records: List[Dict[str, Any]]):
        self.records = [JurisprudenceRecord(**r) for r in records]

    def all(self):
        return self.records

    def get(self, record_id):
        for r in self.records:
            if r.id == record_id:
                return r
        raise KeyError(record_id)

    def search(self, query: str = '', rule: Dict[str, Any] | None = None, limit: int = 10):
        rule = rule or {}
        terms = set(re.findall(r"[a-zàâçéèêëîïôûùüÿñæœ0-9-]+", (query + ' ' + rule.get('title','') + ' ' + str(rule.get('article',''))).lower()))
        out=[]
        for r in self.records:
            hay=' '.join([r.title,r.question,r.solution,r.court,r.reference,' '.join(r.legal_basis)]).lower()
            overlap=sum(1 for t in terms if len(t)>3 and t in hay)
            article_hit=any(str(rule.get('article','')).strip() == str(x).strip() for x in r.legal_basis) if rule.get('article') else False
            score=min(0.99, 0.25 + 0.12*overlap + (0.35 if article_hit else 0)) if overlap or article_hit else 0
            if score:
                out.append((round(score,2),r))
        out.sort(key=lambda x:x[0], reverse=True)
        return [dict(score=s, record=asdict(r)) for s,r in out[:limit]]
