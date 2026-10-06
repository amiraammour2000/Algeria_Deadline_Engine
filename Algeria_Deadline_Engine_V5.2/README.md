# Algeria Legal Case Workspace — V5.1

## Central Legal Case Orchestration

V5.1 transforme le projet en plateforme de **gestion et raisonnement de dossier juridique auditable**.

### Chaîne centrale

Dossier → faits/événements → pièces → qualification assistée → recherche juridique → version normative → calcul des délais → comparaison juridique → état de readiness → rapport/audit.

### Fonctionnalités

- interface Streamlit professionnelle FR / AR (RTL) / EN ;
- gestion des dossiers et chronologie ;
- documents PDF/DOCX/images/TXT et OCR multilingue ;
- propositions documentaires `candidate` puis validation humaine ;
- qualification juridique assistée ;
- recherche structurée dans les sources enregistrées et la jurisprudence ;
- séparation des sources vérifiées et non vérifiées ;
- Legal Knowledge Graph et comparateur juridique ;
- versionnement normatif et applicabilité temporelle ;
- calcul des délais et détection des conflits ;
- Evidence Graph et rapport juridique PDF ;
- audit et hashes d'intégrité ;
- **nouvelle couche V5.1 : LegalCaseOrchestrator**, qui exécute le workflow complet et calcule un état : `blocked`, `review` ou `ready_for_human_review` ;
- persistance des snapshots d'orchestration dans SQLite.

### Principe de sécurité juridique

Le système ne transforme pas une similarité, une extraction OCR, une jurisprudence non vérifiée, une date de publication ou un calcul isolé en conclusion juridique automatique. Les situations incomplètes ou conflictuelles sont remontées comme blocages/avertissements et restent soumises à revue humaine.

### Lancement

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

### Tests

```bash
pytest -q
python -m compileall -q engine app certificates
```

V5.1 ajoute notamment `engine/case_orchestrator.py` et `tests/test_v51.py`.

## V5.2 — Production / Enterprise Foundation
- RBAC roles: admin, lawyer, reviewer, assistant, auditor
- PBKDF2-SHA256 password hashing
- per-case permissions / ACL
- tamper-evident security audit chain
- organization and user management
- case backup ZIP export
- enterprise administration UI in FR/AR/EN
- Arabic RTL preserved

Security design follows a least-privilege and audit-first approach. This is an application foundation, not a certification of legal/security compliance.
