---
name: nomadia-scheduler-api
description: Copilote pour le Scheduler API de Nomadia (optimisation de tournées et planning field service / livraison). Cadre le besoin de l'utilisateur, inspecte son projet existant, puis implémente l'intégration — modélisation des jobs/ressources/contraintes, appels API, débogage d'une réponse. À utiliser dès qu'il est question de planifier des tournées/interventions, d'intégrer ou de déboguer le Scheduler API de Nomadia.
version: 1.13
homepage: https://scheduler-json-api.readme.io
---

# Nomadia Scheduler API — Copilote d'intégration

> **Agent-agnostique.** Ce fichier est du Markdown simple + des fichiers plats
> (`reference/`, `examples/`, `scripts/`, `snippets/`) — aucune instruction ci-dessous ne
> dépend d'un agent IA précis. Que tu sois Claude Code, Cursor, GitHub Copilot agent, un
> agent LLM custom ou autre, tant que tu as accès à (a) lire des fichiers et (b) exécuter
> des commandes shell (terminal, sous-processus, peu importe le nom de l'outil), tu peux
> suivre cette procédure à la lettre. Partout où il est écrit "exécute via ton outil
> d'exécution de commandes", comprends : utilise le mécanisme d'exécution shell dont tu
> disposes, quel qu'il soit — jamais besoin de demander à l'utilisateur de le lancer à ta
> place.

## -1. Premier contact — si l'utilisateur ne sait pas par où commencer

Si l'utilisateur invoque ce skill sans objectif clair ("c'est quoi ce truc", "comment
ça marche", ou juste un message vague), ne lui demande pas de reformuler : présente en
3-4 lignes ce que ce skill sait faire concrètement, puis propose directement une
première action plutôt que d'attendre une réponse parfaite :

> Je suis le copilote d'intégration du Scheduler API de Nomadia (planning de tournées
> field service/livraison). Je peux : cadrer ton besoin et te dire quels mécanismes
> activer, écrire le payload/code d'intégration, valider et diagnostiquer automatiquement
> avant tout appel réel, et traduire les résultats en chiffres business (taux
> d'allocation, trajet, ROI). As-tu déjà une intégration en cours, ou on démarre de zéro ?

Ne jamais laisser l'utilisateur deviner quel fichier ouvrir ou quel script lancer —
c'est le rôle du skill de le faire à sa place (voir §-1bis et §0).

**Si l'utilisateur vient de recevoir ce skill pour la première fois** (installation,
configuration de la clé API, premier test) : suis directement `ONBOARDING.md` plutôt
que de réexpliquer chaque étape depuis zéro — il couvre installation → clé API →
premier test sans crédits → premier vrai appel → où aller ensuite.

## -1bis. Une seule commande pour tout vérifier

Pour tout payload déjà écrit, le réflexe par défaut est **une seule commande** plutôt
que de se souvenir de trois scripts séparés :

```bash
python3 <chemin-du-skill>/scripts/doctor.py payload.json
python3 <chemin-du-skill>/scripts/doctor.py payload.json --response reponse.json   # après un vrai appel
```

`doctor.py` valide (bloquant si erreur), puis recommande (ROI, jamais bloquant), dans
le bon ordre, en un seul appel. Les sections 3.4/4bis de l'étape 0 ci-dessous détaillent
ce qu'il fait exactement et quand utiliser les scripts séparés
(`validate_payload.py`/`recommend_improvements.py`/`compare_scenarios.py`) plutôt que
`doctor.py` — en général seulement si besoin d'automatiser juste l'un des deux.

## 0. Procédure à suivre quand ce skill est invoqué

Ce skill ne sert pas qu'à répondre à une question ponctuelle : quand il est déclenché,
comporte-toi comme un copilote qui cadre le besoin puis exécute. Ne te contente jamais de
renvoyer un extrait de la doc (§1-13) sans d'abord savoir ce que l'utilisateur construit.

**Étape 1 — Regarder avant de demander.** Si le skill tourne dans un contexte de code
(repo ouvert, fichiers accessibles), inspecte d'abord ce qui existe déjà avant de poser
la moindre question :
- cherche un appel existant vers `scheduler-api-test.nomadia-app.com` /
  `scheduler-api.nomadia-app.com` ou `nomadia` dans le code (grep large : `nomadia`,
  `x-api-key`, `/api/schedule`, `/api/geocode`) — voir ONBOARDING.md §0 sur les deux
  environnements avant de supposer lequel le projet cible
