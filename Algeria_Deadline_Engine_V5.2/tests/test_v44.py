import json
from engine.evidence_report import EvidenceBasedLegalReport


def test_document_evidence_hash_and_traceability():
    report = EvidenceBasedLegalReport("DOS-001")
    report.add_question("Q1", "La notification déclenche-t-elle le délai ?")
    report.add_fact("F1", "Date notification", "2026-03-01", event_id="EV1", verified=True)
    report.add_scenario("S1", "Point de départ à la notification", rule_id="RULE-ALG-08-09-829", fact_ids=["F1"], status="candidate")
    evidence = report.add_document_evidence("E1", "DOC-1", "Notification", b"notification", page=2)
    report.add_computation("C1", scenario_id="S1", start="2026-03-01", end="2026-04-01", mode="calendar", result="deadline", confidence=.92)
    report.add_conclusion("K1", "Le scénario S1 est calculé comme plausible.", status="candidate", scenario_ids=["S1"], evidence_ids=[evidence.id])
    out = report.build()
    assert out["validation"]["valid"] is True
    assert len(out["report_hash"]) == 64
    assert out["evidence"][0]["hash"] == __import__('hashlib').sha256(b"notification").hexdigest()


def test_missing_rule_and_evidence_are_flagged():
    report = EvidenceBasedLegalReport("DOS-002")
    report.add_scenario("S1", "Scénario incomplet")
    out = report.build()
    assert out["validation"]["valid"] is False
    assert any("règle" in x for x in out["validation"]["issues"])
    assert any("preuve" in x.lower() for x in out["validation"]["issues"])


def test_json_is_serializable():
    report = EvidenceBasedLegalReport("DOS-003")
    report.add_evidence(__import__('engine.evidence_report', fromlist=['EvidenceItem']).EvidenceItem("E", "source", "JO", source_id="SRC", verified=True))
    data = json.loads(report.to_json())
    assert data["schema"] == "legal-report.v4.4"
