# Architecture V4.2 — Legal Knowledge Graph

La V4.2 relie les règles, sources normatives, propositions et jurisprudence dans un graphe explicite.

Principes :
- une relation n'est pas une conclusion juridique ;
- une jurisprudence non vérifiée reste `verified=false` ;
- les sources officielles sont séparées des faits du dossier ;
- chaque réponse de recherche expose sa trace de graphe ;
- aucune décision n'est inventée pour compléter le graphe.

Chaîne :
`règle -> source normative -> jurisprudence/proposition -> fait -> conclusion`.
