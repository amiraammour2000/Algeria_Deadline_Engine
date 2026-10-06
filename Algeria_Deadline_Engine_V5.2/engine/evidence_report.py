from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List, Optional
import json


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    kind: str
    label: str
    source_id: Optional[str] = None
    document_id: Optional[str] = None
    page: Optional[int] = None
    location: Optional[str] = None
    excerpt: Optional[str] = None
    hash: Optional[str] = None
    verified: bool = False


class EvidenceBasedLegalReport:
    """Build an auditable legal analysis from structured evidence.

    The report never upgrades a proposal into a legal fact. Every conclusion
    should be connected to a scenario, rule, source, fact/event and evidence.
    """

    def __init__(self, dossier_id: str, title: str = "Rapport contentieux intelligent"):
        self.dossier_id = dossier_id
        self.title = title
        self.questions: List[Dict[str, Any]] = []
        self.facts: List[Dict[str, Any]] = []
        self.scenarios: List[Dict[str, Any]] = []
        self.computations: List[Dict[str, Any]] = []
        self.conclusions: List[Dict[str, Any]] = []
        self.evidence: List[EvidenceItem] = []
        self.warnings: List[str] = []

    def add_question(self, question_id: str, text: str, status: str = "open") -> None:
        self.questions.append({"id": question_id, "text": text, "status": status})

    def add_fact(self, fact_id: str, label: str, value: Any, *, event_id: Optional[str] = None,
                 document_id: Optional[str] = None, verified: bool = False) -> None:
        self.facts.append({
            "id": fact_id, "label": label, "value": value,
            "event_id": event_id, "document_id": document_id, "verified": verified,
        })

    def add_scenario(self, scenario_id: str, label: str, *, rule_id: Optional[str] = None,
                     source_ids: Optional[List[str]] = None, fact_ids: Optional[List[str]] = None,
                     status: str = "candidate") -> None:
        self.scenarios.append({
            "id": scenario_id, "label": label, "rule_id": rule_id,
            "source_ids": source_ids or [], "fact_ids": fact_ids or [], "status": status,
        })

    def add_computation(self, computation_id: str, *, scenario_id: str, start: Optional[str],
                        end: Optional[str], mode: str, result: str,
                        confidence: float = 0.0) -> None:
        self.computations.append({
            "id": computation_id, "scenario_id": scenario_id, "start": start,
            "end": end, "mode": mode, "result": result, "confidence": confidence,
        })

    def add_evidence(self, evidence: EvidenceItem) -> None:
        self.evidence.append(evidence)

    def add_document_evidence(self, evidence_id: str, document_id: str, label: str,
                              content: bytes, *, page: Optional[int] = None,
                              location: Optional[str] = None, excerpt: Optional[str] = None,
                              verified: bool = True) -> EvidenceItem:
        digest = sha256(content).hexdigest()
        item = EvidenceItem(
            id=evidence_id, kind="document", label=label, document_id=document_id,
            page=page, location=location, excerpt=excerpt, hash=digest, verified=verified,
        )
        self.add_evidence(item)
        return item

    def validate(self) -> Dict[str, Any]:
        ids = {e.id for e in self.evidence}
        scenario_ids = {s["id"] for s in self.scenarios}
        issues: List[str] = []
        for c in self.computations:
            if c["scenario_id"] not in scenario_ids:
                issues.append(f"Calcul {c['id']} référence un scénario absent")
        for s in self.scenarios:
            if not s.get("rule_id"):
                issues.append(f"Scénario {s['id']} sans règle identifiée")
            if not s.get("fact_ids"):
                issues.append(f"Scénario {s['id']} sans faits rattachés")
        if not ids:
            issues.append("Aucune preuve documentaire ou source probante rattachée")
        return {"valid": not issues, "issues": issues}

    def add_conclusion(self, conclusion_id: str, text: str, *, status: str,
                       scenario_ids: List[str], evidence_ids: List[str],
                       human_review_required: bool = True) -> None:
        self.conclusions.append({
            "id": conclusion_id, "text": text, "status": status,
            "scenario_ids": scenario_ids, "evidence_ids": evidence_ids,
            "human_review_required": human_review_required,
        })

    def build(self) -> Dict[str, Any]:
        validation = self.validate()
        if not validation["valid"]:
            self.warnings.extend(validation["issues"])
        payload = {
            "schema": "legal-report.v4.4",
            "dossier_id": self.dossier_id,
            "title": self.title,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "questions": self.questions,
            "facts": self.facts,
            "scenarios": self.scenarios,
            "computations": self.computations,
            "conclusions": self.conclusions,
            "evidence": [asdict(e) for e in self.evidence],
            "warnings": self.warnings,
            "validation": validation,
            "disclaimer": (
                "Rapport d'analyse structurée et traçable; il ne constitue pas un avis juridique "
                "et ne transforme pas automatiquement les propositions extraites des documents en faits juridiques."
            ),
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload["report_hash"] = sha256(canonical.encode("utf-8")).hexdigest()
        return payload

    def to_json(self) -> str:
        return json.dumps(self.build(), ensure_ascii=False, indent=2)
