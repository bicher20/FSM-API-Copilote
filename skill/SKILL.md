---
name: nomadia-scheduler-api
description: Référence complète du Scheduler API de Nomadia (optimisation de tournées et planning field service / livraison) — schéma de données, quick start, codes d'erreur, crédits. À utiliser pour répondre à toute question sur comment modéliser des jobs, ressources, contraintes, ou interpréter une réponse de l'API.
version: 1.0
homepage: https://scheduler-json-api.readme.io
---

# Nomadia Scheduler API — Skill de référence

## 1. C'est quoi

Le Scheduler API de Nomadia optimise des plannings de **field service et de livraison** :
on envoie des jobs (interventions/livraisons), des locations (adresses géocodées) et des
resources (techniciens/véhicules + leurs shifts), l'API renvoie le **meilleur plan** :
qui fait quoi, quand, dans quel ordre, avec les trajets associés.

- Endpoint principal : `POST https://scheduler-api.nomadia-app.com/api/schedule`
- Endpoint géocodage : `POST https://scheduler-api.nomadia-app.com/api/geocode`
- Auth : header `x-api-key: YOUR_API_KEY` (clé créée dans le Portail Nomadia Scheduler)
- Appel **synchrone** : le plan optimisé revient directement dans la réponse
- Dates en ISO 8601 (`2026-11-02T08:00:00`), durées en ISO 8601 (`PT30M` = 30 min)
- Les `id` sont fournis par l'appelant et renvoyés tels quels

## 2. Quick start (exemple minimal)

```bash
curl -X POST https://scheduler-api.nomadia-app.com/api/schedule \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "locations": [
      { "id": "DEPOT", "latitude": 48.8566, "longitude": 2.3522 },
      { "id": "LOC-1", "latitude": 48.8738, "longitude": 2.2950 },
      { "id": "LOC-2", "latitude": 48.8462, "longitude": 2.3372 }
    ],
    "job_types": [ { "id": "DEFAULT", "custom_duration": "PT30M" } ],
    "jobs": [
      { "id": "JOB-1", "job_type_id": "DEFAULT", "location_id": "LOC-1",
        "sla": { "earliest_start_date_time": "2026-11-02T08:00:00",
                 "latest_start_date_time":   "2026-11-02T18:00:00" } },
      { "id": "JOB-2", "job_type_id": "DEFAULT", "location_id": "LOC-2",
        "sla": { "earliest_start_date_time": "2026-11-02T08:00:00",
                 "latest_start_date_time":   "2026-11-02T18:00:00" } }
    ],
    "resource_types": [ { "id": "TECH", "start_location_id": "DEPOT", "end_location_id": "DEPOT" } ],
    "resources": [
      { "id": "RES-1", "resource_type_id": "TECH",
        "shifts": [ { "start_date_time": "2026-11-02T08:00:00",
                      "end_date_time":   "2026-11-02T18:00:00" } ] }
    ]
  }'
```

Réponse : `allocations` (qui fait quoi, quand), `travels` (trajets), `unallocated_job_reasons`
(jobs non planifiés + raison), `break_allocations`.

### Géocodage (optionnel)
`POST /api/geocode` avec jusqu'à 100 adresses par appel (`address_line`, `post_code`,
`city`, `country_code`). 1 crédit par lot de 10 adresses envoyées.

### Crédits & erreurs
- Coût d'un appel schedule : **5 crédits + (nb_ressources × nb_jobs planifiés)**. Un appel
  qui ne planifie aucun job coûte 5 crédits.
- `400` requête invalide · `401` clé API manquante/invalide/bloquée · `402` solde de
  crédits négatif · `403` période d'essai terminée (abonnement requis)

## 3. Modèle de données — vue d'ensemble

Le schéma est organisé en 6 modules :

| Module | Couleur (doc) | Contenu |
|---|---|---|
| Général | — | `ScheduleDefinition`, `DeletedEntity`, `Location` |
| Job | Bleu | Ce qui doit être fait : `Job`, `JobType`, `SLA`, `JobResource`, disponibilités |
| Resource | Vert | Qui peut le faire : `Resource`, `ResourceType`, `Shift`, `Break`, indisponibilités |
| Output | Violet | Le plan renvoyé : allocations, trajets, raisons de non-allocation |
| Constraints | Rouge | Contraintes dures : `Requirement` (compétences), `Part` (pièces/stock) |
| Events | Cyan | Événements temps réel : statut de job, position connue d'une ressource |
| Advanced | Jaune | Pré-requis entre jobs, priorité de ressource, découpage de job |

Chaque entité a un `id` (clé primaire, String(32)). M = obligatoire, O = optionnel,
M(valeur) = valeur par défaut si omis.

## 4. Entités générales

**Location** — `id`, `latitude`, `longitude`, `locality` (O, regroupe des lieux : l'API
essaie de faire tous les jobs d'une même localité d'un coup), `additional_travel_time` (O).

