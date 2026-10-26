# Changelog du skill

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
  découvre le repo — inspiré du `llms.txt` de la doc Nomadia et du pattern
  `context7.json` du repo GitHub `TimefoldAI/timefold-solver` (manifestes
  machine-lisibles pensés pour un agent, pas pour un humain qui parcourt au hasard).
- Ajout `CONTRIBUTING.md` (racine du repo) : principes de contribution inspirés du
  `CONTRIBUTING.md`/`CONSTITUTION.md` du repo Timefold — jamais de champ deviné,
  jamais de clé API en dur, tout exemple doit passer le validateur, toute modif du
  validateur doit relancer ses tests, versionner SKILL.md + CHANGELOG + llms.txt à
  chaque évolution.
- `SKILL.md` §13bis : pointeur explicite vers `llms.txt` pour tout agent qui découvre
  le skill en premier.

## 1.6 — 2026-10-23
- Ajout `reference/battlecard-timefold.md` : argumentaire commercial factuel vs
  Timefold (barrière technique Java/Kotlin-only de leur Solver open source, pricing
  100% "contact sales" de leur offre Platform, géocodage inclus chez Nomadia) +
  reconnaissance honnête de ce que Timefold fait mieux (échelle 500k jobs,
  explicabilité native payante, what-if avancé) + réponses aux objections courantes.
  Sourcé sur docs.timefold.ai et timefold.ai/pricing au 23/10/2026.

## 1.5 — 2026-10-23
- Ajout `scripts/compare_scenarios.py` : comparateur de scénarios, zéro dépendance.
  Mode statique (diff de config, gratuit) ou mode réel (`--api-key`, vrai avant/après
  chiffré sur taux d'allocation/distance/crédits — consomme de vrais crédits, à
  n'utiliser qu'avec l'accord explicite de l'utilisateur). Réponse directe au fait que
  les solveurs scientifiques (Timefold, OptaPlanner) vendent souvent le benchmarking
  comme fonctionnalité Enterprise.
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