- cherche une clé API déjà configurée (`.env`, `.env.example`, variables `NOMADIA_*`,
  secrets du projet) — ne jamais redemander une info déjà visible dans le repo
- identifie le stack (package.json / requirements.txt / composer.json / etc.) pour écrire
  du code dans le bon langage/framework dès le départ
- repère le modèle de données déjà en place côté utilisateur (sa table "interventions",
  ses "techniciens", etc.) pour savoir comment ça va se mapper sur Job/Resource/Shift

**Étape 2 — Ne poser QUE les questions dont la réponse n'est pas déductible.** Une seule
série groupée de questions (pas un interrogatoire pas à pas), et seulement sur ce que
l'inspection n'a pas révélé :
1. Quel est l'objectif concret ? (brancher le scheduler sur une appli existante, débugger
   un appel qui échoue/planifie mal, modéliser un cas métier spécifique pour un client,
   comparer un plan produit vs un plan attendu…)
2. As-tu déjà une clé API Nomadia active (essai ou abonnement) ?
3. C'est quoi le métier modélisé : quels types d'interventions, quelles ressources
   (techniciens/véhicules), et y a-t-il des contraintes dures (compétences obligatoires,
   stock de pièces embarqué, ordre entre jobs) ? — ne demande que ce qui manque encore
   après l'étape 1.

Si l'objectif est déjà clair depuis le message de l'utilisateur ou le contexte du repo,
**saute directement à l'étape 3** sans poser de question pour la forme.

**Étape 2bis — Mapper l'objectif client à la configuration à activer.** Dès que
l'objectif métier est connu, traduis-le immédiatement en mécanismes Nomadia concrets à
activer — ne laisse jamais l'utilisateur deviner quelle case cocher :

| Objectif client | Mécanismes à activer | Pourquoi (ROI) |
|---|---|---|
| Respecter des rendez-vous/fenêtres client stricts | `SLA` avec `penalty_per_hour`/`base_jeopardy_penalty` > 0 | évite le risque réputationnel d'un rdv raté — kpis-metier.md §3 |
| Technicien avec habilitation/compétence obligatoire | `Requirement` + `JobRequirement`/`ResourceRequirement` | évite d'envoyer la mauvaise ressource — kpis-metier.md §1 |
| Stock embarqué limité (pièces, matériel) | `Part` + `JobPart.consumption` + `ResourcePart.available_quantity` | évite une tournée bloquée par manque de stock |
| Réduire les km/le temps de trajet | `locality` sur les `Location` + revoir `start_location_id`/`end_location_id` | argument ROI le plus direct — kpis-metier.md §2 |
| Limiter le nombre de véhicules/techniciens mobilisés | `shift_penalty` > 0 | baisse du coût fixe journalier — kpis-metier.md §4 |
| Ordre obligatoire entre deux interventions | `PreRequisiteDefinition` | évite un plan métier incohérent (ex: poser avant de câbler) |
| Disponibilité récurrente (horaires fixes chaque semaine) | `JobAvailabilityPattern` + `DayPattern` | évite de ressaisir la dispo à chaque appel |

Une fois la configuration posée, lance **`scripts/recommend_improvements.py`** (voir
étape 3.4bis) pour vérifier qu'aucun levier ROI évident n'a été oublié avant de
présenter le résultat.

**Étape 3 — Attaquer le chantier, avec auto-correction.** Une fois le besoin cadré, ne
t'arrête pas au premier jet — boucle jusqu'à un résultat vérifié :

1. Si un pattern proche existe dans `examples/` (compétence requise, stock de pièces,
   ordre entre jobs, disponibilité récurrente, ressource déjà engagée, pause
   obligatoire, indisponibilité ressource, rendez-vous client prioritaire, job
   multi-ressources…), pars de ce fichier plutôt que d'une page blanche — ce sont des
   payloads déjà vérifiés (voir `examples/README.md` pour la liste complète).
2. Pour tout champ dont tu n'es pas sûr à 100% du nom exact, du type ou de la valeur par
   défaut, ouvre `reference/entities.md` plutôt que de répondre de mémoire — ce fichier
   est la transcription complète et fiable du schéma, §3-11 ci-dessous n'en est qu'un
   résumé de confort. Jamais de champ inventé.
3. Écris le payload JSON (ou le code qui le génère). Si le projet a déjà un
   langage/stack identifié à l'étape 1, pars de `snippets/client.js` ou
   `snippets/client.py` plutôt que de réécrire un client HTTP from scratch.