**ScheduleDefinition** — `id`, `schedule_window_end_date_time` (O, fin de la fenêtre de
planification — sans ça l'API prend tous les shifts/SLA), `current_date_time` (O, pour
planifier à une date autre que maintenant).

**DeletedEntity** (Input/Output) — sert à signaler qu'une entité a été supprimée dans une
mise à jour incrémentale : `entity_type`, `entity_id1/2/3`.

## 5. Module Job — ce qui doit être fait

**JobType** — gabarit partagé par plusieurs jobs : `id`, `custom_duration` (M, défaut
PT1H), `duration_in_half_days` (O, utilisé seulement si `custom_duration` absent),
`value_per_hour` (M, défaut 10000 — la "valeur"/criticité du job), `split_allowed` (O).

**SLA** — fenêtre de temps dans laquelle un job doit démarrer : `id`,
`earliest_start_date_time` (M), `latest_start_date_time` (M), `penalty_per_hour` (M=0,
pénalité progressive pour planifier tard dans la fenêtre — pousse à planifier tôt),
`base_jeopardy_penalty` (M=0, pénalité one-shot si le SLA est raté — peut empêcher
l'allocation hors SLA si > valeur du job), `penalty_per_hour_jeopardy` (M, pénalité
progressive après le SLA raté).

**Job** — `id`, `job_sla_id` (M, sauf si `appointment_sla_id` fourni), `appointment_sla_id`
(O), `job_type_id` (M, défaut "DEFAULT"), `location_id` (M), `custom_duration` /
`duration_in_half_days` (O, sinon hérité du job_type), `value_per_hour` (O, sinon hérité),
`split_allowed` (O, sinon hérité), `fixed_date_time` (O, démarrage imposé),
`appointment_priority` (M=999, les jobs à valeur plus haute "passent devant" pour les
créneaux de rendez-vous).

**JobResource** — associe un job à une ressource (multi-ressources possible via
`resource_index` différents) : `job_id`, `resource_index` (M=1), `fixed_resource_id` (O,
force la ressource — outrepasse les contraintes dures), `commit_date_time_stamp` (O, job
"committé" = à faire au plus tôt sur la ressource fixée, triés par cette valeur si
plusieurs committés).

**JobAvailability / JobUnavailability** — fenêtres où le job PEUT / NE PEUT PAS démarrer
(`job_id`, `start_date_time`, `end_date_time`). En cas de chevauchement, l'unavailability
gagne.

**JobAvailabilityPattern + DayPattern** — disponibilité récurrente par motif de jours
(cron simplifié `<jour-du-mois> <mois> <jour-de-semaine>`, patterns prédéfinis
`EVERY_DAY`, `MONDAY_TO_THURSDAY`, `MONDAY_TO_FRIDAY`, `MONDAY_TO_SATURDAY`, ou expression
custom avec `*, ?, -, ,, /, L, W, #`).

## 6. Module Resource — qui peut le faire

