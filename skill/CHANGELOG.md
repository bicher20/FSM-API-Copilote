# Changelog du skill

## 1.35 — 2026-10-28 — Durcissement du code (audit demandé)
- **Bug réel corrigé : KeyError latent si `sections.json` évolue.** `interview_state.py`
  indexait directement `state["sections"][id]` à plusieurs endroits
  (`compute_global_percent`, `cmd_progress`, `render_prd_markdown`,
  `_build_global_roundup`) — un entretien démarré AVANT une évolution du schéma
  (exactement ce qui s'est produit cette session même, quand "entites" a été scindé en
  4 sections) plantait toute commande dès qu'une section manquait. Nouvelle fonction
  `_migrate_state()`, appelée automatiquement par `load_state()` : ajoute les sections
  manquantes avec un squelette vide, réaligne `total_criteria` si le nombre de
  critères d'une section a changé, et retire tout indice de critère devenu hors
  limites — jamais de crash, jamais de donnée fantôme.
- **Bug réel corrigé : `options --interview ID` avec un id inexistant retombait en
  silence sur un affichage NON filtré** (sans erreur, sans avertissement) au lieu
  d'échouer bruyamment comme toutes les autres commandes — risquait de présenter au
  client des choix déjà sans objet sans que l'agent s'en rende compte. Corrigé : un
  `--interview` explicite mais introuvable échoue maintenant comme partout ailleurs.
- **`cmd_list` passe maintenant par `load_state()`** (migration + tolérance) au lieu
  d'un `json.load` direct — un vieil entretien ou un fichier corrompu n'interrompt
  plus `list` pour tous les autres, juste signalé et ignoré.
- **`new_interview_id()` ne peut plus silencieusement réutiliser un id déjà pris**
  (collision théorique sur `secrets.token_hex(3)`, 16M valeurs) — vérifie
  explicitement avant de retourner.
- **`match_data_model.py match`** rejette maintenant explicitement un JSON introuvable/
  invalide, une liste vide, ou contenant des valeurs non textuelles — avant, une
  entrée mal formée aurait fait planter le script avec une trace Python brute au lieu
  d'un message clair.
- **Nouveau `scripts/test_interview_state.py`** : suite de tests en process (jamais
  sur le vrai `.interview_state/` ni le vrai `sections.json`) couvrant le filtrage
  `depends_on`, la pagination groupée dur/souple, `record`/`score`/`handoff`/`prd`
  (seuil, distinction non-négociable/souple par section ET dans le récapitulatif
  global), et surtout la migration de schéma décrite ci-dessus — pour que ce genre de
  régression soit détecté avant un commit, pas en situation réelle avec un client.

## 1.34 — 2026-10-28
- **Nouvelle commande `interview_state.py handoff`** : génère un message prêt à
  relire/adapter (jamais envoyé automatiquement) pour mettre le client en relation
  avec le contact nommé (Marouane Bicher, marouane.bicher@nomadia.com) dès qu'il
  confirme vouloir passer par le compte pro/l'offre complète — reprend les mécanismes
  détectés par `score` si `--summary` n'est pas fourni. Réduit la friction de
  rédaction manuelle à chaque fois que ce moment arrive.
- **Support multilingue de la conversation** (`reference/regles-entretien.md` §0ter,
  nouveau) : tout le texte interne du skill (sections.json, les sorties du script, la
  doc) reste en français — c'est la langue de travail interne, jamais une contrainte
  sur la langue parlée avec le client. Règle explicite ajoutée : dès que le client
  écrit dans une autre langue (anglais, etc.), continuer toute la conversation dans
  cette langue sans qu'il ait à le demander, en traduisant à la volée les questions/
  labels que le script affiche (supports internes pour l'agent, jamais un texte à
  réciter mot pour mot) ; et pour tout livrable transmis au client (PRD, `handoff`),
  le retraduire soi-même avant remise plutôt que de livrer un document à moitié en
  français.

## 1.33 — 2026-10-28
- **Nouvelle commande `interview_state.py list`** : liste tous les entretiens en
  cours (id, titre, % de couverture), triés du plus récent au plus ancien. Comblait
  un vrai manque : sans `--interview` explicite, les autres commandes prenaient par
  défaut l'entretien le plus récemment modifié — correct pour un seul client à la
  fois, risqué dès que plusieurs prospects sont suivis en parallèle (reprise d'une
  conversation sur un autre dossier entre deux sessions pouvait faire travailler sur
  le mauvais entretien sans le savoir).
- `start` prend maintenant explicitement `--title "<nom du client>"` en exemple
  partout (déjà supporté avant, mais pas mis en avant) — c'est ce que `list` affiche
  pour qu'un entretien reste identifiable sans avoir à retenir un id hexadécimal.
- `regles-entretien.md` §0bis (nouveau) : réflexe à avoir — lancer `list` dès qu'on
  reprend un échange déjà en cours, plutôt que de supposer "le plus récent".

## 1.32 — 2026-10-28
- **Nouveau : `reference/cerveau-matching.md` + `scripts/match_data_model.py`.**
  Rapprochement systématique entre le code/schéma du client et le modèle Nomadia :
  l'agent extrait les noms de champs/tables trouvés dans le repo client (grep/lecture
  de fichiers, déjà demandé par §0 Étape 1 de `SKILL.md`) et les passe au script, qui
  compare contre un dictionnaire de synonymes FR/EN par entité Nomadia (Job, Resource,
  Location, ResourceType, JobType + champs clés) et renvoie un niveau de confiance par
  champ (haute : mappe directement sans redemander ; moyenne : propose et fait
  confirmer ; aucune : pose la question). Objectif : ne questionner le client que sur
  ce qui est réellement ambigu, jamais sur ce que son propre code dit déjà.
