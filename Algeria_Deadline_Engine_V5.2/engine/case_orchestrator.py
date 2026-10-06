from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from typing import Any, Dict, List, Optional
import hashlib, json

@dataclass(frozen=True)
class OrchestrationResult:
    schema: str
    case_id: str
    generated_at: str
    rule_id: Optional[str]
    version_status: str
    qualification_status: str
    research_count: int
    evaluation_status: str
    conclusion_status: str
    readiness: str
    blockers: List[str]
    warnings: List[str]
    trace: List[Dict[str, Any]]
    snapshot_hash: str

class LegalCaseOrchestrator:
    """Central, auditable orchestration layer for a legal case.

    It coordinates facts, documents, qualification, source research, normative
    versioning, deadline evaluation, comparison and reporting. It never upgrades
    a candidate into a legal conclusion. Readiness is a workflow state, not legal
    advice or a finding of liability/forfeiture.
    """
    def __init__(self, *, rules, engine, qualifier, research, versioning, comparator):
        self.rules = rules
        self.engine = engine
        self.qualifier = qualifier
        self.research = research
        self.versioning = versioning
        self.comparator = comparator

    @staticmethod
    def _json_hash(payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def run(self, *, case: Dict[str, Any], events: List[Dict[str, Any]], documents: List[Dict[str, Any]],
            rule_id: Optional[str], facts: Dict[str, Any], today: Optional[date] = None) -> Dict[str, Any]:
        today = today or date.today()
        trace: List[Dict[str, Any]] = []
        blockers: List[str] = []
        warnings: List[str] = []

        trace.append({"step": 1, "type": "facts", "message": f"{len(events)} événement(s), {len(documents)} pièce(s) enregistrés."})
        qualification = self.qualifier.qualify(events, documents, rule_id)
        trace.append({"step": 2, "type": "qualification", "message": f"{qualification['candidate_count']} qualification(s) candidate(s)."})
        if qualification.get("global_missing"):
            warnings.extend(qualification["global_missing"])

        version = {"status": "unresolved", "human_review_required": True, "selected": None}
        if rule_id:
            start_date = facts.get("start_date") or today.isoformat()
            version = self.versioning.applicable(rule_id, start_date)
            trace.append({"step": 3, "type": "normative_version", "message": f"Versioning: {version['status']} pour {rule_id} à {start_date}."})
            if version.get("human_review_required"):
                blockers.append("La version normative applicable n'est pas suffisamment établie.")
        else:
            blockers.append("Aucune règle juridique n'a été sélectionnée.")
            trace.append({"step": 3, "type": "normative_version", "message": "Aucune règle sélectionnée."})

        research_result = self.research.search(
            query=f"{rule_id or ''} {facts.get('question','')}", rule_id=rule_id, language=facts.get("language", "fr")
        )
        trace.append({"step": 4, "type": "research", "message": f"{len(research_result['results'])} résultat(s) de recherche enregistrés."})
        if not research_result["results"]:
            warnings.append("Aucune source enregistrée ne correspond à la recherche contextualisée.")

        evaluation = None
        if rule_id:
            evaluation = self.engine.evaluate(rule_id, facts, events, today=today, documents=documents, case=case)
            trace.append({"step": 5, "type": "computation", "message": f"Calcul: {evaluation.get('status', 'indeterminate')}."})
            if evaluation.get("status") == "indeterminate":
                blockers.append("Le calcul du délai reste indéterminé.")
            for c in evaluation.get("conflicts", []):
                if c.get("severity") in {"blocking", "high"}:
                    blockers.append(c.get("message", "Conflit juridique bloquant."))
                elif c.get("severity") == "warning":
                    warnings.append(c.get("message", "Avertissement."))

        comparison = self.comparator.compare(rule_id) if rule_id else {"status":"unresolved", "human_review_required":True, "classification":"Aucune règle sélectionnée."}
        trace.append({"step": 6, "type": "comparison", "message": comparison.get("classification", "Comparaison non résolue.")})
        if comparison.get("human_review_required"):
            warnings.append("La comparaison juridique nécessite une revue humaine.")

        validated_events = sum(e.get("effect_status") == "validated" for e in events)
        pending_events = len(events) - validated_events
        if pending_events:
            blockers.append(f"{pending_events} événement(s) attend(ent) encore une validation juridique.")

        unanalyzed_docs = sum(d.get("extraction_status", "not_analyzed") == "not_analyzed" for d in documents)
        if unanalyzed_docs:
            warnings.append(f"{unanalyzed_docs} pièce(s) n'ont pas encore été analysées par l'intelligence documentaire.")

        if not events:
            blockers.append("Aucun événement n'est enregistré dans le dossier.")
        if not documents:
            warnings.append("Aucune pièce n'est rattachée au dossier.")

        if blockers:
            readiness = "blocked"
        elif warnings:
            readiness = "review"
        else:
            readiness = "ready_for_human_review"

        conclusion_status = "candidate" if evaluation else "not_available"
        result = {
            "schema": "legal-case-orchestration/v1",
            "case_id": str(case["id"]),
            "generated_at": date.today().isoformat(),
            "rule_id": rule_id,
            "facts": facts,
            "validated_events": validated_events,
            "pending_events": pending_events,
            "qualification": qualification,
            "version": version,
            "research": research_result,
            "evaluation": evaluation,
            "comparison": comparison,
            "conclusion": {"status": conclusion_status, "human_review_required": True},
            "readiness": readiness,
            "blockers": list(dict.fromkeys(blockers)),
            "warnings": list(dict.fromkeys(warnings)),
            "trace": trace,
            "disclaimer": "Orchestration de dossier et aide au raisonnement uniquement. La disponibilité d'un calcul ou d'une source ne constitue pas un avis juridique, une décision ou une conclusion définitive.",
        }
        result["snapshot_hash"] = self._json_hash(result)
        return result
