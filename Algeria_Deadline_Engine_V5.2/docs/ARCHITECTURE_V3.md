# Architecture V3 — Dossier contentieux intelligent

## 1. Principes

1. **Fact first** : le système conserve les faits et documents sans leur attribuer automatiquement un effet juridique.
2. **Rule first** : toute computation doit identifier une règle, une version de référentiel et une source.
3. **No magic legal effect** : interruption/suspension/forclusion potentielle sont des conclusions conditionnelles, jamais des conséquences d'un simple libellé.
4. **Explainability** : chaque résultat possède une trace lisible.
5. **Reproducibility** : l'entrée, la règle et le résultat sont hashés.
6. **Human validation** : les conditions juridiquement sensibles restent signalées.

## 2. Modèle

- Case
- Event
- Rule
- Fact
- Calculation
- Conflict
- Audit
- Certificate

## 3. Pipeline

```text
Documents / saisie
       ↓
Chronologie factuelle
       ↓
Qualification (règle + conditions)
       ↓
Détection des conflits
       ↓
Computation calendaire
       ↓
Statut + confiance
       ↓
Audit immuable logique
       ↓
Certificat vérifiable
```

## 4. Roadmap V3.1

- stockage des documents et empreintes SHA-256 ;
- extraction OCR assistée avec validation humaine ;
- versioning temporel des règles ;
- calendrier légal multi-années ;
- graphe des actes et dépendances ;
- moteur de scénarios concurrents ;
- authentification et rôles ;
- service public de vérification des certificats ;
- signature électronique selon le cadre réglementaire retenu.