- **Règle stricte anti-promesse** (`reference/cerveau-matching.md` §2,
  `reference/regles-entretien.md` §7) : plus aucun pourcentage de gain/ROI affiché au
  client sans l'avoir mesuré sur un payload réel exécuté pour CE client — via
  `scripts/compare_scenarios.py` en mode avec clé API (déjà existant), jamais une
  moyenne sectorielle ou une estimation générique. Le PRD doit si possible enchaîner
  sur un vrai appel plutôt que de rester une promesse abstraite, sans jamais insister
  si le client préfère attendre.
- **Les crédits ne sont plus un argument** : supprimé toute idée d'afficher le coût en
  crédits comme argument commercial dans le PRD ou ailleurs — ce sujet reste
  strictement opérationnel (confirmer la clé API, prévenir avant un appel qui
  consomme), jamais un levier de vente.

## 1.31 — 2026-10-28
- **Ton "raisonnement en direct" plutôt que formulaire** (`regles-entretien.md` §0,
  nouveau) : comparatif direct avec l'assistant PRD d'un concurrent — leur fil ne pose
  jamais une question sans dire d'abord, en une phrase, ce que la réponse
  précédente vient de décider pour le plan du client ("comme tu m'as dit X, ton plan
  va Y — maintenant, Z ?"). Le skill applique maintenant ce même principe à chaque
  transition, y compris quand elle touche l'offre complète/le contact nommé : ce
  point s'intègre dans la même phrase de conséquence que le reste, jamais comme un
  encart ou une formule plaquée séparée du raisonnement. Demande aussi de varier les
  formules de clôture/relance d'une section à l'autre plutôt que de répéter mot pour
  mot la même tournure.

## 1.30 — 2026-10-28
- **Contact offre complète nommé** : partout où le skill oriente le client vers
  l'équipe Nomadia pour l'offre complète (`reference/offre-complete-nomadia.md`,
  `reference/decouverte-besoin.md`, `scripts/interview_state.py score`, `SKILL.md`,
  `reference/regles-entretien.md`), le contact donné est maintenant nommé — Marouane
  Bicher, expert Nomadia, marouane.bicher@nomadia.com — jamais un "équipe Nomadia"
  anonyme.
- **Pagination des QCM : jamais un mélange dur/souple sur une même page.** Revue d'un
  échange réel a montré qu'une page de contraintes (page 2/3) mélangeait deux
  contraintes dures et une préférence souple sans le signaler. `options <section>`
  groupe maintenant les choix par `options[].hard` avant de paginer (dur d'abord,
  souple ensuite), avec un sous-titre explicite par groupe.
- **Ne plus redemander au client de classer dur/souple** (`regles-entretien.md`
  §2ter) : c'est déjà encodé par les options QCM cochées — présenter le découpage déjà
  connu et demander confirmation, jamais une classification de zéro.
- **Pagination : garder le même numéro de question** (`regles-entretien.md` §1ter) —
  un échange réel montrait un saut de "Question 9" à "Question 10" au milieu d'une
  même question paginée, ce qui laisse croire à un changement de sujet.

## 1.29 — 2026-10-28
- **Ton self-service/offre complète revu : jamais un blocage, jamais un motif pour
  arrêter la conversation.** Mène toujours l'entretien de découverte comme si on visait
  l'offre complète (périmètre des questions jamais réduit selon le niveau d'offre
  détecté). Le self-service est présenté au client positivement — "on sait gérer ça, il
  faut juste nous mettre en contact avec l'équipe Nomadia" — jamais comme une limite ou
  une version dégradée.
- `scripts/interview_state.py score` : le signal `[MISMATCH]` devient
  `[OFFRE COMPLETE REQUISE]`, avec une consigne explicite de ne jamais stopper
  l'entretien pour autant.
