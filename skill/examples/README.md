# Exemples vérifiés

Chaque fichier est un payload complet et valide (passe `scripts/validate_payload.py`
sans erreur), un par pattern courant. Partir d'un de ces fichiers pour construire un
payload réel plutôt que d'écrire à vide — moins de risque d'erreur de structure.

| Fichier | Démontre |
|---|---|
| `01_minimal.json` | le strict nécessaire (2 jobs, 1 ressource) — base de tout payload |
| `02_competence_requise.json` | `Requirement` : un job qui exige une compétence précise |
| `03_stock_pieces.json` | `Part` : un stock embarqué limité qui contraint l'affectation |
| `04_ordre_entre_jobs.json` | `PreRequisiteDefinition` : ordre + même ressource obligatoire |
| `05_disponibilite_recurrente.json` | `JobAvailabilityPattern` + `DayPattern` : dispo récurrente |

Ces fichiers contiennent une clé `_comment` (ignorée par l'API, à retirer avant un vrai
appel) qui explique le pattern démontré.