**ResourceType** — gabarit partagé par plusieurs ressources (ex. "technicien", "camion
3.5T") : `id`, `start_location_id`/`end_location_id` (M), `cost_per_kilometre`/
`cost_per_hour` (M=1), `maximum_travel_time_from_start_location` / `_individual_` /
`_per_shift` (O), `travel_time_multiplier`/`work_time_multiplier` (M=1),
`minimum_jobs_per_shift`/`maximum_jobs_per_shift` (O), `pre_shift_travel_period`/
`post_shift_travel_period` (M=PT0S), `overtime_period` (M=PT0S),
`overtime_cost_multiplier` (M=5), `shift_penalty` (M=0, coût fixe dès qu'un shift a au
moins 1 job — pousse à concentrer le travail sur moins de ressources/shifts).

**Resource** — une ressource précise, hérite de `ResourceType` sauf si surchargé : mêmes
champs que ci-dessus en option, + `id`, `resource_type_id` (M, défaut "DEFAULT").

**Shift** — une journée de travail précise pour une ressource : `id`, `resource_id` (M),
`start_date_time`/`end_date_time` (M), tout le reste hérite de `Resource` si omis.

**Break** — pause dans un shift : `id`, `shift_id` (M), `earliest_start_date_time`/
`latest_start_date_time` (M), `duration` (M=PT1H), `fixed_date_time` (O).

**ResourceUnavailability** — période où une ressource ne peut pas travailler : `id`,
`resource_id` (M), `start_date_time`/`end_date_time` (M), `location_id` (O).

## 7. Module Output — ce que l'API renvoie

| Entité | Rôle |
|---|---|
| `JobResourceAllocation` | quelle ressource fait quel job |
| `JobDateTimeAllocation` | quand (± plusieurs `visit_id` si job découpé) |
| `BreakAllocation` | quand la pause a été planifiée |
| `Travel` | trajets d'une ressource (distance, lieux, horaires) |
| `UnallocatedJobReason` | pourquoi un job n'a pas été planifié (voir §9) |
| `OutputInformation` | métadonnées (type de sortie COMPLETE/UPDATE, ids de changement) |

## 8. Module Constraints — contraintes dures

Deux mécanismes, identiques en structure :

- **Requirement** (compétences/qualifications) : `Requirement` (id) puis
  `JobTypeRequirement` / `JobRequirement` / `JobResourceRequirement` /
  `ResourceTypeRequirement` / `ResourceRequirement` / `ShiftRequirement` — un job ne peut
  être fait que par une ressource ayant TOUS les requirements demandés.
- **Part** (pièces/stock consommé) : `Part` (id) puis `JobTypePart` / `JobPart` /
  `JobResourcePart` (avec `consumption`) côté job, `ResourceTypePart` / `ResourcePart` /
  `ShiftPart` (avec `available_quantity`) côté ressource — chaque job fait consomme du
  stock embarqué, qui doit suffire.

## 9. Raisons de non-allocation (`UnallocatedJobReason`)

`NotCalculated`, `Unknown`, `ZeroValue` (valeur du job = 0), `NoValidTimeWithinSchedulingWindow`,
`NoPossibleResources`, `AllPossibleResourcesFull`, `NoAvailableResourcesMaxTravel`,
`AvailableResourcesLittleTime`, `PossibleResourcesDistant`,
`PossibleResourcesInsufficientParts`, `PossibleResourcesHaveMaxJobs`, `LowValue`,
`JobInvalid`, `MultiResourceJob`, `InvalidFixedJobsInPossibleRoute`,
`CostsOutweighJobValue`, `NoAvailableResourcesMaxTravelInShift`,
`PossibleResourcesNoShiftAtTime`, `ResourceNotPermitted`, `ResourceNotPermittedPreReqs`,
`PreRequisiteJobNotAllocated`, `DependantJobNotAllocated`.

## 10. Module Events — temps réel

**JobResourceStatus** — événements de suivi d'un job : `job_id`, `resource_index`,
`visit_id`, `travel_start_date_time` / `expected_arrival_date_time` / `start_date_time` /
`end_date_time` (tous O) — permet de dire "la ressource est partie", "est arrivée", "a
commencé", "a fini".

**ResourceKnownLocation** — position GPS connue d'une ressource à un instant T
(`resource_id`, `date_time_stamp`, `latitude`, `longitude`) pour réajuster le planning en
temps réel.

## 11. Module Advanced

**PreRequisiteDefinition** — contrainte d'ordre entre 2 jobs : `earlier_job_id`,
`later_job_id`, `minimum_time_difference`/`maximum_time_difference` (O),
`same_resource` (M=false), `all_or_nothing` (M=false, si un des deux ne peut être
planifié, l'autre non plus).

**JobResourcePriority** *(WIP)* — liste de priorité de ressources pour un job :
`MANDATORY` / `FAVOURED` / `UNFAVOURED` / `FORBIDDEN`.

**AllowedSplitPoint** *(WIP)* — points de découpage autorisés pour un job splittable :
`job_id`, `index`, `duration`.

## 12. FAQ rapide

- **Comment forcer un technicien précis sur un job ?** `JobResource.fixed_resource_id`
  (outrepasse les contraintes dures) + éventuellement `commit_date_time_stamp` pour le
  prioriser au plus tôt.
- **Comment grouper les jobs d'un même quartier dans une même tournée ?** donner la même
  `locality` aux `Location` concernées.
- **Comment pénaliser un planning avec trop de shifts "éclatés" ?** `shift_penalty` sur le
  `ResourceType`/`Resource`/`Shift`.
- **Comment gérer une compétence obligatoire (ex. habilitation électrique) ?**
  `Requirement` + `JobRequirement` (ou `JobTypeRequirement`) côté job et
  `ResourceRequirement` côté ressource.
- **Comment gérer un stock de pièces embarqué limité ?** `Part` + `JobPart.consumption`
  côté job et `ResourcePart.available_quantity` côté ressource/shift.
- **Pourquoi un job n'est pas planifié alors qu'une ressource semble libre ?** regarder
  `unallocated_job_reasons` — souvent `NoAvailableResourcesMaxTravel`,
  `PossibleResourcesHaveMaxJobs` ou `CostsOutweighJobValue`.
- **Le planning évolue en temps réel ?** oui, via `ResourceKnownLocation` (position) et
  `JobResourceStatus` (avancement) en entrée, `DeletedEntity` en sortie pour signaler ce
  qui a changé.

## 13. Sources

- Doc schéma complète : PDF "Scheduler Schema Documentation" v1.1.9/1.1.10 (fourni par
  Nomadia)
- Doc API interactive : https://scheduler-json-api.readme.io/reference/quick-start
- Index pour agents IA : https://scheduler-json-api.readme.io/llms.txt
