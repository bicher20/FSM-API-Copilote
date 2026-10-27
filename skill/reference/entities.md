# Schéma de référence — API self-service Nomadia Scheduler

**Source de vérité : le schéma OpenAPI réel qui alimente
https://scheduler-json-api.readme.io/reference/post_schedule et `.../post_geocode`,
récupéré le 26-27/10/2026 et conservé dans `vendor-docs/openapi-schedule.json` et
`vendor-docs/openapi-geocode.json`. Ce fichier en est la transcription lisible.**

> **Pourquoi ce fichier a changé en profondeur le 27/10/2026.** Jusqu'à cette date, ce
> fichier décrivait le schéma d'un document PDF interne Nomadia ("Scheduler Schema
> Documentation", 33 pages) qui s'est révélé décrire l'**offre complète** (avec équipe
> projet Nomadia), pas l'API self-service réellement accessible avec une simple clé.
> Un test réel (payload multi-ressources, `examples/10_job_multi_ressources.json`) a
> donné un résultat qui ne correspondait pas à ce que le PDF décrivait, ce qui a
> déclenché cette vérification. Conséquence concrète : plusieurs mécanismes
> documentés ici avant (job multi-ressources, pièces/stock, ordre entre jobs,
> disponibilité récurrente, horizon de planification borné) **n'existent pas** dans
> l'API self-service — voir `reference/offre-complete-nomadia.md` pour savoir quoi
> dire à un client qui en a besoin.

## Vue d'ensemble

Cinq entités d'entrée, toutes au niveau racine du payload :

| Entité | Clé racine | Obligatoire |
|---|---|---|
| Job | `jobs` | oui |
| ResourceType | `resource_types` | oui |
| Resource | `resources` | oui |
| Location | `locations` | oui |
| JobType | `job_types` | non (peut être `null`) |

Tout le reste (SLA, Shift, Break, disponibilités/indisponibilités) est **imbriqué**
dans l'une de ces cinq entités — il n'y a aucune entité "jointure" séparée au niveau
racine (pas de `job_requirements`, `resource_parts`, `job_resources`, etc.).

**Règle de nommage des identifiants ISO 8601** : dates en `date-time`
(`2026-11-02T08:00:00`), durées en `duration` (`PT30M` = 30 min, `PT1H` = 1h).

**Permissivité observée** : la spec déclare `additionalProperties: false` sur tous
les objets (ce qui devrait rejeter tout champ inconnu avec un 400), mais un test réel
a montré qu'un champ inconnu au niveau racine (`job_resources`) est **silencieusement
ignoré** (HTTP 200, comportement par défaut appliqué) plutôt que de déclencher une
erreur — cohérent avec un désérialiseur runtime permissif (ex: `System.Text.Json` par
défaut en .NET) qui ne respecte pas forcément cette annotation de doc. **Conséquence
pratique : un payload qui "passe" (HTTP 200) ne prouve pas que tous ses champs ont été
pris en compte.** Toujours vérifier dans la réponse que le résultat correspond
réellement à ce qui était demandé.

---

## Job (`jobs[]`)

| Champ | Type | M/O | Notes |
|---|---|---|---|
| `id` | string | **M** | Unique. |
| `job_type_id` | string | **M** | Défaut `"DEFAULT"` si omis dans le JSON envoyé — mais le champ reste requis par le schéma ; utiliser `"DEFAULT"` explicitement si aucun `JobType` réel. |
| `location_id` | string | **M** | Référence un `Location.id`. |
| `sla` | objet `SLA` | **M** | Fenêtre de planification du job (voir plus bas). |
| `appointment_sla` | objet `SLA` | O | Une **deuxième** fenêtre SLA, distincte de `sla` — c'est le mécanisme pour un rendez-vous client avec sa propre tolérance, pas un champ `appointment_sla_id`/`appointment_priority` séparé (cette dernière paire **n'existe pas** dans ce schéma). |
| `fixed_resource_id` | string | O | Id d'une `Resource` à laquelle ce job est "engagé" — le solveur ne peut plus changer la ressource, et planifie le job au plus tôt. **Pas de champ séparé pour forcer une date précise d'engagement** (pas de `commit_date_time_stamp`) — combiner avec `fixed_date_time` si une heure exacte est aussi requise. |
| `fixed_date_time` | date-time | O | Le job doit démarrer exactement à cette date/heure. |
| `custom_duration` | duration | O | Sinon valeur du `job_type`, sinon défaut implicite de l'API. |
| `duration_in_half_days` | integer | O | Alternative à `custom_duration`, en demi-journées. |
| `value_per_hour` | double | O | Valeur/criticité du job pour l'arbitrage du solveur. **⚠️ Aucune valeur par défaut déclarée dans le schéma OpenAPI réel** (`nullable`, pas de `default` — contrairement à l'ancienne doc du skill, issue du PDF offre complète, qui affirmait un défaut de `10000` : ce défaut n'est pas confirmé côté self-service). **Confirmé par test réel le 27/10/2026** : un job sans `value_per_hour` explicite a été planifié 6h30 après sa fenêtre SLA (malgré `base_jeopardy_penalty: 500` et une ressource qualifiée libre dans la fenêtre) — le solveur l'a jugé trop peu rentable pour justifier le coût de respecter la fenêtre. En fixant `value_per_hour` à une valeur haute et explicite sur le même job (toutes choses égales par ailleurs), la fenêtre a été respectée au test suivant. **Toujours fixer `value_per_hour` explicitement si le respect strict d'un SLA ou d'une fenêtre de rendez-vous est important pour le client** — ne jamais compter sur un défaut implicite. Voir `troubleshooting.md` §3bis et `scripts/recommend_improvements.py` (détection automatique de ce cas). |
| `split_allowed` | boolean | O | Le job peut être découpé en **plusieurs visites dans le temps** (ex: sur deux shifts) si sa durée l'exige. **Ne concerne jamais plusieurs ressources simultanées** — voir l'avertissement multi-ressources ci-dessous. |
| `availabilities` | liste de `JobAvailability` | O | Fenêtres où le job **peut** démarrer. |
| `unavailabilities` | liste de `JobUnavailability` | O | Fenêtres où le job **ne peut pas** démarrer (prioritaire sur `availabilities` en cas de recouvrement). |
| `requirements` | liste de **chaînes** | O | Compétences requises — simples chaînes libres, à faire correspondre avec `requirements` côté `Resource`/`ResourceType`/`JobType`. **Pas d'entité `Requirement` séparée avec id.** |

