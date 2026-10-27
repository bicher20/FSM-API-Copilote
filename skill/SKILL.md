---
name: nomadia
description: Copilote pour le Scheduler API de Nomadia (optimisation de tournées et planning field service / livraison). Cadre le besoin de l'utilisateur, inspecte son projet existant, puis implémente l'intégration — modélisation des jobs/ressources/contraintes, appels API, débogage d'une réponse. À utiliser dès qu'il est question de planifier des tournées/interventions, d'intégrer ou de déboguer le Scheduler API de Nomadia.
version: 1.25
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

> **Deux offres Nomadia, à ne jamais confondre.** Ce skill cible l'**offre
> self-service** — celle que la clé API de test/essai permet réellement d'appeler,
> documentée sur https://scheduler-json-api.readme.io (reference/entities.md en est
> la transcription complète et fiable). Nomadia a aussi une **offre complète**
> (documentation interne 33 pages), avec des mécanismes avancés
> (multi-ressources/binôme, stock de pièces, ordre entre jobs, horizon borné,
> disponibilité récurrente) **absents du self-service** — un payload qui les utilise
> reçoit un HTTP 200 mais le mécanisme est silencieusement ignoré, pas rejeté. Pour
> ces besoins, voir `reference/offre-complete-nomadia.md` : montrer l'exemple, puis
> orienter le client vers un contact Nomadia — jamais essayer de les simuler en
> self-service.

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

**Garde-fou clé API, valable à tout moment, pas seulement au premier contact :**
avant tout appel réel (pas la validation locale via `doctor.py` seul, qui ne consomme
rien), confirme explicitement avec l'utilisateur que la clé API utilisée est bien la
sienne (compte créé sur le portail test Nomadia) — voir `ONBOARDING.md` §2. Ne jamais
réutiliser silencieusement une `NOMADIA_API_KEY` déjà présente dans l'environnement
sans cette confirmation : elle peut appartenir à une session précédente, un autre
client, ou l'intégrateur plutôt qu'au client final.

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

Les étapes 1-2bis ci-dessous suivent la méthode détaillée dans
`reference/decouverte-besoin.md` (découverte structurée en 4 thèmes — entités,
contraintes, objectifs, taille du problème — adaptée pour exploiter la lecture du code
existant et trancher explicitement entre les deux offres Nomadia). Ouvre ce fichier
pour un besoin qui n'est pas immédiatement évident ; les résumés ci-dessous suffisent
pour un besoin simple et déjà clair.

## 0ter. Entretien avec état persistant et PRD (besoin pas immédiatement évident)

Pour un besoin ambigu ou un client qui préfère être guidé plutôt que de tout formuler
d'un coup, mène l'entretien en t'appuyant sur `reference/sections.json` (5 sections,
chacune avec une question d'ouverture et des critères de couverture) et
`scripts/interview_state.py` — **l'état vit dans un fichier, jamais seulement dans la
conversation**, pour survivre à une coupure/reprise. Déclenche-le dès que le client
exprime un besoin de cadrage ("je ne sais pas trop par où commencer", "aide-moi à
définir le besoin") — une seule phrase du client suffit, jamais une suite de commandes
à lui faire taper :

1. `python3 scripts/interview_state.py start` → récupère l'`interview_id`, pose la
   première question d'ouverture **dans les mots du métier du client, jamais de jargon
   technique** (ne jamais dire "job" ou "resource" à ce stade — dire "intervention",
   "technicien").
2. **Pose chaque question en QCM** (`scripts/interview_state.py options <section>`
   affiche les choix numérotés) : le client répond en cochant un ou plusieurs numéros,
   jamais en rédigeant une réponse ouverte — plus rapide pour lui, et il peut toujours
   ajouter une précision libre en plus. Enregistre avec
   `record <section> ["<précision>"] --options id1,id2,...` (virgules, pas d'espace
   entre les id) — ça marque automatiquement les critères liés, sans que tu aies à
   deviner. Une seule section à la fois.
3. Règles complètes de conduite d'entretien (reformulation, relance ciblée, réouverture
   d'une section, **possibilité pour le client de corriger toute réponse suggérée**
   via `interview_state.py edit`, seuil avant PRD) : voir `reference/regles-entretien.md`
   — à lire avant le premier entretien mené, pas à redéduire à chaque fois.
