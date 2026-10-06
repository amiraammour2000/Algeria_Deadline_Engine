from engine.evidence_report import EvidenceBasedLegalReport
from engine.legal_report_pdf import legal_report_pdf


def sample_report():
    report = EvidenceBasedLegalReport("DOS-V45", "Rapport de test V4.5")
    report.add_question("Q1", "Le délai est-il expiré ?")
    report.add_fact("F1", "Date de notification", "2026-03-01", event_id="EV1", verified=True)
    report.add_scenario("S1", "Calcul à partir de la notification", rule_id="RULE-ALG-08-09-829", fact_ids=["F1"])
    ev = report.add_document_evidence("E1", "DOC-1", "Notification", b"preuve", page=3, location="page 3 / date", verified=True)
    report.add_computation("C1", scenario_id="S1", start="2026-03-01", end="2026-04-01", mode="calendar", result="deadline", confidence=.94)
    report.add_conclusion("K1", "Le calcul du scénario est traçable.", status="candidate", scenario_ids=["S1"], evidence_ids=[ev.id])
    return report.build()


def test_pdf_generation_returns_valid_pdf_bytes():
    pdf = legal_report_pdf(sample_report())
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2500


def test_pdf_contains_report_hash():
    report = sample_report()
    pdf = legal_report_pdf(report)
    assert report["report_hash"].encode() in pdf