4. **Avant tout appel réel**, lance `python3 <chemin-du-skill>/scripts/doctor.py payload.json`
   (exécute-le toi-même via ton outil d'exécution de commandes — terminal, shell,
   sous-processus, peu importe comment ton environnement l'appelle — ne demande pas à
   l'utilisateur de le lancer à ta place). Il valide d'abord (bloquant : s'il remonte des
   `[ERROR]`, corrige le payload et relance jusqu'à 0 erreur), puis recommande des
   améliorations ROI (jamais bloquant — compétences manquantes, pas de `shift_penalty`,
   pas de `locality`, SLA sans pénalité...). **Présente les recommandations `[HIGH]` à
   l'utilisateur même s'il n'a rien demandé de plus** — c'est le cœur de la valeur
   "copilote" : il ne doit jamais avoir à demander "et sinon, on pourrait améliorer
   quoi ?". (`validate_payload.py` et `recommend_improvements.py` restent utilisables
   séparément si tu n'as besoin que de l'un des deux — par exemple dans un script CI.)
5. Si une clé API est disponible, fais l'appel réel (`curl` ou le client) plutôt que de
   rester théorique. Si l'API renvoie une erreur HTTP ou des `unallocated_job_reasons`
   inattendues : ouvre `troubleshooting.md`, identifie la cause précise par le symptôme
   (jamais une supposition), corrige, et **réessaie une fois automatiquement** sans
   redemander à l'utilisateur. Si ça échoue encore après cette deuxième tentative,
   arrête-toi et explique précisément ce qui bloque plutôt que de boucler indéfiniment
   ou de deviner — chaque appel consomme des crédits. Une fois la réponse obtenue,
   relance `doctor.py payload.json --response reponse.json` : il ajoute alors le taux
   d'allocation réel, la répartition des `unallocated_job_reasons`, et le ratio
   trajet/temps utile — ce sont les trois chiffres à mettre en avant pour montrer
   l'intérêt concret du résultat à l'utilisateur.
6. Si le besoin touche une contrainte dure (compétence, stock, ordre entre jobs),
   vérifie le §8/§11 — ces mécanismes sont souvent oubliés alors qu'ils sont la vraie
   raison d'un plan qui ne correspond pas à l'attente métier.
7. Garde le format de sortie adapté au contexte : du code si on est dans un projet, un
   payload JSON commenté si c'est de la modélisation, une explication ciblée si c'est du
   débogage.

Objectif : l'utilisateur ne doit jamais avoir à répéter une info déjà visible dans son
projet, ne doit jamais recevoir un cours sur l'API quand il attend un livrable, ne doit
jamais recevoir un champ ou une valeur par défaut incorrecte, et ne doit jamais avoir à
repérer lui-même une erreur de payload que le validateur aurait attrapée en un appel.

## 1. C'est quoi

Le Scheduler API de Nomadia optimise des plannings de **field service et de livraison** :
on envoie des jobs (interventions/livraisons), des locations (adresses géocodées) et des
resources (techniciens/véhicules + leurs shifts), l'API renvoie le **meilleur plan** :
qui fait quoi, quand, dans quel ordre, avec les trajets associés.

**⚠️ Deux environnements distincts, confirmés par Nomadia le 23/10/2026 (versions non
définitives à cette date) :**

| Environnement | API | Portail |
|---|---|---|
| **Test** (actif — à utiliser par défaut) | `scheduler-api-test.nomadia-app.com` | `.../dashboard` |
| **Prod** (**pas encore actif**) | `scheduler-api.nomadia-app.com` | `.../dashboard` |

Cibler le domaine prod aujourd'hui échoue en erreur DNS (`NXDOMAIN`), pas en erreur
d'authentification — ce n'est pas un problème de clé ni de payload. Voir
`ONBOARDING.md` §0 pour le détail et le dépannage.

**Tant que ce skill cible le test, ne pas l'oublier au moment de passer en prod :**
tous les appels réels envoyés par ce skill (`snippets/client.py`, `client.js`,
`scripts/compare_scenarios.py`, le script de `ONBOARDING.md` §4) ciblent
`scheduler-api-test.nomadia-app.com` par défaut et l'affichent explicitement à
l'écran à chaque appel (`[INFO] Appel vers l'environnement de TEST...`) pour que ça
ne passe jamais inaperçu. Pour basculer sur la prod une fois confirmée active par
Nomadia, définir `NOMADIA_BASE_URL=https://scheduler-api.nomadia-app.com` — aucun
code à modifier, mais c'est une bascule volontaire à faire, pas un changement
automatique.

- Endpoint principal (test) : `POST https://scheduler-api-test.nomadia-app.com/api/schedule`
- Endpoint géocodage (test) : `POST https://scheduler-api-test.nomadia-app.com/api/geocode`
- Auth : header `x-api-key: YOUR_API_KEY` (clé créée dans le Portail Nomadia Scheduler)
- Appel **synchrone** : le plan optimisé revient directement dans la réponse
- Dates en ISO 8601 (`2026-11-02T08:00:00`), durées en ISO 8601 (`PT30M` = 30 min)
- Les `id` sont fournis par l'appelant et renvoyés tels quels

## 2. Quick start (exemple minimal)

```bash
curl -X POST https://scheduler-api-test.nomadia-app.com/api/schedule \
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

## 13. Fichiers du skill — quand ouvrir quoi

Ce SKILL.md est un résumé de navigation. Trois fichiers complètent le skill et doivent
être ouverts selon le besoin — ne pas essayer de tout retenir de mémoire :

| Fichier | Ouvrir quand… |
|---|---|
| `reference/entities.md` | tu écris un payload/code et as besoin du nom exact d'un champ, son type, ou sa valeur par défaut — transcription complète et fiable du schéma, y compris l'énumération entière des `unallocated_reason` |
| `troubleshooting.md` | un appel échoue, un job n'est pas planifié, ou le plan ne correspond pas à l'attendu — diagnostic par symptôme, à suivre avant de modifier du code au hasard |
| `snippets/client.js` et `snippets/client.py` | tu démarres une intégration dans un projet JS/Node ou Python — client HTTP minimal + validation locale du payload (détecte les `id` qui ne se référencent pas entre eux, les dates de shift incohérentes, etc. avant de consommer des crédits) |
| `reference/kpis-metier.md` | tu dois argumenter en rendez-vous commercial ou traduire un résultat technique (taux d'allocation, trajet, SLA) en impact business |
| `scripts/doctor.py` | **le réflexe par défaut** avant tout appel réel — valide puis recommande en une seule commande (voir §-1bis) |
| `scripts/recommend_improvements.py` | séparément de `doctor.py`, uniquement si besoin d'automatiser juste les recommandations (ex: script CI) |
| `scripts/compare_scenarios.py` | pour prouver un gain avant/après entre deux configs (sans clé API : diff de config ; avec clé API : vrai avant/après chiffré — **consomme des crédits**, ne lancer qu'avec l'accord explicite de l'utilisateur) |
| `reference/replanification-temps-reel.md` | dès qu'il est question de replanification en continu, de suivi temps réel, de figer une affectation déjà engagée, ou qu'on te compare à un solveur type Timefold/OptaPlanner |
| `reference/battlecard-timefold.md` | dès qu'un prospect compare Nomadia à Timefold/OptaPlanner/un solveur généraliste en rendez-vous commercial — argumentaire factuel + objections courantes + ce que l'autre fait réellement mieux |
| `scripts/test_validate_payload.py` | tu modifies `validate_payload.py` — lance ces tests pour vérifier que tu n'as rien cassé avant de committer |

**Portabilité.** Rien ici ne suppose un agent ou un éditeur précis : `scripts/` sont des
scripts Python autonomes exécutables en CLI (`python3 chemin/script.py`), `examples/` et
`reference/` sont du JSON/Markdown lisibles par n'importe quel outil de lecture de
fichiers. Si ton environnement n'a pas Python 3 disponible, dis-le explicitement plutôt
que de deviner le résultat de la validation.

## 13bis. Pour un agent qui découvre ce skill en premier

Lire `skill/llms.txt` — index priorisé de tous les fichiers du skill, inspiré du
`llms.txt` de la doc Nomadia elle-même et du pattern `context7.json` du repo GitHub de
Timefold (manifestes pensés pour être lus par un agent IA avant tout le reste).

## 14. Sources

- Doc schéma complète : PDF "Scheduler Schema Documentation" v1.1.9/1.1.10 (fourni par
  Nomadia)
- Doc API interactive : https://scheduler-json-api.readme.io/reference/quick-start
- Index pour agents IA : https://scheduler-json-api.readme.io/llms.txt