4. `progress` à tout moment pour voir où en est la couverture ; `prd --summary "..."`
   une fois au-dessus du seuil (`reference/sections.json: threshold_percent`) ou sur
   demande explicite — le `--summary` (1-2 phrases, écrites par toi) s'affiche en tête
   du PRD sous "Ce qui est planifié", et `--entity "Nom|Statut|Description"` (répétable)
   y ajoute une liste structurée par entité si tu préfères ce format à/en plus du texte
   libre. Le PRD distingue déjà automatiquement non-négociable / souple dans la section
   contraintes, ET se termine par un récapitulatif global qui agrège ces deux catégories
   sur **tous les thèmes** (contraintes + objectifs), pas juste localement.
5. **Chaque `record` affiche un avancement global (%, sections complètes/total)** —
   partage-le au client à chaque changement de section (pas après chaque phrase) pour
   qu'il voie une progression naturelle et mesurable, jamais qu'il se demande où il en
   est (voir `reference/regles-entretien.md` §2bis).

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

**Si la réponse au point 3 fait apparaître un besoin de stock de pièces, d'ordre entre
jobs, de job multi-ressources, d'horizon borné ou de disponibilité récurrente** :
**pose explicitement la question self-service vs offre complète** avant d'aller plus
loin (voir `reference/decouverte-besoin.md`, section "Niveau d'offre") — ne suppose
jamais que le client est en self-service juste parce que c'est ce que ce skill appelle
directement.

Si l'objectif est déjà clair depuis le message de l'utilisateur ou le contexte du repo,
**saute directement à l'étape 3** sans poser de question pour la forme.

**Étape 2bis — Mapper l'objectif client à la configuration à activer.** Dès que
l'objectif métier est connu, traduis-le immédiatement en mécanismes Nomadia concrets à
activer — ne laisse jamais l'utilisateur deviner quelle case cocher :

