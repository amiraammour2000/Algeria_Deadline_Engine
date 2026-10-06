# Algeria Deadline Engine — V3.4

## Evidence Graph / Legal Reasoning Graph

V3.4 adds a deterministic traceability graph linking:

`Conclusion → Scenario → Rule → Event/Fact → Document`

and the versioned ruleset:

`Rule → Ruleset`

An event whose legal effect is still pending validation creates an explicit `unresolved` node. The graph never upgrades an extracted fact into a legally validated fact by itself.

## Design principles

1. **Facts and legal qualification are separate.**
2. **Every sensitive legal effect needs a rule and validation state.**
3. **A conclusion can have several concurrent scenarios.**
4. **Evidence is traceable to its source document and SHA-256.**
5. **The ruleset version is part of the reasoning graph and audit.**
6. **No silent calendar adjustment is applied without an explicit rule.**

## Current normative baseline

The prototype references the official Algerian sources for Law 08-09 and Law 22-13. The current engine treats the legal ruleset as `prototype_juridique_a_valider`; it is not a substitute for legal review.
