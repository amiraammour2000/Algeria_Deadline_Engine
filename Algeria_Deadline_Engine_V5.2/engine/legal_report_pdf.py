from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Iterable

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class LegalReportPDF:
    """Render a V4.4 evidence report as an auditable PDF.

    This renderer is deliberately presentation-only: it does not create or
    alter legal conclusions. All legal assertions must already exist in the
    structured report supplied to it.
    """

    def __init__(self, report: Dict[str, Any]):
        self.report = report
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name="ReportTitle", parent=self.styles["Title"], fontSize=20,
            leading=24, alignment=TA_CENTER, spaceAfter=8,
        ))
        self.styles.add(ParagraphStyle(
            name="ReportSubtitle", parent=self.styles["Normal"], fontSize=9,
            leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#555555"),
            spaceAfter=14,
        ))
        self.styles.add(ParagraphStyle(
            name="Section", parent=self.styles["Heading2"], fontSize=13,
            leading=16, spaceBefore=10, spaceAfter=7,
        ))
        self.styles.add(ParagraphStyle(
            name="Small", parent=self.styles["Normal"], fontSize=7.5,
            leading=10,
        ))
        self.styles.add(ParagraphStyle(
            name="Warning", parent=self.styles["Normal"], fontSize=8,
            leading=11, textColor=colors.HexColor("#7a4b00"),
        ))
        self.styles.add(ParagraphStyle(
            name="Conclusion", parent=self.styles["Normal"], fontSize=9,
            leading=13, spaceAfter=5,
        ))

    @staticmethod
    def _p(value: Any, style: str = "Small") -> Paragraph:
        text = "" if value is None else str(value)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(text.replace("\n", "<br/>"), getSampleStyleSheet()[style] if style in getSampleStyleSheet() else getSampleStyleSheet()["Small"])

    def _paragraph(self, value: Any, style: str = "Small") -> Paragraph:
        text = "" if value is None else str(value)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(text.replace("\n", "<br/>"), self.styles[style])

    def _table(self, rows: Iterable[Iterable[Any]], widths=None, header=True) -> Table:
        prepared = []
        for row in rows:
            prepared.append([self._paragraph(x) for x in row])
        table = Table(prepared, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
        commands = [
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8B8B8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if header:
            commands += [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        table.setStyle(TableStyle(commands))
        return table

    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(18 * mm, 10 * mm, f"Dossier {self.report.get('dossier_id', '')} — Rapport V4.5")
        canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def _qr(self) -> Image:
        payload = (
            f"ALG-LEGAL-REPORT-V4.5|DOSSIER:{self.report.get('dossier_id','')}|"
            f"HASH:{self.report.get('report_hash','')}"
        )
        qr = qrcode.make(payload)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)
        return Image(buf, width=30 * mm, height=30 * mm)

    def build(self) -> bytes:
        out = BytesIO()
        doc = SimpleDocTemplate(
            out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=17 * mm, bottomMargin=17 * mm,
            title=self.report.get("title", "Rapport contentieux intelligent"),
            author="Algeria Deadline Engine",
        )
        # Keep page content uncompressed so the embedded integrity hash can be
        # inspected directly in the PDF byte stream by lightweight validators.
        doc.pageCompression = 0
        r = self.report
        story = []

        story += [
            self._paragraph(r.get("title", "Rapport contentieux intelligent"), "ReportTitle"),
            self._paragraph("EVIDENCE-BASED LEGAL REPORT — V4.5", "ReportSubtitle"),
        ]

        meta = [
            ["Dossier", r.get("dossier_id", "")],
            ["Schéma", r.get("schema", "")],
            ["Généré le", r.get("generated_at", "")],
            ["Hash du rapport", r.get("report_hash", "")],
        ]
        story.append(self._table(meta, widths=[42 * mm, 132 * mm], header=False))
        story += [Spacer(1, 7), self._qr(), Spacer(1, 6)]
        story.append(self._paragraph(
            "Ce document restitue une analyse structurée et traçable. Le rendu PDF ne modifie pas les données juridiques du rapport source.",
            "Small",
        ))

        story.append(self._paragraph("1. Questions juridiques", "Section"))
        questions = [["ID", "Question", "Statut"]] + [
            [q.get("id"), q.get("text"), q.get("status")] for q in r.get("questions", [])
        ]
        story.append(self._table(questions or [["—", "Aucune question enregistrée", "—"]], widths=[25*mm, 125*mm, 24*mm]))

        story.append(self._paragraph("2. Faits et événements", "Section"))
        facts = [["ID", "Fait", "Valeur", "Événement", "Vérifié"]] + [
            [f.get("id"), f.get("label"), f.get("value"), f.get("event_id") or "—", "Oui" if f.get("verified") else "Non"]
            for f in r.get("facts", [])
        ]
        story.append(self._table(facts or [["—", "Aucun fait", "—", "—", "—"]], widths=[18*mm, 42*mm, 62*mm, 28*mm, 18*mm]))

        story.append(self._paragraph("3. Scénarios juridiques", "Section"))
        scenarios = [["ID", "Scénario", "Règle", "Faits", "Statut"]] + [
            [s.get("id"), s.get("label"), s.get("rule_id") or "—", ", ".join(s.get("fact_ids") or []) or "—", s.get("status")]
            for s in r.get("scenarios", [])
        ]
        story.append(self._table(scenarios or [["—", "Aucun scénario", "—", "—", "—"]], widths=[18*mm, 65*mm, 38*mm, 35*mm, 18*mm]))

        story.append(PageBreak())
        story.append(self._paragraph("4. Computations / calculs", "Section"))
        computations = [["ID", "Scénario", "Départ", "Fin", "Mode", "Résultat", "Confiance"]] + [
            [c.get("id"), c.get("scenario_id"), c.get("start"), c.get("end"), c.get("mode"), c.get("result"), c.get("confidence")]
            for c in r.get("computations", [])
        ]
        story.append(self._table(computations or [["—", "—", "—", "—", "—", "Aucun calcul", "—"]], widths=[16*mm, 24*mm, 27*mm, 27*mm, 25*mm, 34*mm, 20*mm]))

        story.append(self._paragraph("5. Sources et preuves", "Section"))
        evidence = [["ID", "Type", "Libellé", "Document/source", "Page", "Localisation", "Vérifié", "SHA-256"]] + [
            [e.get("id"), e.get("kind"), e.get("label"), e.get("document_id") or e.get("source_id") or "—",
             e.get("page") or "—", e.get("location") or "—", "Oui" if e.get("verified") else "Non", e.get("hash") or "—"]
            for e in r.get("evidence", [])
        ]
        story.append(self._table(evidence or [["—", "—", "Aucune preuve", "—", "—", "—", "Non", "—"]], widths=[14*mm, 17*mm, 32*mm, 27*mm, 13*mm, 25*mm, 17*mm, 35*mm]))

        story.append(self._paragraph("6. Conclusions", "Section"))
        conclusions = r.get("conclusions", [])
        if conclusions:
            for c in conclusions:
                story.append(KeepTogether([
                    self._paragraph(f"{c.get('id')} — {c.get('status', '')}", "Heading3"),
                    self._paragraph(c.get("text", ""), "Conclusion"),
                    self._paragraph(
                        f"Scénarios : {', '.join(c.get('scenario_ids') or []) or '—'} | "
                        f"Preuves : {', '.join(c.get('evidence_ids') or []) or '—'} | "
                        f"Revue humaine : {'requise' if c.get('human_review_required', True) else 'non requise'}",
                        "Small",
                    ),
                    Spacer(1, 4),
                ]))
        else:
            story.append(self._paragraph("Aucune conclusion enregistrée.", "Warning"))

        story.append(self._paragraph("7. Contrôle de traçabilité", "Section"))
        validation = r.get("validation") or {}
        story.append(self._table([
            ["Contrôle", "Résultat"],
            ["Rapport valide", "OUI" if validation.get("valid") else "NON"],
            ["Nombre d'alertes", len(validation.get("issues") or [])],
            ["Hash SHA-256", r.get("report_hash", "")],
        ], widths=[60*mm, 114*mm]))
        for issue in validation.get("issues") or []:
            story.append(self._paragraph(f"⚠ {issue}", "Warning"))

        story.append(self._paragraph("8. Réserve", "Section"))
        story.append(self._paragraph(r.get("disclaimer", ""), "Warning"))
        story.append(Spacer(1, 8))
        story.append(self._paragraph(
            "Intégrité : le hash SHA-256 permet de vérifier que le contenu structuré ayant servi à produire le rapport n'a pas été modifié. Il ne certifie pas, à lui seul, la véracité matérielle des faits ni l'exactitude d'une qualification juridique.",
            "Small",
        ))

        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)
        return out.getvalue()


def legal_report_pdf(report: Dict[str, Any]) -> bytes:
    return LegalReportPDF(report).build()