| Objectif client | Mécanisme self-service à activer | Pourquoi (ROI) |
|---|---|---|
| Respecter des rendez-vous/fenêtres client stricts | `job.sla` avec `penalty_per_hour`/`base_jeopardy_penalty` > 0 **ET `job.value_per_hour` fixé explicitement** (voir l'avertissement ci-dessous) | évite le risque réputationnel d'un rdv raté — kpis-metier.md §3 |
| Rendez-vous client avec sa propre tolérance, en plus du SLA général | `job.appointment_sla` (2e objet SLA imbriqué) | couvre le besoin "rdv prioritaire" sans le champ `appointment_priority` dédié (offre complète) |
| Technicien avec habilitation/compétence obligatoire | `requirements: ["..."]` (liste de chaînes) sur le `job` et sur la/les `resource(s)` habilitée(s) | évite d'envoyer la mauvaise ressource — kpis-metier.md §1 |
| Réduire les km/le temps de trajet | `locality` sur les `Location` + revoir `start_location_id`/`end_location_id` | argument ROI le plus direct — kpis-metier.md §2 |
| Limiter le nombre de véhicules/techniciens mobilisés | `shift_penalty` > 0 | baisse du coût fixe journalier — kpis-metier.md §4 |
| Technicien déjà engagé/en route sur un job | `fixed_resource_id` directement sur le `job` | empêche l'API de réaffecter un job déjà pris en charge |

**⚠️ `value_per_hour` n'a aucune valeur par défaut fiable côté self-service — confirmé
par test réel le 27/10/2026.** Un job sans `value_per_hour` explicite a été planifié
6h30 après sa fenêtre SLA (09:00-11:00) malgré une `base_jeopardy_penalty` de 500 et
une ressource habilitée disponible dans la fenêtre — le solveur a jugé le job trop
peu "valorisé" pour justifier le coût de respecter la fenêtre. En fixant
`value_per_hour` à une valeur haute (et explicite) sur ce même job, la fenêtre a été
respectée au test suivant, toutes choses égales par ailleurs. **Toujours fixer
`value_per_hour` explicitement sur tout job dont le respect d'une fenêtre SLA/rendez-vous
compte réellement pour le client** — ne jamais compter sur un défaut implicite (voir
`reference/entities.md`).

Si l'objectif correspond plutôt à un mécanisme de l'**offre complète** (job
multi-ressources/binôme, stock de pièces embarqué, ordre obligatoire entre deux
jobs, horizon de planification borné, disponibilité vraiment récurrente) : ouvrir
`reference/offre-complete-nomadia.md`, montrer l'exemple qui y figure, et dire
explicitement au client qu'il doit contacter l'équipe Nomadia pour l'activer — ne
jamais essayer de l'encoder dans un payload self-service (il serait silencieusement
ignoré, voir l'avertissement en tête de ce fichier).

Une fois la configuration posée, lance **`scripts/recommend_improvements.py`** (voir
étape 3.4bis) pour vérifier qu'aucun levier ROI évident n'a été oublié avant de
présenter le résultat.

**Étape 3 — Attaquer le chantier, avec auto-correction.** Une fois le besoin cadré, ne
t'arrête pas au premier jet — boucle jusqu'à un résultat vérifié :

1. Si un pattern proche existe dans `examples/` (compétence requise, disponibilité
   limitée à des créneaux, ressource déjà engagée, pause obligatoire, indisponibilité
   ressource, rendez-vous client), pars de ce fichier plutôt que d'une page blanche —
   ce sont des payloads self-service déjà vérifiés (voir `examples/README.md` pour la
   liste complète). Trois exemples (`03`, `04`, `10`) sont marqués "offre complète
   uniquement" : ils montrent la forme du payload côté offre complète pour un besoin
   qui n'a pas d'équivalent self-service — ne jamais les envoyer tels quels à l'API
   self-service en espérant un vrai résultat.
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
6. Si le besoin touche une contrainte dure self-service (compétence via
   `requirements`), vérifie le §8. Si le besoin correspond à un mécanisme absent du
   self-service (multi-ressources, stock, ordre entre jobs, horizon borné,
   récurrence), ouvre `reference/offre-complete-nomadia.md` plutôt que d'essayer de
   le simuler — c'est souvent la vraie raison d'un plan qui ne correspond pas à
   l'attente métier, pas un bug de modélisation.
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

## 3. Modèle de données — vue d'ensemble (self-service)

**Source de vérité : `reference/entities.md`**, transcrit du schéma OpenAPI réel qui
alimente l'API self-service (confirmé le 27/10/2026 par fetch direct du schéma, pas
par la doc rendue). Les sections 4-8 ci-dessous n'en sont qu'un résumé de confort —
toujours ouvrir `reference/entities.md` pour le détail exact d'un champ.

Cinq entités d'entrée au niveau racine, aucune entité "jointure" séparée — tout le
reste (SLA, Shift, Break, disponibilités) est **imbriqué** :

| Entité | Clé racine | Obligatoire |
|---|---|---|
| `Job` | `jobs` | oui |
| `ResourceType` | `resource_types` | oui |
| `Resource` | `resources` | oui |
| `Location` | `locations` | oui |
| `JobType` | `job_types` | non |

**⚠️ Pas de rejet garanti des champs inconnus.** La spec déclare
`additionalProperties: false`, mais un champ inconnu au niveau racine a été observé
silencieusement ignoré par l'API réelle (HTTP 200) plutôt que rejeté. Un payload qui
"passe" ne prouve donc pas que tous ses champs ont été pris en compte — toujours
vérifier le résultat, pas seulement le code HTTP.

## 4. Location

