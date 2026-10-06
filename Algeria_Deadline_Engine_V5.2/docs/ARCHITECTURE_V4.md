# Architecture V4 — Legal Intelligence Layer

V4 ajoute une couche de recherche juridique déterministe au workspace V3.5.

## Principes

1. **Sources d'abord** : seules les sources enregistrées dans `data/legal_sources.json` sont classées.
2. **Pas de jurisprudence inventée** : aucune décision n'est générée si elle n'existe pas dans le registre.
3. **Pas de conclusion automatique** : le classement d'une source ne vaut pas validation juridique.
4. **Traçabilité** : chaque finding contient source, citation, base et score.
5. **Versionnement** : le ruleset reste séparé des sources et de la computation.

## Extension prévue

Le registre peut être étendu avec des décisions de justice vérifiées, doctrine et commentaires, chacun avec identifiant stable, juridiction, date, référence, URL ou pièce source, statut de vérification et empreinte.
