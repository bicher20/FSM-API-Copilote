# Exemples vérifiés

Les exemples **01, 02, 05, 06, 07, 08, 09** sont des payloads self-service complets
et valides (passent `scripts/validate_payload.py` sans erreur), un par pattern
courant — partir d'un de ces fichiers pour construire un payload réel plutôt que
d'écrire à vide.

Les exemples **03, 04, 10** sont marqués **"offre complète uniquement"** : le
mécanisme qu'ils montrent n'a **aucun équivalent dans l'API self-service**
(confirmé le 27/10/2026 par le schéma OpenAPI réel, voir `reference/entities.md`).
Ils sont volontairement incomplets (pas de `locations`/`resources` etc.) puisqu'ils
ne servent qu'à montrer la forme du payload côté offre complète — **ne jamais les
envoyer à l'API self-service en espérant un vrai résultat**, le mécanisme serait
silencieusement ignoré (HTTP 200 trompeur).

| Fichier | Démontre | Self-service ? |
|---|---|---|
| `01_minimal.json` | le strict nécessaire (2 jobs, 1 ressource) — base de tout payload | ✅ oui |
| `02_competence_requise.json` | `requirements` (liste de chaînes) : un job qui exige une compétence précise | ✅ oui |
| `03_stock_pieces.json` | pièces/stock embarqué (`Part`/`ResourcePart`/`JobResourcePart`) | ❌ offre complète uniquement — voir `reference/offre-complete-nomadia.md` §2 |
| `04_ordre_entre_jobs.json` | ordre entre jobs (`PreRequisiteDefinition`) | ❌ offre complète uniquement — voir `reference/offre-complete-nomadia.md` §3 |
| `05_disponibilite_recurrente.json` | fenêtres de disponibilité **fixes et énumérées** (`job.availabilities[]`) — pas de récurrence possible en self-service | ✅ oui (sans récurrence) |
| `06_ressource_engagee.json` | `fixed_resource_id` directement sur le job : technicien déjà engagé/en route (voir `reference/replanification-temps-reel.md` §1) | ✅ oui |
| `07_pause_obligatoire.json` | `breaks` imbriqué sous `shifts[].breaks[]` : pause déjeuner obligatoire — confirmé par un vrai appel API (HTTP 200) | ✅ oui |
| `08_indisponibilite_ressource.json` | `unavailabilities` imbriqué sous `resources[].unavailabilities[]` : ressource indisponible en milieu de shift | ✅ oui |
| `09_rendez_vous_client.json` | `job.appointment_sla` : deuxième objet SLA imbriqué pour un rendez-vous avec sa propre tolérance | ✅ oui |
| `10_job_multi_ressources.json` | job nécessitant 2 ressources simultanément (binôme) | ❌ offre complète uniquement, **confirmé par test réel** — voir `troubleshooting.md` §4bis et `reference/offre-complete-nomadia.md` §1 |
| `11_scenario_complexe.json` | scénario combiné réaliste (8 jobs, 3 ressources) : compétence, SLA+pénalités, rendez-vous, ressource engagée, indisponibilité, pauses, locality, job splittable, disponibilité limitée | ✅ oui |
| `12_test_controle_sla_value.json` | payload de test minimal ayant permis de confirmer l'absence de défaut de `value_per_hour` (voir `troubleshooting.md` §3bis) — pas un exemple de référence, un test contrôlé | ✅ oui |
| `13_charge_100_jobs.json` | payload de charge (100 jobs, 10 ressources) généré par `scripts/generate_load_test.py`, pour challenger l'API sur le volume. **Coût maximum ≈ 1005 crédits** si tous les jobs sont alloués — ne jamais lancer l'appel réel sans avoir accepté ce coût | ✅ oui |

Les fichiers self-service contiennent une clé `_comment` (ignorée par l'API, à
retirer avant un vrai appel) qui explique le pattern démontré. Les fichiers "offre
complète uniquement" portent un avertissement explicite en `_comment` — toujours le
lire avant de réutiliser ce payload.

## Historique — comment cette distinction a été établie

Jusqu'au 26/10/2026, ces 10 exemples étaient tous construits à partir du PDF interne
"Scheduler Schema Documentation" (33 pages), en supposant qu'il décrivait l'API
self-service accessible avec la clé de test. Un test réel sur l'ancienne version de
`10_job_multi_ressources.json` a donné un résultat suspect (voir
`troubleshooting.md` §4bis) qui a déclenché une vérification croisée : comparaison du
PDF avec le schéma OpenAPI réel qui alimente
`https://scheduler-json-api.readme.io` (récupéré directement via le réseau de la
page, pas la doc rendue — voir `vendor-docs/openapi-schedule.json` et
`vendor-docs/openapi-geocode.json`). Résultat : le PDF décrit l'**offre complète**
Nomadia (équipe projet requise), le schéma OpenAPI réel l'**offre self-service** — ce
que la clé de test donne réellement. Les deux schémas divergent significativement
sur 7 des 10 exemples (02, 03, 04, 05, 06, 08, 09), d'où leur réécriture le
27/10/2026 — voir `CHANGELOG.md`.
