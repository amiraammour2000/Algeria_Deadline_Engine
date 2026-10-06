from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from typing import Any, Dict, List, Optional
import json
from pathlib import Path

@dataclass(frozen=True)
class NormativeVersion:
    id: str
    rule_id: str
    article: str
    title: str
    source_id: str
    publication_date: str
    effective_from: Optional[str]
    effective_to: Optional[str]
    effective_date_status: str
    status: str
    supersedes: List[str]
    amends: List[str]
    notes: str = ""

class LegalVersioningEngine:
    """Version-aware selection of normative rules.

    The engine distinguishes publication from legal effectiveness. A publication
    date is never silently treated as an entry-into-force date. Only records whose
    effective date is explicitly confirmed can be selected automatically.
    Overlaps, gaps, unconfirmed dates, and amendments are surfaced for human review.
    """
    def __init__(self, records: List[Dict[str, Any]], rules_repository=None):
        self.records = [NormativeVersion(**r) for r in records]
        self.rules = rules_repository

    @classmethod
    def from_json(cls, path: str | Path, rules_repository=None):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data.get("versions", data), rules_repository)

    def all(self) -> List[Dict[str, Any]]:
        return [asdict(x) for x in self.records]

    def for_rule(self, rule_id: str) -> List[NormativeVersion]:
        return [x for x in self.records if x.rule_id == rule_id]

    @staticmethod
    def _parse(value: Optional[str]) -> Optional[date]:
        return date.fromisoformat(value) if value else None

    def timeline(self, rule_id: str) -> Dict[str, Any]:
        records = sorted(self.for_rule(rule_id), key=lambda x: (x.effective_from or "9999-12-31", x.publication_date))
        return {
            "rule_id": rule_id,
            "versions": [asdict(x) for x in records],
            "amendments": [
                {"version_id": x.id, "amends": x.amends, "supersedes": x.supersedes}
                for x in records if x.amends or x.supersedes
            ],
            "human_review_required": any(x.effective_date_status != "confirmed" for x in records),
        }

    def applicable(self, rule_id: str, on_date: str, *, require_confirmed=True) -> Dict[str, Any]:
        target = self._parse(on_date)
        if target is None:
            raise ValueError("on_date must be YYYY-MM-DD")
        candidates=[]
        for x in self.for_rule(rule_id):
            start=self._parse(x.effective_from)
            end=self._parse(x.effective_to)
            if require_confirmed and x.effective_date_status != "confirmed":
                continue
            if start and target < start:
                continue
            if end and target > end:
                continue
            candidates.append(x)
        conflicts=[]
        for i,a in enumerate(candidates):
            for b in candidates[i+1:]:
                a_end=self._parse(a.effective_to) or date.max
                b_end=self._parse(b.effective_to) or date.max
                a_start=self._parse(a.effective_from) or date.min
                b_start=self._parse(b.effective_from) or date.min
                if max(a_start,b_start) <= min(a_end,b_end):
                    conflicts.append({"type":"overlap","versions":[a.id,b.id]})
        if len(candidates)==1 and not conflicts:
            selected=candidates[0]
            return {"rule_id":rule_id,"date":on_date,"status":"selected","selected":asdict(selected),"candidates":[asdict(x) for x in candidates],"conflicts":conflicts,"human_review_required":False}
        return {
            "rule_id":rule_id,"date":on_date,
            "status":"unresolved" if not candidates else "conflict",
            "selected":None,
            "candidates":[asdict(x) for x in candidates],
            "conflicts":conflicts,
            "human_review_required":True,
            "reason":"Aucun texte à effet confirmé ne couvre la date, ou plusieurs versions se chevauchent. La date d'entrée en vigueur doit être vérifiée humainement."
        }

    def applicability_matrix(self, rule_ids: List[str], dates: List[str]) -> List[Dict[str, Any]]:
        return [self.applicable(r, d) for r in rule_ids for d in dates]
