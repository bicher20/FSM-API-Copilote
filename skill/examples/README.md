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
| `06_ressource_engagee.json` | `JobResource.fixed_resource_id` + `commit_date_time_stamp` : technicien déjà en route (voir `reference/replanification-temps-reel.md` §1) |
| `07_pause_obligatoire.json` | `Break` : pause déjeuner obligatoire dans un shift |
| `08_indisponibilite_ressource.json` | `ResourceUnavailability` : ressource indisponible en milieu de shift |
| `09_rendez_vous_client.json` | `appointment_sla_id` + `appointment_priority` : rendez-vous client prioritaire vs job normal |
| `10_job_multi_ressources.json` | `JobResource.resource_index` : job nécessitant 2 ressources simultanément (binôme) — **⚠️ comportement non confirmé par l'API en test, voir `troubleshooting.md` §4bis** |

Ces fichiers contiennent une clé `_comment` (ignorée par l'API, à retirer avant un vrai
appel) qui explique le pattern démontré.

## Note de fiabilité — conventions confirmées / restant à confirmer

- Les `shifts` imbriqués sous `resources[].shifts[]` : **confirmé** (quick start
  officiel + tests réels).
- Les `breaks` imbriqués sous `shifts[].breaks[]` : **confirmé par un vrai appel API**
  (23/10/2026, `07_pause_obligatoire.json` → HTTP 200, `break_allocations` rempli avec
  la pause de 12:00-12:45 demandée). `validate_payload.py` continue d'accepter aussi un
  `breaks[]` top-level avec `shift_id` par tolérance, mais la convention imbriquée est
  désormais la référence.
- Le nom de clé racine pour `JobResource` reste supposé `job_resources` (pluriel, par
  analogie avec `job_requirements`/`job_parts`) — **non confirmé**.
- **Testé en conditions réelles le 26/10/2026, résultat suspect** : deux appels
  identiques sur `10_job_multi_ressources.json` n'ont chacun alloué qu'**une seule**
  ressource au job (jamais les deux ensemble), sans erreur ni `unallocated_job_reasons`
  — comme si `job_resources` était ignoré. Pas encore de réponse Nomadia pour trancher
  entre "clé mal nommée", "limite de l'environnement de test", ou "champ manquant".
  Détail complet dans `troubleshooting.md` §4bis.

À corriger dans ce fichier et dans `validate_payload.py`/`recommend_improvements.py` dès
qu'un vrai appel API confirme (ou infirme) ce dernier point, ou dès que Nomadia répond
— voir `FEEDBACK.md`.
