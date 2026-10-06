from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import hashlib
import json
import re
import urllib.request

@dataclass(frozen=True)
class SourceRecord:
    id: str
    source_type: str
    title: str
    citation: str
    url: str
    status: str
    relevance: float = 0.0
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    verified_at: Optional[str] = None
    version: Optional[str] = None

class LegalResearchEngine:
    """Deterministic legal-source research layer.

    It searches only registered sources and known rules/jurisprudence. A match is
    a research lead, never legal authority by similarity alone. Optional URL
    verification records only HTTP metadata and a content hash; it never silently
    changes the legal database.
    """
    def __init__(self, sources: List[Dict[str, Any]], rules_repository=None, jurisprudence=None):
        self.sources = [SourceRecord(**{k: s.get(k) for k in SourceRecord.__dataclass_fields__}) for s in sources]
        self.rules = rules_repository
        self.jurisprudence = jurisprudence or []

    @staticmethod
    def _tokens(text: str) -> set[str]:
        # \w is Unicode-aware in Python; this safely covers FR/AR/EN.
        return {x.lower() for x in re.findall(r"\w{2,}", text or "", flags=re.UNICODE)}

    def search(self, query: str, rule_id: Optional[str] = None, language: str = "fr") -> Dict[str, Any]:
        q = self._tokens(query)
        results=[]
        selected = self.rules.get(rule_id) if rule_id and self.rules else None
        if selected:
            rule_text = json.dumps(selected, ensure_ascii=False)
            q |= self._tokens(rule_text)
        for s in self.sources:
            text = f"{s.title} {s.citation} {s.source_type}"
            overlap = len(q & self._tokens(text))
            if overlap or (selected and s.source_type == 'statute'):
                score = min(1.0, s.relevance * (0.35 + overlap / max(1, len(q))))
                results.append({'kind':'source','id':s.id,'title':s.title,'citation':s.citation,'url':s.url,'status':s.status,'score':round(score,4),'version':s.version,'effective_from':s.effective_from,'effective_to':s.effective_to})
        for j in self.jurisprudence:
            text=json.dumps(j,ensure_ascii=False)
            overlap=len(q & self._tokens(text))
            if overlap:
                results.append({'kind':'jurisprudence','id':j.get('id'),'title':j.get('title'),'citation':j.get('reference'),'url':j.get('source_url') or j.get('url'),'status':'verified' if j.get('verified') else 'unverified','score':round(overlap/max(1,len(q)),4),'version':None,'effective_from':None,'effective_to':None})
        results.sort(key=lambda x:(x['score'], x['status']=='verified', x['kind']=='source'), reverse=True)
        return {'schema':'legal-research/v1','query':query,'rule_id':rule_id,'language':language,'results':results,'human_review_required':True,'disclaimer':'Résultat de recherche documentaire. La pertinence ou la similarité ne constitue pas une autorité juridique; les sources doivent être vérifiées et la version applicable confirmée.'}

    def sources_for_rule(self, rule_id: str) -> List[Dict[str, Any]]:
        if not self.rules: return []
        rule=self.rules.get(rule_id)
        text=f"{rule.get('article','')} {rule.get('title','')}"
        return self.search(text, rule_id)['results']

    def verify_url(self, source_id: str, timeout: int = 10) -> Dict[str, Any]:
        source=next((s for s in self.sources if s.id==source_id), None)
        if not source: raise KeyError(source_id)
        parsed=urlparse(source.url)
        if parsed.scheme not in {'http','https'}: raise ValueError('Unsupported URL scheme')
        req=urllib.request.Request(source.url, headers={'User-Agent':'AlgeriaLegalCaseWorkspace/4.9'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data=r.read()
                return {'id':source.id,'url':source.url,'http_status':getattr(r,'status',200),'content_type':r.headers.get('Content-Type'),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'verified_transport':200 <= getattr(r,'status',200) < 400}
        except Exception as exc:
            return {'id':source.id,'url':source.url,'verified_transport':False,'error':f'{type(exc).__name__}: {exc}'}