### JobAvailability / JobUnavailability

```json
{ "start_date_time": "2026-11-02T08:00:00", "end_date_time": "2026-11-02T12:00:00" }
```
Juste une fenêtre fixe. **Aucun mécanisme de récurrence** (pas de "tous les lundis") —
pour une disponibilité qui se répète, il faut soit lister chaque occurrence
explicitement, soit faire plusieurs appels, soit passer par l'offre complète (voir
`reference/offre-complete-nomadia.md`).

### SLA (utilisé par `job.sla` et `job.appointment_sla`)

| Champ | Type | M/O |
|---|---|---|
| `earliest_start_date_time` | date-time | **M** |
| `latest_start_date_time` | date-time | **M** |
| `penalty_per_hour` | double | O — pousse à planifier au plus tôt dans la fenêtre |
| `base_jeopardy_penalty` | double | O — pénalité fixe si la fenêtre est ratée ; une valeur supérieure à `value_per_hour` du job peut empêcher l'allocation hors fenêtre |
| `penalty_per_hour_jeopardy` | double | O — pénalité progressive si la fenêtre est ratée (⚠️ la doc officielle déclare une valeur par défaut `"*"` incohérente avec son propre type `number` — ne pas s'y fier, toujours fixer explicitement si utilisé) |

---

## JobType (`job_types[]`, optionnel)

Valeurs par défaut partagées par plusieurs jobs : `id` (**M**), `requirements`,
`custom_duration`, `duration_in_half_days`, `value_per_hour`, `split_allowed` — mêmes
sens que sur `Job`, utilisés si le job ne redéfinit pas sa propre valeur.

---

## Location (`locations[]`)

| Champ | Type | M/O |
|---|---|---|
| `id` | string | **M** |
| `latitude` | double | **M** |
| `longitude` | double | **M** |
| `locality` | string | O — regroupe des locations ; le solveur tente de traiter tous les jobs d'une même `locality` d'un coup |
| `additional_travel_time` | duration | O — s'ajoute à tout trajet vers cette location |

---

## Resource (`resources[]`)

| Champ | Type | M/O | Notes |
|---|---|---|---|
| `id` | string | **M** | |
| `resource_type_id` | string | **M** | Défaut `"DEFAULT"`. |
| `shifts` | liste de `Shift` | O | |
| `unavailabilities` | liste de `ResourceUnavailability` | O | **Imbriquée ici**, pas une entité top-level avec `resource_id` en clé étrangère. |
| `requirements` | liste de chaînes | O | Compétences/habilitations de cette ressource précise. |
| `start_location_id` / `end_location_id` | string | O | Surcharge le `start_location_id`/`end_location_id` du `resource_type` pour cette ressource précise. |

### Shift (`resources[].shifts[]`)

| Champ | Type | M/O |
|---|---|---|
| `start_date_time` | date-time | **M** |
| `end_date_time` | date-time | **M** |
| `breaks` | liste de `Break` | O |
| `start_location_id` / `end_location_id` | string | O — surcharge celle de la `Resource` pour ce shift précis |

### Break (`resources[].shifts[].breaks[]`)

```json
{
  "earliest_start_date_time": "2026-11-02T12:00:00",
  "latest_start_date_time": "2026-11-02T13:00:00",
  "duration": "PT45M"
}
```
Pas de `id` ni de `shift_id` — la pause est entièrement définie par sa position dans
`shift.breaks[]`, inutile d'en ajouter. `fixed_date_time` optionnel si la pause doit
démarrer à une heure précise plutôt que dans une fenêtre.

### ResourceUnavailability (`resources[].unavailabilities[]`)

| Champ | Type | M/O |
|---|---|---|
| `id` | string | **M** |
| `start_date_time` | date-time | **M** |
| `end_date_time` | date-time | **M** |
| `location_id` | string | O |

---

## ResourceType (`resource_types[]`)

| Champ | Type | M/O | Défaut |
|---|---|---|---|
| `id` | string | **M** | |
| `start_location_id` | string | **M** | |
| `end_location_id` | string | **M** | |
| `requirements` | liste de chaînes | O | |
| `cost_per_kilometre` | double | O | `1` |
| `cost_per_hour` | double | O | `1` |
| `maximum_travel_time_from_start_location` | duration | O | |
| `maximum_individual_travel_time` | duration | O | |
| `maximum_travel_time_per_shift` | duration | O | |
| `minimum_jobs_per_shift` | integer | O | |
| `maximum_jobs_per_shift` | integer | O | |
| `pre_shift_travel_period` | duration | O | `PT0S` |
| `post_shift_travel_period` | duration | O | `PT0S` |
| `overtime_period` | duration | O | `PT0S` |
| `overtime_cost_multiplier` | double | O | `5` |
| `shift_penalty` | double | O | `0` — pénalité par shift dès qu'au moins un job y est planifié ; utile pour inciter à concentrer le travail sur moins de ressources/shifts |

---

## Sortie (`POST /schedule`, code 200)

```json
{
  "allocations": [
    { "job_id": "JOB-1", "visits": [
      { "visit_id": 1, "resource_id": "RES-1", "start_date_time": "...", "end_date_time": "..." }
    ]}
  ],
  "travels": [
    { "resource_id": "RES-1", "start_date_time": "...", "end_date_time": "...", "distance_in_metres": 4200, "start_location_id": "DEPOT", "end_location_id": "LOC-1" }
  ],
  "unallocated_job_reasons": [
    { "job_id": "JOB-2", "unallocated_reason": "AllPossibleResourcesFull" }
  ],
  "break_allocations": [
    { "resource_id": "RES-1", "start_date_time": "...", "end_date_time": "..." }
  ]
}
```

**Point important, confirmé par test réel le 26/10/2026** : `allocations[]` est une
liste **par job**, chaque entrée portant une liste `visits[]` (pas une liste plate
`{job_id, resource_id, ...}`). Un job a plusieurs `visits` seulement si `split_allowed`
l'a fait étaler **dans le temps** — jamais plusieurs ressources sur la même visite.
**Il n'y a aucun champ qui permettrait d'exprimer "ce job nécessite 2 ressources en
même temps"** — voir avertissement ci-dessous.

Les raisons possibles de `unallocated_reason` ne sont pas documentées sur cette page
self-service (elles l'étaient dans le PDF de l'offre complète — `NotCalculated`,
`ZeroValue`, `AllPossibleResourcesFull`, etc.). À traiter comme des valeurs probables
mais non garanties tant qu'un test réel n'en a pas confirmé l'exhaustivité côté
self-service.

---

## ⚠️ Mécanismes absents de l'API self-service

Confirmés absents du schéma OpenAPI réel (donc : un payload qui en envoie reçoit un
HTTP 200 mais le mécanisme est **silencieusement ignoré**, pas une erreur) :

- **Job multi-ressources / binôme** (pas de `JobResource`, `resource_index`, ni aucun
  champ "nombre de ressources requises" — `split_allowed` ne concerne que l'étalement
  dans le temps). Confirmé par test réel le 26/10/2026 : deux appels identiques sur un
  job déclaré "binôme" n'ont chacun alloué qu'une seule ressource, sans erreur.
- **Pièces/stock embarqué** (pas de `Part`, `JobResourcePart`, `ResourcePart`).
- **Ordre/dépendance entre jobs** (pas de `PreRequisiteDefinition`).
- **Horizon de planification borné** (pas de `ScheduleDefinition`).
- **Disponibilité récurrente** (pas de pattern "tous les lundis" — seulement des
  fenêtres fixes via `availabilities`/`unavailabilities`).
- **`appointment_priority`** en tant que champ dédié (le besoin métier "rendez-vous
  prioritaire" se couvre avec `appointment_sla` + `base_jeopardy_penalty`, pas avec un
  champ de priorité séparé).

Si le besoin d'un client correspond à l'un de ces points, voir
`reference/offre-complete-nomadia.md` : ne jamais lui dire "impossible" ni essayer de
l'encoder quand même dans le self-service — montrer que Nomadia sait le faire (offre
complète) et orienter vers un contact.