`id` (M), `latitude`/`longitude` (M), `locality` (O, regroupe des lieux : l'API
essaie de faire tous les jobs d'une même localité d'un coup), `additional_travel_time`
(O, s'ajoute à tout trajet vers ce lieu).

## 5. Module Job — ce qui doit être fait

**JobType** (optionnel) — valeurs par défaut partagées par plusieurs jobs : `id` (M),
`requirements` (liste de chaînes), `custom_duration`, `duration_in_half_days`,
`value_per_hour`, `split_allowed`.

**SLA** (objet imbriqué, jamais une entité top-level avec id) — utilisé par
`job.sla` et `job.appointment_sla` : `earliest_start_date_time` (M),
`latest_start_date_time` (M), `penalty_per_hour` (O, pousse à planifier tôt),
`base_jeopardy_penalty` (O, pénalité fixe si la fenêtre est ratée — peut empêcher
l'allocation hors fenêtre si > `value_per_hour` du job), `penalty_per_hour_jeopardy`
(O, ⚠️ la doc officielle donne une valeur par défaut incohérente avec son propre
type — toujours la fixer explicitement si utilisée).

**Job** — `id` (M), `job_type_id` (M, défaut `"DEFAULT"`), `location_id` (M), `sla`
(objet SLA, M), `appointment_sla` (objet SLA, O — **deuxième** fenêtre distincte,
pour un rendez-vous avec sa propre tolérance), `fixed_resource_id` (O, ressource à
laquelle le job est engagé — champ direct, pas d'entité séparée, pas de
`commit_date_time_stamp`), `fixed_date_time` (O, démarrage exact imposé),
`custom_duration`/`duration_in_half_days` (O, sinon hérité du `job_type`),
`value_per_hour` (O), `split_allowed` (O, étale le job **dans le temps** sur
plusieurs visites — jamais sur plusieurs ressources simultanées),
`availabilities`/`unavailabilities` (listes de fenêtres fixes `{start_date_time,
end_date_time}`, **aucune récurrence possible**), `requirements` (liste de chaînes).

## 6. Module Resource — qui peut le faire

**ResourceType** — `id` (M), `start_location_id`/`end_location_id` (M),
`requirements` (liste de chaînes), `cost_per_kilometre`/`cost_per_hour` (défaut 1),
`maximum_travel_time_from_start_location`/`maximum_individual_travel_time`/
`maximum_travel_time_per_shift` (O), `minimum_jobs_per_shift`/`maximum_jobs_per_shift`
(O), `pre_shift_travel_period`/`post_shift_travel_period` (défaut PT0S),
`overtime_period` (défaut PT0S), `overtime_cost_multiplier` (défaut 5),
`shift_penalty` (défaut 0, coût fixe dès qu'un shift a au moins 1 job — pousse à
concentrer le travail sur moins de ressources/shifts).

**Resource** — `id` (M), `resource_type_id` (M, défaut `"DEFAULT"`), `shifts` (liste
de `Shift`), `unavailabilities` (liste de `ResourceUnavailability`, **imbriquée ici**,
pas une entité top-level avec `resource_id`), `requirements` (liste de chaînes),
`start_location_id`/`end_location_id` (O, surcharge le `resource_type`).

**Shift** (`resources[].shifts[]`) — `start_date_time`/`end_date_time` (M), `breaks`
(liste de `Break`), `start_location_id`/`end_location_id` (O, surcharge pour ce
shift). Pas de champ `id`.

**Break** (`shifts[].breaks[]`) — `earliest_start_date_time`/`latest_start_date_time`
(M), `duration` (M), `fixed_date_time` (O). Pas de champ `id`/`shift_id` : la pause
est définie par sa position dans `shift.breaks[]`.

**ResourceUnavailability** (`resources[].unavailabilities[]`) — `id` (M),
`start_date_time`/`end_date_time` (M), `location_id` (O).

## 7. Module Output — ce que l'API renvoie

| Clé | Rôle |
|---|---|
| `allocations[]` | **par job** (`job_id` + liste `visits[]`) — plusieurs `visits` seulement si le job a été étalé dans le temps, jamais plusieurs ressources sur une même visite |
| `travels[]` | trajets d'une ressource (distance, lieux, horaires) |
| `unallocated_job_reasons[]` | pourquoi un job n'a pas été planifié (`job_id` + `unallocated_reason`) |
| `break_allocations[]` | quand chaque pause a été placée |

Les valeurs possibles de `unallocated_reason` ne sont pas documentées sur les pages
self-service (elles l'étaient côté offre complète — `NotCalculated`, `ZeroValue`,
`AllPossibleResourcesFull`, etc.) : à traiter comme probables mais non garanties tant
qu'un test réel n'en a pas confirmé l'exhaustivité côté self-service.

## 8. Compétences obligatoires (contrainte dure disponible en self-service)

Un seul mécanisme, simple : `requirements` est une **liste de chaînes libres**,
directement sur `job`/`job_type` d'un côté et `resource`/`resource_type` de l'autre
(pas d'entité `Requirement` séparée avec id). Un job ne peut être fait que par une
ressource dont les `requirements` couvrent la liste du job.

Les autres contraintes dures — stock de pièces, ordre entre jobs, multi-ressources —
n'ont **aucun équivalent self-service** : voir `reference/offre-complete-nomadia.md`.

## 9. FAQ rapide

- **Comment forcer un technicien précis sur un job ?** `fixed_resource_id`
  directement sur le `job`.
- **Comment grouper les jobs d'un même quartier dans une même tournée ?** donner la
  même `locality` aux `Location` concernées.
- **Comment pénaliser un planning avec trop de shifts "éclatés" ?** `shift_penalty`
  sur le `resource_type`/`resource`.
- **Comment gérer une compétence obligatoire (ex. habilitation électrique) ?**
  `requirements: ["HABILITATION_ELEC"]` sur le job et sur la/les ressource(s)
  habilitée(s) — voir §8.
- **Comment gérer un rendez-vous avec sa propre tolérance horaire ?**
  `job.appointment_sla`, un deuxième objet SLA imbriqué.
- **Et le stock de pièces / l'ordre entre jobs / le multi-ressources / l'horizon
  borné / la récurrence ?** Aucun équivalent self-service — voir
  `reference/offre-complete-nomadia.md`, ne jamais essayer de les simuler.
- **Pourquoi un job n'est pas planifié alors qu'une ressource semble libre ?**
  regarder `unallocated_job_reasons` — voir §7 et `troubleshooting.md`.
- **Le planning évolue en temps réel ?** voir
  `reference/replanification-temps-reel.md` pour ce qui est confirmé côté
  self-service.

## 10. Fichiers du skill — quand ouvrir quoi

Ce SKILL.md est un résumé de navigation. Les fichiers suivants complètent le skill et
doivent être ouverts selon le besoin — ne pas essayer de tout retenir de mémoire :

| Fichier | Ouvrir quand… |
|---|---|
| `reference/entities.md` | tu écris un payload/code et as besoin du nom exact d'un champ, son type, ou sa valeur par défaut — transcription fiable du schéma OpenAPI self-service réel (pas la doc PDF de l'offre complète) |
| `reference/offre-complete-nomadia.md` | le besoin correspond à un mécanisme absent du self-service (multi-ressources, stock, ordre entre jobs, horizon borné, récurrence, priorité de rdv dédiée) — exemple à montrer + comment orienter vers un contact Nomadia |
| `reference/decouverte-besoin.md` | au tout début d'une mission, pour mener la découverte du besoin en 4 thèmes (entités, contraintes, objectifs, taille) et trancher explicitement self-service vs offre complète — surtout utile sur un besoin pas immédiatement évident |
| `reference/sections.json` | structure machine-lisible de l'entretien (sections, questions d'ouverture, critères de couverture, seuil) — lu par `scripts/interview_state.py`, jamais à dupliquer de mémoire |
| `reference/regles-entretien.md` | avant de mener un entretien structuré — reformulation, relance, réouverture de section, règle du jamais-inventé, seuil avant PRD |
| `scripts/interview_state.py start\|options\|record\|progress\|prd\|edit` | entretien de découverte du besoin en QCM (options numérotées + précision libre), état persistant (fichier, pas la mémoire de la conversation), avancement affiché en couleur à chaque réponse, et génération du PRD final (résumé libre et/ou liste d'entités structurée, récapitulatif global non-négociable/nice-to-have tous thèmes confondus) — voir §0ter |
| `troubleshooting.md` | un appel échoue, un job n'est pas planifié, ou le plan ne correspond pas à l'attendu — diagnostic par symptôme, à suivre avant de modifier du code au hasard |
| `snippets/client.js` et `snippets/client.py` | tu démarres une intégration dans un projet JS/Node ou Python — client HTTP minimal + validation locale du payload (détecte les `id` qui ne se référencent pas entre eux, les dates de shift incohérentes, etc. avant de consommer des crédits) |
| `reference/kpis-metier.md` | tu dois argumenter en rendez-vous commercial ou traduire un résultat technique (taux d'allocation, trajet, SLA) en impact business |
| `scripts/doctor.py` | **le réflexe par défaut** avant tout appel réel — valide puis recommande en une seule commande (voir §-1bis) |
| `scripts/recommend_improvements.py` | séparément de `doctor.py`, uniquement si besoin d'automatiser juste les recommandations (ex: script CI) |
| `scripts/compare_scenarios.py` | pour prouver un gain avant/après entre deux configs (sans clé API : diff de config ; avec clé API : vrai avant/après chiffré — **consomme des crédits**, ne lancer qu'avec l'accord explicite de l'utilisateur) |
| `reference/replanification-temps-reel.md` | dès qu'il est question de replanification en continu, de suivi temps réel, ou de figer une affectation déjà engagée |
| `scripts/test_validate_payload.py` | tu modifies `validate_payload.py` — lance ces tests pour vérifier que tu n'as rien cassé avant de committer |
| `scripts/generate_load_test.py` | pour générer un payload de charge à grande échelle (N jobs/M ressources) et challenger l'API sur le volume — **affiche le coût maximum estimé avant d'écrire le fichier, ne jamais lancer l'appel réel sans l'avoir accepté explicitement** |

**Portabilité.** Rien ici ne suppose un agent ou un éditeur précis : `scripts/` sont des
scripts Python autonomes exécutables en CLI (`python3 chemin/script.py`), `examples/` et
`reference/` sont du JSON/Markdown lisibles par n'importe quel outil de lecture de
fichiers. Si ton environnement n'a pas Python 3 disponible, dis-le explicitement plutôt
que de deviner le résultat de la validation.

## 10bis. Pour un agent qui découvre ce skill en premier

Lire `skill/llms.txt` — index priorisé de tous les fichiers du skill, inspiré du
`llms.txt` de la doc Nomadia elle-même et des manifestes `llms.txt`/`context7.json`
qu'on trouve sur plusieurs repos GitHub d'outils IA (pensés pour être lus par un agent
avant tout le reste).

## 11. Sources

- Doc self-service (référence primaire de ce skill) :
  https://scheduler-json-api.readme.io/reference/quick-start,
  `.../reference/api-keys`, `.../reference/post_schedule`, `.../reference/post_geocode`
  — schémas OpenAPI complets récupérés le 27/10/2026 et conservés dans
  `vendor-docs/openapi-schedule.json` et `vendor-docs/openapi-geocode.json`.
- Doc offre complète (uniquement pour `reference/offre-complete-nomadia.md`) : PDF
  "Scheduler Schema Documentation" v1.1.9/1.1.10 (fourni par Nomadia) — ne jamais
  utiliser comme référence pour un payload self-service.
- Index pour agents IA : https://scheduler-json-api.readme.io/llms.txt