- `reference/decouverte-besoin.md` : script de présentation au client reformulé dans
  cet esprit (plus de "en self-service en me limitant à ce qui est possible
  aujourd'hui" présenté comme une alternative équivalente).
- `reference/regles-entretien.md` §7 et `SKILL.md` §0ter/étape 2 mis à jour en
  conséquence.

## 1.28 — 2026-10-27
- **Jamais plus de 4 choix affichés au client en une fois** : `options <section>`
  coupe maintenant automatiquement toute section ayant plus de
  `MAX_CHOICES_PER_SCREEN` (4) choix visibles en plusieurs parties (`--page N`),
  avec indication explicite "partie X/Y" et rappel de la commande pour la suite —
  rien à découper soi-même.
- **Relance renforcée (§4 de `regles-entretien.md`)** : quand un critère n'est pas
  couvert, l'agent doit reformuler la question différemment et nommer précisément ce
  qui manque, jamais répéter mot pour mot la question initiale.
- **Nouveau : `scripts/interview_state.py score`** — système de scoring qui compare
  les contraintes cochées correspondant à un mécanisme offre-complète-only
  (`sections.json: options[].offre_complete_trigger` sur stock de pièces, ordre
  entre jobs, binôme/multi-ressources) au niveau d'offre confirmé par le client en
  section niveau_offre, et signale explicitement un `[MISMATCH]` (besoin détecté mais
  self-service/pas de clé/pas clarifié) plutôt que de laisser l'agent le remarquer ou
  pas. `reference/regles-entretien.md` §7 : à lancer avant tout appel réel.

## 1.27 — 2026-10-27
- **Le thème "entités" était un mur de 9 choix mélangeant 4 sujets différents**
  (type de ressource, durée des interventions, géolocalisation, données existantes)
  dans un seul QCM — scindé en 4 sections successives à un seul sujet chacune
  (`entites_ressources`, `entites_interventions`, `entites_lieux`, `entites_donnees`),
  chacune avec sa propre question d'ouverture conversationnelle. L'entretien compte
  maintenant 8 sections au lieu de 5 ; les `depends_on` référençant l'ancienne section
  `entites` (pour "binôme technicien" et "mobiliser moins de techniciens") pointent
  désormais vers `entites_ressources`.
- Rupture pour un entretien déjà en cours au moment de la mise à jour (état dans
  `.interview_state/`, jamais committé/livré) : relancer `start` plutôt que de
  reprendre un entretien entamé sous l'ancien découpage à 5 sections.

## 1.26 — 2026-10-27
- **Ton des questions plus conversationnel** : toutes les `opening_question` de
  `reference/sections.json` reformulées (moins "formulaire", plus une vraie
  conversation — "Pour commencer, aide-moi à visualiser ton quotidien...").
- **"Autre chose à préciser" devient un vrai choix numéroté** dans `options <section>`,
  pas juste une note en petit sous la liste QCM — le client coche ce numéro comme les
  autres pour ajouter du contexte libre.
- **Filtrage adaptatif des options non pertinentes** (`sections.json: options[].
  depends_on`) : une option peut maintenant dépendre d'une réponse déjà donnée dans une
  autre section (ex. "binôme technicien" et "mobiliser moins de techniciens" ne
  s'affichent que si des techniciens/équipes ont été identifiés en section "entités").
  `scripts/interview_state.py options <section> --interview ID` filtre automatiquement
  d'après l'état réel de l'entretien — l'agent n'envoie plus la liste complète par
  défaut, et n'a jamais à décider lui-même quoi masquer. Les options de conformité clé
  API (section "niveau_offre") restent toujours visibles, elles.
- `reference/regles-entretien.md` : nouvelle §1bis documentant ce mécanisme.

## 1.25 — 2026-10-27
- **PRD : "Ce qui est planifié" accepte une liste structurée par entité**, via
  `scripts/interview_state.py prd --entity "Nom|Statut|Description"` (répétable), en
  plus ou à la place du `--summary` en texte libre — rendue en liste à puces
  (`**Nom** — *Statut* : description`), jamais déduite automatiquement des labels QCM.
- **Nouveau "Récapitulatif global" en fin de PRD** : agrège, sur **tous les thèmes**
  (pas seulement la section "contraintes"), deux listes uniques "Non négociable" /
  "Nice to have" — construites option par option (jamais tour par tour, pour éviter
  qu'une réponse mixte dure+souple duplique toute la phrase dans les deux listes). Les
  objectifs priorisés (section "objectifs") y entrent systématiquement côté nice-to-have.
- **Règle d'entretien formalisée (§4bis)** : que faire quand la réponse du client ne
  correspond manifestement pas à la question posée — le dire explicitement plutôt que
  de forcer la réponse dans le critère le plus proche.

## 1.24 — 2026-10-27
- **PRD : récap "Ce qui est planifié" en tête**, via `scripts/interview_state.py prd
  --summary "<1-2 phrases>"` écrites par l'agent — affiché avant le détail
  section par section, pour que le client retrouve l'essentiel en un coup d'œil.
- **Section "contraintes" : séparation automatique non-négociable / souple** dans le
  rendu du PRD, plutôt qu'un seul paragraphe mélangé. `reference/sections.json` gagne
  un flag `options[].hard` (section contraintes uniquement) ; `interview_state.py`
  classe chaque tour enregistré en conséquence (`_classify_turn_by_hardness`) sans
  rien à faire de plus côté agent — les choix QCM portent déjà cette information.

## 1.23 — 2026-10-27
- **L'entretien de découverte (v1.22) passe en QCM** : chaque section de
  `reference/sections.json` a maintenant une liste d'options numérotées
  (`options[].id/label/criteria`) en plus de ses critères — le client répond en
  cochant un ou plusieurs numéros plutôt qu'en rédigeant une réponse ouverte, et peut
  toujours ajouter une précision libre. Nouvelle sous-commande
  `scripts/interview_state.py options <section>` pour afficher le questionnaire.
  `record` accepte `--options id1,id2,...` et marque **automatiquement** les critères
  liés (plus besoin que l'agent devine) ; le texte libre optionnel vient en
  complément, composé avec les choix dans la réponse enregistrée.
- **Couleurs ANSI par défaut dans le terminal** pour toute la sortie de
  `interview_state.py` ([OK] en vert, [ERROR] en rouge, symboles ○/◐/● de couverture,
  pourcentage d'avancement en cyan, numéros du QCM) — désactivées automatiquement si
  `NO_COLOR` est défini ou si la sortie n'est pas un vrai terminal (redirection,
  pipe), pour ne jamais polluer une sortie relue par un autre outil.
- **Nouveau critère "clé API + suivi des crédits"** dans la section `niveau_offre` :
  le PRD ne se considère plus complet sans confirmer explicitement que la clé API
  utilisée appartient au client courant et sans indiquer où suivre sa consommation de
  crédits (portail Nomadia) avant un premier appel réel — relié à `ONBOARDING.md` §2
  et au garde-fou clé API déjà présent en `SKILL.md` §-1. `reference/regles-entretien.md`
  §7 rappelle ce point explicitement au moment d'enchaîner le PRD vers un appel réel.
- **Retrait de toute mention du nom d'un concurrent** (présent dans `SKILL.md`,
  `llms.txt`, `reference/decouverte-besoin.md`, `reference/regles-entretien.md`,
  `reference/sections.json`, `scripts/interview_state.py`, `scripts/doctor.py`,
  `scripts/compare_scenarios.py`, `reference/replanification-temps-reel.md`,
  `CHANGELOG.md`) — la méthode (découverte par thèmes, suivi de couverture, document
  de besoins généré une fois le cadrage suffisant) reste la même, décrite sans nommer
  l'outil qui l'a inspirée. Le comparatif commercial détaillé reste uniquement dans
  `internal/battlecard-timefold.md`, jamais livré au client
  (`scripts/package_for_client.py` ne copie que `skill/`).

## 1.22bis — 2026-10-27
- **Renommé le skill `nomadia-scheduler-api` → `nomadia`**, nom plus simple à retenir
  et à invoquer. Changé dans `SKILL.md` (`name:`), `llms.txt`, `ONBOARDING.md`,
  `README.md`, et `scripts/package_for_client.py` (nom de package par défaut). Le
  dossier du repo reste `skill/` (générique, n'a jamais porté l'ancien nom) — seul le
  dossier local d'installation doit être renommé par chaque utilisateur existant :
  `mv ~/.claude/skills/nomadia-scheduler-api ~/.claude/skills/nomadia`.

## 1.22 — 2026-10-27
- **Entretien structuré avec état persistant et génération de PRD**, pour aller plus
  loin que `reference/decouverte-besoin.md` (découverte en prose) vers un vrai moteur
  de cadrage conversationnel :
  - `reference/sections.json` : les 5 sections de l'entretien (entités, contraintes,
    objectifs, taille, niveau d'offre) en JSON machine-lisible, chacune avec sa
    question d'ouverture et ses critères de couverture, + le seuil global
    (`threshold_percent`, 85% par défaut) avant génération du PRD.
  - `scripts/interview_state.py` (stdlib uniquement) : `start` / `record` / `progress`
    / `prd` / `edit`. L'état vit dans un fichier JSON (`.interview_state/` à la racine
    du repo, jamais committé), pas dans la mémoire de la conversation, pour survivre à
    une coupure/reprise. `progress` affiche la couverture par section (○/◐/●) et le
    pourcentage global. `prd` refuse de générer sous le seuil sans `--force` (réservé à
    une demande explicite du client) et liste toujours les points encore à clarifier
    plutôt que de les cacher.
  - **`edit <section> <turn_index> "<réponse corrigée>"`** : le client peut à tout
    moment corriger une réponse déjà enregistrée ou une suggestion que l'agent lui a
    proposée — remplace le tour existant plutôt que d'en ajouter un, pour que le PRD
    final ne contienne jamais deux versions contradictoires.
  - `reference/regles-entretien.md` : règles de conduite (une question à la fois dans
    les mots du client, reformulation avant de clore une section, relance ciblée sur
    les critères manquants, réouverture d'une section déjà couverte, et l'enchaînement
    du PRD généré vers la construction du payload/code — pas une fin en soi).
  - **Avancement affiché à chaque `record`** (pourcentage global + sections
    complètes/total) — à partager au client à chaque changement de section
    (`regles-entretien.md` §2bis) pour qu'il voie une progression naturelle et
    mesurable plutôt que de deviner où en est l'entretien.
  - PRD écrit dans `skill/output/<slug-titre>-PRD-<6 hex>.md` (dossier gitignored : un
    PRD est spécifique à un client, jamais à committer dans le repo public du skill).
  - `SKILL.md` §0ter et §10, et `llms.txt`, mis à jour pour pointer vers ce nouveau
    système. Testé de bout en bout (entretien complet avec correction de réponse +
    refus/forçage du PRD sous le seuil) sans régression sur `doctor.py` ni
    `test_validate_payload.py`.

## 1.21 — 2026-10-27
- **Nouveau `reference/decouverte-besoin.md`** : découverte structurée du besoin en 4
  thèmes (entités, contraintes, objectifs, taille du problème), avec une conversation
  guidée et une notion de couverture avant génération, adaptée à ce que ce skill sait
  faire en plus : lire le code existant du client (§0 Étape 1) et trancher
  explicitement entre les deux offres Nomadia.
- **Garde-fou explicite ajouté à `SKILL.md` §0 Étape 2** : dès qu'un besoin client
  touche un mécanisme de l'offre complète (multi-ressources, stock, ordre entre jobs,
  horizon borné, récurrence), l'agent doit **poser la question self-service vs offre
  complète au client**, plutôt que de supposer silencieusement le self-service parce
  que c'est ce que ce skill appelle directement.
- `llms.txt` et la table §13 des fichiers mis à jour pour référencer ce nouveau
  fichier en priorité sur un besoin pas immédiatement évident.

## 1.20 — 2026-10-27
- **Validé par un test en conditions réelles** : un agent générique sans aucun
  contexte préalable, invoqué uniquement avec la demande client "~100 interventions,
  une dizaine de techniciens, certains habilités électricité", a suivi `SKILL.md`,
  découvert et utilisé lui-même `scripts/generate_load_test.py` (sans qu'on le lui
  indique), validé avec `doctor.py`, et s'est arrêté avant l'appel réel en demandant
  la confirmation de la clé + l'acceptation du coût — comportement conforme sur toute
  la ligne.
- **Amélioration remontée par ce test** : `generate_load_test.py` avait des ratios
  élec/rendez-vous/engagement codés en dur (30%/20%/10%/4%), pas adaptés à un besoin
  client réel différent de ces proportions. Le script accepte maintenant
  `--elec-resource-ratio`, `--elec-job-ratio`, `--appointment-ratio`, `--fixed-ratio`
  et `--date`, avec tirage aléatoire (plus de motif modulo figé) pour une répartition
  plus réaliste. `examples/13_charge_100_jobs.json` régénéré en conséquence.

## 1.19 — 2026-10-27
- **Nouveau `scripts/generate_load_test.py`** : génère un payload self-service à
  grande échelle (N jobs / M ressources configurables), combinant à l'échelle
  plusieurs mécanismes confirmés (locality, requirements, SLA avec `value_per_hour`
  explicite — voir §1.18 —, appointment_sla, fixed_resource_id, breaks,
  shift_penalty, maximum_jobs_per_shift). Affiche le coût **maximum** estimé
  (5 + ressources × jobs) avant d'écrire le fichier, puisque ce script ne fait lui-même
  aucun appel réel.
- Nouvel exemple `examples/13_charge_100_jobs.json` (100 jobs, 10 ressources, généré
  par le script ci-dessus, seed=42 pour reproductibilité) — coût maximum ≈ 1005
  crédits si tous les jobs sont alloués. `examples/README.md` et `llms.txt` mis à jour.

## 1.18 — 2026-10-27
- **Lacune confirmée par test réel, corrigée** : `value_per_hour` n'a aucune valeur
  par défaut déclarée côté self-service (vérifié directement dans le schéma OpenAPI
  réel — `nullable`, pas de `default`), contrairement à l'ancienne doc du skill
  (issue du PDF offre complète) qui affirmait un défaut de `10000`. Conséquence
  démontrée par deux tests contrôlés (`examples/11_scenario_complexe.json` puis
  `examples/12_test_controle_sla_value.json`) : un job sans `value_per_hour`
  explicite a été planifié 6h30 après sa fenêtre SLA malgré une `base_jeopardy_penalty`
  de 500 et une ressource qualifiée disponible dans la fenêtre ; en fixant
  `value_per_hour` explicitement (toutes choses égales par ailleurs), la fenêtre a
  été respectée.
- `reference/entities.md` et `SKILL.md` §2bis mis à jour avec cet avertissement.
  Nouvelle section `troubleshooting.md` §3bis. `scripts/recommend_improvements.py`
  détecte maintenant automatiquement ce cas (HIGH) : un job avec une pénalité SLA
  mais sans `value_per_hour` explicite.
- Nouveaux exemples `examples/11_scenario_complexe.json` (scénario combiné réaliste,
  8 jobs/3 ressources, pour challenger l'API sur plusieurs mécanismes self-service à
  la fois) et `examples/12_test_controle_sla_value.json` (payload de test minimal et
  isolé ayant permis de confirmer la cause ci-dessus).

## 1.17 — 2026-10-27
- **Correction majeure, honnête : le skill documentait la mauvaise API.** Nomadia a
  deux offres : une offre complète (PDF interne "Scheduler Schema Documentation", 33
  pages, nécessite une équipe projet Nomadia) et une offre self-service (documentée
  sur https://scheduler-json-api.readme.io, ce que la clé API de test donne
  réellement). Ce skill construisait ses exemples et sa référence de schéma à partir
  du PDF de l'offre complète, en supposant qu'il décrivait le self-service — ce qui
  n'était pas le cas. Déclenché par le comportement suspect documenté en 1.16
  (job multi-ressources), confirmé définitivement en comparant le PDF au schéma
  OpenAPI réel qui alimente les pages readme.io (récupéré directement via le réseau
  de la page, pas la doc rendue — voir `vendor-docs/openapi-schedule.json` et
  `vendor-docs/openapi-geocode.json`).
- **`reference/entities.md` entièrement réécrit** sur le vrai schéma self-service :
  5 entités racine (Job, JobType, Location, Resource, ResourceType), SLA/Shift/Break/
  disponibilités imbriqués (jamais une entité top-level séparée), `requirements`
  comme simple liste de chaînes, `fixed_resource_id` directement sur le job (pas de
  `commit_date_time_stamp`), sortie `allocations[]` par job avec `visits[]` imbriqués.
  Documente aussi la permissivité observée du désérialiseur (un champ inconnu est
  silencieusement ignoré, pas rejeté, malgré `additionalProperties: false` déclaré).
- **Nouveau fichier `reference/offre-complete-nomadia.md`** : pour chaque mécanisme
  confirmé absent du self-service (job multi-ressources, stock/pièces, ordre entre
  jobs, horizon de planification borné, disponibilité récurrente, priorité de
  rendez-vous dédiée), un exemple tiré de la doc de l'offre complète + la consigne
  explicite de ne jamais bloquer le client ni simuler le mécanisme en self-service,
  mais de l'orienter vers un contact Nomadia.
- **7 des 10 exemples corrigés** (`02`, `05`, `06`, `07`, `08`, `09` alignés sur le
  vrai schéma self-service ; `03`, `04`, `10` réduits à des payloads minimaux
  "offre complète uniquement", clairement avertis, non testables en self-service).
  `examples/README.md` entièrement réécrit avec une colonne "Self-service ?" et
  l'historique de cette correction.
- **`scripts/validate_payload.py` réécrit** : `requirements` validé comme liste de
  chaînes (plus d'entité séparée), `sla`/`appointment_sla` comme objets imbriqués sur
  le job, indisponibilités validées comme imbriquées sous `resources[].unavailabilities[]`.
  Ajout d'une détection explicite (en `[WARN]`, jamais `[ERROR]` puisque l'API
  elle-même ne rejette pas ces clés) de tout champ de l'offre complète envoyé par
  erreur (`job_resources`, `parts`, `pre_requisite_definitions`,
  `schedule_definition(s)`, `*_pattern`…). `scripts/test_validate_payload.py` mis à
  jour en conséquence (suppression des tests sur des mécanismes confirmés absents,
  ajout de tests sur `requirements`/`fixed_resource_id`/indisponibilités imbriquées).
- **`scripts/recommend_improvements.py` corrigé** : la vérification de compétences
  regarde maintenant `requirements` sur jobs/resources directement (plus
  `job_requirements`/`resource_requirements`, qui n'existent pas) ; la vérification
  SLA ne regarde plus un `slas[]`/`job_sla_id` top-level inexistant mais les objets
  `sla`/`appointment_sla` imbriqués ; **la vérification `schedule_definitions` (déjà
  marquée "non confirmé" en 1.x) est supprimée** et remplacée par une détection
  générique (HIGH) de tout champ de l'offre complète présent dans le payload.
- **`SKILL.md` restructuré (§3-11 → §3-9)** : schéma self-service comme référence
  primaire, avertissement en tête sur les deux offres, table §2bis des mécanismes
  self-service uniquement, redirections explicites vers
  `reference/offre-complete-nomadia.md` partout où un mécanisme de l'offre complète
  était auparavant présenté comme disponible. `troubleshooting.md` §4bis mis à jour
  avec la cause définitive (confirmée, plus "non résolu") ; §1-2-4-6 corrigés des
  mécanismes de l'offre complète qui s'y étaient glissés (`job_sla_id`,
  `PossibleResourcesInsufficientParts`, `travel_time_multiplier`…).
- Version bumpée 1.16 → 1.17.

## 1.16 — 2026-10-26
- **Comportement suspect documenté honnêtement, pas encore résolu** : deux appels
  réels identiques sur `10_job_multi_ressources.json` (job déclaré avec 2 entrées
  `job_resources`, `resource_index` 1 et 2) n'ont chacun alloué qu'**une seule**
  ressource (RES-1 puis RES-2, au hasard d'un appel à l'autre), sans erreur ni
  `unallocated_job_reasons` — comme si la contrainte multi-ressources était ignorée.
  Nouvelle section `troubleshooting.md` §4bis détaillant les 3 hypothèses non
  tranchées (clé `job_resources` mal nommée, limite de l'environnement de test, champ
  manquant) et `examples/README.md` mis à jour avec un avertissement explicite sur cet
  exemple. Question posée à Nomadia en parallèle — à corriger dès réponse.
- **Correction d'un angle mort repéré pendant le test en conditions réelles** : le
  skill utilisait silencieusement une `NOMADIA_API_KEY` déjà présente dans
  l'environnement, sans jamais demander explicitement au client s'il avait déjà un
  compte/une clé sur le portail de test Nomadia. Une clé qui traîne d'une session
  précédente (démo, autre client, l'intégrateur lui-même) pouvait donc être utilisée
  à la place de la sienne, sans qu'il le sache.
- `ONBOARDING.md` §2 et `SKILL.md` §-1 : garde-fou explicite, à poser comme question
  avant tout appel réel (pas juste documenté en passant) — confirmer à qui appartient
  la clé utilisée, diriger vers le portail de test
  (`scheduler-api-test.nomadia-app.com/dashboard`) si le client n'en a pas encore, et
  prévenir qu'un nouveau compte/une nouvelle clé sera probablement nécessaire le jour
  de la bascule en prod.

## 1.14 — 2026-10-26
- **Correction d'un angle mort réel de distribution, trouvé en testant le parcours
  client de bout en bout** : un test a montré qu'un agent à qui on demande "installe
  ce skill" à partir de l'URL du repo clone le repo entier puis copie correctement le
  sous-dossier `skill/` dans `~/.claude/skills/` — mais comme `reference/
  battlecard-timefold.md` (argumentaire commercial interne) vivait *dans* `skill/`,
  il était embarqué dans cette copie. `package_for_client.py` l'excluait bien, mais ce
  filtrage ne protège que ceux qui pensent à l'utiliser — pas un client qui reçoit le
  repo brut et l'installe lui-même.
- **`reference/battlecard-timefold.md` déplacé vers `internal/battlecard-timefold.md`**
  (hors de `skill/`, à la racine du repo). Un fichier qui n'est jamais dans `skill/` ne
  peut pas être copié avec `skill/`, quelle que soit la méthode d'installation —
  protection structurelle plutôt qu'une liste d'exclusion à maintenir.
- `README.md`, `package_for_client.py`, `SKILL.md` §13, `llms.txt` : références mises
  à jour en conséquence.

## 1.13 — 2026-10-23
- **Convention `breaks` confirmée par un vrai appel API** : `07_pause_obligatoire.json`
  (pause de 45 min, 12:00-12:45) → HTTP 200, `break_allocations` rempli avec la pause
  demandée. La structure imbriquée `shifts[].breaks[]` est désormais la référence
  (`validate_payload.py` continue d'accepter aussi la forme top-level par tolérance).
  Reste à confirmer : le nom de clé `job_resources` (test prévu sur
  `10_job_multi_ressources.json`).
- **Nouveau contrôle dans `recommend_improvements.py`** (signalé par un testeur) :
  le script ne vérifiait pas que les pauses obligatoires demandées dans le payload
  apparaissent bien dans `break_allocations` de la réponse. Ajout d'un contrôle HIGH
  qui compare le nombre de pauses demandées vs présentes et alerte en cas d'écart —
  une pause non respectée est un risque de conformité, pas un simple détail
  d'optimisation.

## 1.12 — 2026-10-23
- **Annonce explicite de l'environnement visé à l'exécution**, pas seulement dans la
  doc : chaque appel réel (`snippets/client.py` et `client.js` — `schedule_request`/
  `scheduleRequest` et `geocode_request`/`geocodeRequest` —, `scripts/compare_scenarios.py`
  en mode `--api-key`, et le script autonome de `ONBOARDING.md` §4) affiche désormais
  au lancement `[INFO] Appel vers l'environnement de TEST Nomadia (...)` ou
  `[ATTENTION] Appel vers ... — vérifie que c'est bien la PRODUCTION voulue`, selon
  le hostname réellement ciblé. Objectif : qu'un client ne découvre jamais après coup
  qu'il visait le test en pensant viser la prod (ou l'inverse) — l'info est visible à
  chaque appel, pas seulement lisible dans un README qu'on peut sauter.
- `SKILL.md` §1 : paragraphe explicite rappelant que la bascule test→prod se fait via
  `NOMADIA_BASE_URL` (aucun code à changer) mais reste une action volontaire, jamais
  automatique.

## 1.11 — 2026-10-23
- **Correction majeure, confirmée par Nomadia (email de Maxime, 23/10/2026)** : il
  existe deux environnements distincts avec des hostnames différents —
  `scheduler-api-test.nomadia-app.com` (test, **actif**) et
  `scheduler-api.nomadia-app.com` (prod, **pas encore actif**, DNS `NXDOMAIN`
  confirmé en testant). Jusqu'ici, tout le skill (SKILL.md, ONBOARDING.md,
  snippets/client.py, client.js, scripts/compare_scenarios.py) ne connaissait que le
  hostname prod — ce qui aurait fait échouer tout premier test réel d'un client avec
  une erreur DNS impossible à diagnostiquer sans cette info.
- `snippets/client.py`, `client.js`, `scripts/compare_scenarios.py` : hostname par
  défaut changé pour le test, désormais surchargeable via `NOMADIA_BASE_URL` (pour le
  jour où la prod devient active).
- `SKILL.md` §1/§2 et `ONBOARDING.md` §0 : tableau des deux environnements + portails,
  avec l'avertissement explicite de Nomadia que ces URLs sont "non définitives" à
  cette date.
- Versions explicitement annoncées par Nomadia comme non définitives — à revérifier
  avant toute mise en production réelle chez un client.
- **Premier test réel réussi (23/10/2026)** : `POST /api/schedule` sur
  `scheduler-api-test.nomadia-app.com` avec `examples/01_minimal.json` → HTTP 200, 2
  jobs/2 alloués, 3 `travels`, `unallocated_job_reasons` et `break_allocations` vides.
  Confirme que les noms de champs de réponse utilisés dans `recommend_improvements.py`
  (`allocations`, `travels`, `unallocated_job_reasons`) sont exacts — plus seulement
  déduits de la doc. `doctor.py --response` sur cette vraie réponse a produit un
  ratio trajet/temps utile de 133% (cohérent : micro-exemple à 2 jobs, trajet
  aller-retour dépôt proportionnellement lourd — sans valeur commerciale à ce volume,
  comme `kpis-metier.md` l'indique déjà). La convention `schedule_definitions` reste
  **ni confirmée ni infirmée** (cet exemple n'en envoie pas) — à tester spécifiquement
  si besoin.

## 1.10 — 2026-10-23
- Ajout `ONBOARDING.md` : démarrage rapide pour un client qui reçoit ce skill —
  installation (Claude Code et autres agents), configuration sécurisée de la clé API,
  premier test sans crédits (`doctor.py` sur un exemple), premier vrai appel API, et
  où aller ensuite. Objectif : qu'un agent IA qui découvre le skill en premier contact
  suive ce document au lieu de réexpliquer chaque étape depuis zéro à chaque client.
- `ONBOARDING.md` documente aussi 2 scénarios de blocage réseau réels, rencontrés en
  testant ce skill lui-même : (1) sandbox cloud avec proxy à liste blanche (erreur
  HTTP/connexion) et (2) résolveur DNS local qui ne connaît pas le domaine
  (`scheduler-api.nomadia-app.com` reconfirmé exact et inchangé via la doc officielle
  au moment de l'ajout) — avec la commande `dig @1.1.1.1` pour trancher.
- `SKILL.md` §-1 et `llms.txt` pointent maintenant vers `ONBOARDING.md` en premier
  contact.

## 1.9.1 — 2026-10-23
- Correctif : `scripts/doctor.py --help` (ou `-h`, ou aucun argument) plantait en
  essayant d'ouvrir "--help" comme chemin de fichier. Repéré lors d'un premier test en
  local par un utilisateur. Gère maintenant `-h`/`--help` proprement (affiche l'usage,
  exit 0) et `--response` sans valeur suivante (message d'erreur clair, exit 2) au
  lieu d'un crash Python.

## 1.9 — 2026-10-23
- **Correction de fiabilité** : la détection de `ScheduleDefinition` dans
  `recommend_improvements.py` reposait sur un nom de clé racine (`schedule_definitions`)
  jamais vérifié contre la doc — message et priorité (LOW) explicitement reformulés
  pour ne pas faire croire à une certitude qu'on n'a pas. Même traitement pour le champ
  `Shift.id` : marqué obligatoire par `reference/entities.md` mais absent du quick
  start officiel de Nomadia reproduit dans `SKILL.md` — downgradé de [ERROR] à [WARN]
  dans `validate_payload.py` plutôt que de bloquer sur une base non confirmée.
- **Couverture FSM étendue** dans `validate_payload.py` : cross-ref désormais vérifiés
  pour `resource_requirements`, `resource_parts`, `resource_unavailabilities`,
  `job_resources` (`fixed_resource_id`, règle `commit_date_time_stamp` nécessite
  `fixed_resource_id`), `pre_requisite_definitions`, et les `breaks` (nested sous
  shift ou top-level avec `shift_id`).
- **5 nouveaux exemples** (`examples/06` à `10`) couvrant les cas FSM restants :
  ressource déjà engagée (`fixed_resource_id`+`commit_date_time_stamp`), pause
  obligatoire (`Break`), indisponibilité ressource (`ResourceUnavailability`),
  rendez-vous client prioritaire (`appointment_sla_id`+`appointment_priority`), job
  multi-ressources/binôme (`JobResource.resource_index`). Tous les 10 exemples
  existants corrigés pour inclure `Shift.id` (manquant depuis la 1.0).
  `examples/README.md` documente aussi 2 conventions de structure non confirmées
  (nesting des `breaks`, nom de clé `job_resources`) — transparence plutôt que fausse
  certitude.
- `scripts/test_validate_payload.py` : 5 nouveaux tests de régression sur les
  vérifications croisées ajoutées.
- `scripts/doctor.py` : verdict final en une ligne (✅/❌) pour une lecture plus rapide.

## 1.8 — 2026-10-23
- Ajout `scripts/doctor.py` : point d'entrée unique (valide puis recommande en une
  seule commande) — une seule chose à retenir au lieu de trois scripts séparés.
  `validate_payload.py` et `recommend_improvements.py` restent utilisables seuls
  (ex: intégration CI) mais `doctor.py` devient le réflexe par défaut partout dans
  `SKILL.md`.
- `SKILL.md` : nouvelles sections -1 ("Premier contact" — que répondre si l'utilisateur
  ne sait pas par où commencer) et -1bis (pointeur vers `doctor.py`).
- `reference/kpis-metier.md` : reformulation de l'intro pour servir aussi un client
  déjà équipé qui suit sa propre performance, pas uniquement un contexte de vente.
- Ajout `FEEDBACK.md` (racine) : comment signaler un problème (version précise,
  payload minimal reproductible, sortie de `doctor.py`), et ce qui n'est pas un bug.
- `llms.txt` mis à jour (doctor.py en tête des scripts exécutables).

## 1.7 — 2026-10-23
- Ajout `skill/llms.txt` : index priorisé des fichiers du skill pour un agent IA qui
  découvre le repo — inspiré du `llms.txt` de la doc Nomadia et des manifestes
  machine-lisibles (type `context7.json`) qu'on trouve sur plusieurs repos GitHub
  d'outils IA, pensés pour un agent plutôt que pour un humain qui parcourt au hasard.
- Ajout `CONTRIBUTING.md` (racine du repo) : principes de contribution — jamais de
  champ deviné, jamais de clé API en dur, tout exemple doit passer le validateur,
  toute modif du validateur doit relancer ses tests, versionner SKILL.md + CHANGELOG +
  llms.txt à chaque évolution.
- `SKILL.md` §13bis : pointeur explicite vers `llms.txt` pour tout agent qui découvre
  le skill en premier.

## 1.6 — 2026-10-23
- Ajout d'un argumentaire commercial interne (positionnement vs solveurs scientifiques
  concurrents) + réponses aux objections courantes — déplacé depuis vers `internal/`
  dès la version suivante qui a séparé le contenu interne du contenu livré au client
  (voir entrée correspondante plus bas dans ce changelog).

## 1.5 — 2026-10-23
- Ajout `scripts/compare_scenarios.py` : comparateur de scénarios, zéro dépendance.
  Mode statique (diff de config, gratuit) ou mode réel (`--api-key`, vrai avant/après
  chiffré sur taux d'allocation/distance/crédits — consomme de vrais crédits, à
  n'utiliser qu'avec l'accord explicite de l'utilisateur). Réponse directe au fait que
  les solveurs scientifiques généralistes vendent souvent le benchmarking comme
  fonctionnalité Enterprise.
- Ajout `reference/replanification-temps-reel.md` : documente les patterns Nomadia
  équivalents aux fonctionnalités "continuous/real-time planning" et "pinned planning
  variables" des solveurs généralistes (fixed_resource_id + commit_date_time_stamp,
  DeletedEntity + output_type, ResourceKnownLocation + JobResourceStatus), et nomme
  honnêtement ce que Nomadia ne fait pas nativement (explication de score détaillée,
  mode daemon, benchmarking natif) avec le pattern qui compense chaque manque.

## 1.4 — 2026-10-23
- Ajout `scripts/recommend_improvements.py` : moteur de recommandations proactives,
  orienté ROI, exécutable en CLI. Analyse un payload (config seule) et optionnellement
  une vraie réponse API (`--response`) pour sortir des recommandations priorisées
  (HIGH/MEDIUM/LOW), chacune reliée à `reference/kpis-metier.md`. Testé sur les 5
  exemples et sur une réponse API simulée.
- `SKILL.md` §0 : nouvelle étape 2bis — table "objectif client → mécanismes Nomadia à
  activer → pourquoi (ROI)" pour cadrer la configuration dès que le besoin métier est
  connu, sans laisser l'utilisateur deviner quel champ cocher.
- `SKILL.md` §0 étape 3 : le copilote lance désormais systématiquement
  `recommend_improvements.py` après avoir posé un payload, et de nouveau après un vrai
  appel API — il doit présenter les recommandations `[HIGH]` sans attendre qu'on les
  lui demande.
- Préparation explicite à un test API réel (clé fournie précédemment par
  l'utilisateur) : rappel que la clé ne doit jamais être écrite en dur dans un fichier
  commité, uniquement utilisée en mémoire au moment du test.

## 1.3 — 2026-10-23
- Ajout `reference/kpis-metier.md` : traduction des paramètres/résultats techniques en
  arguments business (taux d'allocation, ratio trajet/temps utile, respect SLA,
  équilibrage de charge, coût en crédits vs planification manuelle, stabilité du plan).
- Ajout `scripts/test_validate_payload.py` : suite de tests automatisés sur le
  validateur (régression du bug lat/lng corrigé en 1.2, détection de chaque type
  d'erreur, les 5 exemples doivent tous passer).
- `SKILL.md` explicitement rendu agent-agnostique : note en tête de fichier précisant
  que la procédure ne dépend d'aucun agent IA précis (Claude Code, Cursor, Copilot
  agent, etc.), et reformulation des références à "Bash" en "ton outil d'exécution de
  commandes". Reste volontairement scopé à Nomadia uniquement (pas de couche
  multi-fournisseur).

## 1.2 — 2026-10-23
- Ajout `scripts/validate_payload.py` : validateur exécutable (plus un simple snippet à
  copier), testé contre un payload volontairement cassé.
- Ajout `examples/` : 5 payloads vérifiés (minimal, compétence requise, stock de pièces,
  ordre entre jobs, disponibilité récurrente), tous passés au validateur.
- Ajout boucle d'auto-correction dans `SKILL.md` §0 étape 3 (construire → valider →
  corriger → appeler → diagnostiquer une erreur API → corriger → réessayer une fois).
- `snippets/client.js` et `client.py` : ajout retry avec backoff sur les erreurs réseau
  et 5xx uniquement (jamais sur 400/401/402/403, qui ne se corrigent pas en réessayant).
- Ajout de ce CHANGELOG.

## 1.1 — 2026-10-23
- Ajout `reference/entities.md` (transcription exhaustive du schéma + énumération
  complète des raisons de non-allocation).
- Ajout `troubleshooting.md` (playbook de dépannage par symptôme).
- Ajout `snippets/client.js` et `client.py` (client HTTP + validation locale basique).

## 1.0 — 2026-10-23
- Première version : `SKILL.md` avec résumé du schéma complet, quick start, crédits et
  codes d'erreur, procédure de cadrage (§0).
